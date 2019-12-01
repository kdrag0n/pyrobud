import asyncio
import io
import os
import subprocess
import time
from datetime import datetime

from PIL import Image

from .. import command, module, util

PNG_MAGIC = b"\x89\x50\x4e\x47\x0d\x0a\x1a\x0a"


class LengthMismatchError(Exception):
    pass


class StickerModule(module.Module):
    name = "Sticker"

    async def on_load(self):
        self.db = self.bot.get_db("stickers")
        self.settings_db = self.bot.get_db("sticker_settings")

    async def add_sticker(self, sticker_data, pack_name, emoji="❓"):
        # User to send messages to
        target = "Stickers"

        # The sticker bot's error strings
        too_many_stickers_error = "A pack can't have more than 120 stickers at the moment."
        invalid_format_error = "Sorry, the file type is invalid."

        commands = [
            ("text", "/cancel"),
            ("text", "/addsticker"),
            ("text", pack_name),
            ("file", sticker_data),
            ("text", emoji),
            ("text", "/done"),
        ]

        success = False
        before = datetime.now()

        async with self.bot.client.conversation(target) as conv:

            async def reply_and_ack():
                # Wait for a response
                response = await conv.get_response()
                # Ack the response to suppress its notiication
                await conv.mark_read()

                return response

            try:
                for cmd_type, data in commands:
                    if cmd_type == "text":
                        await conv.send_message(data)
                    elif cmd_type == "file":
                        await conv.send_file(data, force_document=True)
                    else:
                        raise TypeError(f"Unknown command type '{cmd_type}'")

                    # Wait for both the rate-limit and the bot's response
                    try:
                        wait_task = self.bot.loop.create_task(reply_and_ack())
                        ratelimit_task = self.bot.loop.create_task(asyncio.sleep(0.25))
                        await asyncio.wait({wait_task, ratelimit_task})

                        response = wait_task.result()
                        if too_many_stickers_error in response.raw_text:
                            return (
                                "error",
                                f"Sticker creation failed because there are too many stickers in the [{pack_name}](https://t.me/addstickers/{pack_name}) pack — Telegram's limit is 120. Delete some unwanted stickers or create a new pack.",
                            )
                        elif invalid_format_error in response.raw_text:
                            return (
                                "error",
                                f"Sticker creation failed because Telegram rejected the uploaded image file for deviating from their expected format. This is usually indicative of a MIME type issue in this bot.",
                            )
                    except asyncio.TimeoutError:
                        after = datetime.now()
                        delta_seconds = int((after - before).total_seconds())

                        return (
                            "error",
                            f"Sticker creation failed after {delta_seconds} seconds because [the bot](https://t.me/{target}) failed to respond within 1 minute of issuing the last command.",
                        )

                success = True
            finally:
                # Cancel the operation if we return early
                if not success:
                    await conv.send_message("/cancel")

        return ("success", f"https://t.me/addstickers/{pack_name}")

    async def img_to_png(self, src, dest=None):
        if not dest:
            dest = src

        def _img_to_png():
            im = Image.open(src).convert("RGBA")
            if hasattr(src, "seek"):
                src.seek(0)
            im.save(dest, "png")

        await util.run_sync(_img_to_png)
        return dest

    async def img_to_sticker(self, src, formats):
        if not formats:
            return

        def _img_to_sticker():
            im = Image.open(src).convert("RGBA")

            sz = im.size
            target = 512
            if sz[0] > sz[1]:
                w_ratio = target / float(sz[0])
                h_size = int(float(sz[1]) * float(w_ratio))
                im = im.resize((target, h_size), Image.LANCZOS)
            else:
                h_ratio = target / float(sz[1])
                w_size = int(float(sz[0]) * float(h_ratio))
                im = im.resize((w_size, target), Image.LANCZOS)

            for fmt, dest in formats.items():
                im.save(dest, fmt)

        await util.run_sync(_img_to_sticker)
        return formats

    @command.desc("Kang a sticker into configured/provided pack")
    async def cmd_kang(self, msg, pack_name):
        if not msg.is_reply:
            return "__Reply to a sticker to kang it.__"

        saved_pack_name = await self.settings_db.get("kang_pack")
        if not saved_pack_name and not pack_name:
            return "__Specify the name of the pack to add the sticker to.__"

        if pack_name:
            await self.settings_db.put("kang_pack", pack_name)
        else:
            pack_name = saved_pack_name

        reply_msg = await msg.get_reply_message()

        if not reply_msg.sticker:
            return "__That message isn't a sticker.__"

        await msg.result("Kanging sticker...")

        sticker_bytes = await reply_msg.download_media(file=bytes)
        sticker_buf = io.BytesIO(sticker_bytes)
        await self.img_to_png(sticker_buf)

        sticker_buf.seek(0)
        sticker_buf.name = "sticker.png"
        status, result = await self.add_sticker(sticker_buf, pack_name, emoji=reply_msg.file.emoji)
        if status == "success":
            self.bot.dispatch_event_nowait("stat_event", "stickers_created")
            return f"[Sticker kanged]({result})."
        else:
            return result

    @command.desc("Save a sticker with a name (as a reference)")
    async def cmd_save(self, msg, name):
        if not msg.is_reply:
            return "__Reply to a sticker to save it.__"

        if not name:
            return "__Provide a name for the new sticker.__"

        if await self.db.has(name):
            return "__There's already a sticker with that name.__"

        reply_msg = await msg.get_reply_message()

        if not reply_msg.sticker:
            return "__That message isn't a sticker.__"

        await self.db.put(name, reply_msg.file.id)
        return f"Sticker saved as `{name}`."

    @command.desc("Save a sticker with a name (to disk)")
    async def cmd_saved(self, msg, name):
        if not msg.is_reply:
            return "__Reply to a sticker to save it.__"

        if not name:
            return "__Provide a name for the new sticker.__"

        if await self.db.has(name):
            return "__There's already a sticker with that name.__"

        reply_msg = await msg.get_reply_message()

        if not reply_msg.sticker:
            return "__That message isn't a sticker.__"

        path = await util.tg.msg_download_file(reply_msg, msg, destination=f"stickers/{name}.webp", file_type="sticker")
        if not path:
            return "__Error downloading sticker__"

        await self.db.put(name, path)
        return f"Sticker saved to disk as `{name}`."

    @command.desc("List saved stickers")
    async def cmd_stickers(self, msg):
        out = ["**Stickers saved**:"]

        async for key, value in self.db:
            typ = "local" if value.endswith(".webp") else "reference"
            out.append(f"{key} ({typ})")

        if len(out) == 1:
            return "__No stickers saved.__"

        return "\n    \u2022 ".join(out)

    @command.desc("List locally saved stickers")
    async def cmd_stickersp(self, msg):
        out = ["**Stickers saved**:"]

        async for key, value in self.db:
            if value.endswith(".webp"):
                out.append(key)

        if len(out) == 1:
            return "__No stickers saved.__"

        return "\n    \u2022 ".join(out)

    @command.desc("Delete a saved sticker")
    async def cmd_sdel(self, msg, name):
        if not name:
            return "__Provide the name of a sticker to delete.__"

        if not await self.db.has(name):
            return "__That sticker doesn't exist.__"

        await self.db.delete(name)
        return f"Sticker `{name}` deleted."

    @command.desc("Fetch a sticker by name")
    async def cmd_s(self, msg, name):
        if not name:
            await msg.result("__Provide the name of the sticker to fetch.__")
            return

        path = await self.db.get(name)
        if path is None:
            await msg.result("__That sticker doesn't exist.__")
            return

        await msg.result("Uploading sticker...")
        await msg.respond(file=path, reply_to=msg.reply_to_msg_id)
        await msg.delete()

    @command.desc("Fetch a sticker by name and send it as a photo")
    @command.alias("sphoto")
    async def cmd_sp(self, msg, name):
        if not name:
            await msg.result("__Provide the name of the sticker to fetch.__")
            return

        webp_path = await self.db.get(name)
        if webp_path is None:
            await msg.result("__That sticker doesn't exist.__")
            return

        if not webp_path.endswith(".webp"):
            await msg.result("__That sticker cannot be sent as a photo.__")
            return

        await msg.result("Uploading sticker...")
        png_path = webp_path[: -len(".webp")] + ".png"
        if not os.path.isfile(png_path):
            await self.img_to_png(webp_path, dest=png_path)

        await msg.respond(file=png_path, reply_to=msg.reply_to_msg_id)
        await msg.delete()

    @command.desc("Create a sticker from an image and add it to the given pack")
    async def cmd_sticker(self, msg, *args):
        if not msg.is_reply and not msg.file:
            return "__Reply to or embed an image to sticker it.__"

        if not args:
            await msg.result(
                "__Provide the name of the pack to add the sticker to, and optionally the emoji to associate with it.__"
            )
            return

        if msg.file:
            reply_msg = msg
        else:
            reply_msg = await msg.get_reply_message()

        if not reply_msg.file:
            return "__That message doesn't contain an image.__"

        pack_name = args[0]
        emoji = args[1] if len(args) > 1 else "❓"

        await msg.result("Creating sticker...")

        sticker_bytes = await reply_msg.download_media(file=bytes)
        sticker_buf = io.BytesIO(sticker_bytes)

        png_buf = io.BytesIO()
        webp_buf = io.BytesIO()
        await self.img_to_sticker(sticker_buf, {"png": png_buf, "webp": webp_buf})

        png_buf.seek(0)
        png_buf.name = "sticker.png"
        status, result = await self.add_sticker(png_buf, pack_name, emoji=emoji)
        if status == "success":
            self.bot.dispatch_event_nowait("stat_event", "stickers_created")
            await msg.result(f"[Sticker created]({result}). Preview:")

            webp_buf.seek(0)
            webp_buf.name = "sticker.webp"
            await msg.respond(file=webp_buf)
        else:
            return result

    @command.desc("Create a sticker from an image and save it to disk under the given name")
    async def cmd_qstick(self, msg, name):
        if not msg.is_reply and not msg.file:
            return "__Reply to an image to sticker it.__"

        if not name:
            return "__Provide a name for the new sticker.__"

        if await self.db.has(name):
            return "__There's already a sticker with that name.__"

        if msg.file:
            reply_msg = msg
        else:
            reply_msg = await msg.get_reply_message()

        if not reply_msg.file:
            return "__That message isn't an image.__"

        await msg.result("Creating sticker...")

        sticker_bytes = await reply_msg.download_media(file=bytes)
        sticker_buf = io.BytesIO(sticker_bytes)

        path = f"stickers/{name}.webp"
        await self.img_to_sticker(sticker_buf, {"webp": path})

        self.db.put(name, path)
        self.bot.dispatch_event_nowait("stat_event", "stickers_created")
        return f"Sticker saved to disk as `{name}`."

    @command.desc("Glitch an image")
    async def cmd_glitch(self, msg, boffset_str):
        if not msg.is_reply and not msg.file:
            return "__Reply to an image to glitch it.__"

        boffset = 8
        if boffset_str:
            try:
                boffset = int(boffset_str)
            except ValueError:
                return "__Invalid distorted block offset strength.__"

        if msg.file:
            reply_msg = msg
        else:
            reply_msg = await msg.get_reply_message()

        if not reply_msg.file:
            return "__That message isn't an image.__"

        await msg.result("Glitching image...")

        orig_bytes = await reply_msg.download_media(file=bytes)

        # Convert to PNG if necessary
        if orig_bytes.startswith(PNG_MAGIC):
            png_bytes = orig_bytes
        else:
            png_buf = io.BytesIO(orig_bytes)
            await self.img_to_png(png_buf)
            png_bytes = png_buf.getvalue()

        # Invoke external 'corrupter' program to glitch the image
        # Source code: https://github.com/r00tman/corrupter
        command = ["corrupter", "-boffset", str(boffset), "-"]
        try:
            proc = await util.run_sync(
                lambda: subprocess.run(
                    command, input=png_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=15
                )
            )
        except subprocess.TimeoutExpired:
            return "🕑 `corrupter` failed to finish within 15 seconds."
        except subprocess.CalledProcessError as err:
            return f"⚠️ `corrupter` failed with return code {err.returncode}. Error: ```{err.stderr}```"
        except FileNotFoundError:
            return "❌ The `corrupter` [program](https://github.com/r00tman/corrupter) must be installed on the host system."

        glitched_bytes = proc.stdout
        await msg.respond(file=glitched_bytes, reply_to=msg.reply_to_msg_id)
        await msg.delete()
