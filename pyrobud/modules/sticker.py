import asyncio
import io
import os
from datetime import datetime
from pathlib import Path
from typing import ClassVar, Optional, Set, Tuple

import telethon as tg

from .. import command, module, util

PNG_MAGIC = b"\x89\x50\x4e\x47\x0d\x0a\x1a\x0a"

# Sticker bot info and return error strings
STICKER_BOT_USERNAME = "Stickers"


class LengthMismatchError(Exception):
    pass


class StickerModule(module.Module):
    name: ClassVar[str] = "Sticker"
    db: util.db.AsyncDB
    settings_db: util.db.AsyncDB

    async def on_load(self):
        self.db = self.bot.get_db("stickers")
        self.settings_db = self.bot.get_db("sticker_settings")

    async def add_sticker(
        self,
        sticker_data: tg.hints.FileLike,
        pack_name: str,
        emoji: str = "❓",
        *,
        target: str = STICKER_BOT_USERNAME,
    ) -> Tuple[bool, str]:
        commands = [
            # We don't check this response because it's just a precautionary measure
            # Could be either failure (most likely) or success
            ("text", "/cancel", None),
            ("text", "/addsticker", "Choose the sticker pack"),
            ("text", pack_name, "send me the sticker"),
            ("file", sticker_data, "send me an emoji"),
            ("text", emoji, "added your sticker"),
            ("text", "/done", "done"),
        ]

        success = False
        before = datetime.now()

        async with self.bot.client.conversation(target) as conv:

            async def reply_and_ack():
                # Wait for a response
                resp = await conv.get_response()
                # Ack the response to suppress its notification
                await conv.mark_read()

                return resp

            try:
                for cmd_type, data, expected_resp in commands:
                    if cmd_type == "text":
                        await conv.send_message(data)
                    elif cmd_type == "file":
                        await conv.send_file(data, force_document=True)
                    else:
                        raise TypeError(f"Unknown command type '{cmd_type}'")

                    # Wait for both the rate-limit and the bot's response
                    try:
                        done: Set[asyncio.Future]
                        resp_task = self.bot.loop.create_task(reply_and_ack())
                        done, _ = await asyncio.wait((resp_task, asyncio.sleep(0.25)))
                        # Raise exceptions encountered in coroutines
                        for fut in done:
                            fut.result()

                        response = resp_task.result()
                        if expected_resp and expected_resp not in response.raw_text:
                            return False, f'Sticker creation failed: "{response.text}"'
                    except asyncio.TimeoutError:
                        after = datetime.now()
                        delta_seconds = int((after - before).total_seconds())

                        return (
                            False,
                            f"Sticker creation timed out after {delta_seconds} seconds.",
                        )

                success = True
            finally:
                # Cancel the operation if we return early
                if not success:
                    await conv.send_message("/cancel")

        return True, f"https://t.me/addstickers/{pack_name}"

    @command.desc("Copy a sticker into another pack")
    @command.alias("stickercopy", "scopy", "copys", "scp", "cps", "kang")
    @command.usage("[sticker pack short name? if not set] [emoji?]", optional=True)
    async def cmd_copysticker(self, ctx: command.Context) -> str:
        if not ctx.msg.is_reply:
            return "__Reply to a sticker to copy it.__"

        pack_name = None
        emoji = ""

        for arg in ctx.args:
            if util.text.has_emoji(arg):
                # Allow for emoji split across several arguments, since some clients
                # automatically insert spaces
                emoji += arg
            else:
                pack_name = arg

        if not pack_name:
            pack_name = await self.settings_db.get("kang_pack")
            if not pack_name:
                return "__Specify the name of the pack to add the sticker to.__"
        else:
            await self.settings_db.put("kang_pack", pack_name)

        reply_msg = await ctx.msg.get_reply_message()
        if not reply_msg.sticker:
            return "__That message isn't a sticker.__"

        await ctx.respond("Copying sticker...")

        sticker_bytes = await reply_msg.download_media(file=bytes)
        sticker_buf = io.BytesIO(sticker_bytes)
        await util.image.img_to_png(sticker_buf)

        sticker_buf.seek(0)
        sticker_buf.name = "sticker.png"
        status, result = await self.add_sticker(
            sticker_buf, pack_name, emoji=emoji or reply_msg.file.emoji
        )
        if status:
            await self.bot.log_stat("stickers_created")
            return f"[Sticker copied]({result})."

        return result

    @command.desc("Save a sticker with a name (as a reference)")
    @command.usage("[new sticker name]")
    async def cmd_save(self, ctx: command.Context) -> str:
        name = ctx.input

        if not ctx.msg.is_reply:
            return "__Reply to a sticker to save it.__"

        if await self.db.has(name):
            return "__There's already a sticker with that name.__"

        reply_msg = await ctx.msg.get_reply_message()
        if not reply_msg.sticker:
            return "__That message isn't a sticker.__"

        await self.db.put(name, reply_msg.file.id)
        return f"Sticker saved as `{name}`."

    @command.desc("Save a sticker with a name (to disk)")
    @command.usage("[new sticker name]")
    async def cmd_saved(self, ctx: command.Context) -> str:
        name = ctx.input

        if not ctx.msg.is_reply:
            return "__Reply to a sticker to save it.__"

        if await self.db.has(name):
            return "__There's already a sticker with that name.__"

        reply_msg = await ctx.msg.get_reply_message()
        if not reply_msg.sticker:
            return "__That message isn't a sticker.__"

        f_path = Path("stickers") / f"{name}.webp"
        path = await util.tg.download_file(
            ctx, reply_msg, dest=f_path, file_type="sticker"
        )
        if not path:
            return "__Error downloading sticker__"

        await self.db.put(name, path)
        return f"Sticker saved to disk as `{name}`."

    @command.desc("List saved stickers")
    async def cmd_stickers(self, ctx: command.Context) -> str:
        out = ["**Stickers saved:**"]

        key: str
        value: str
        async for key, value in self.db:
            typ = "local" if value.endswith(".webp") else "reference"
            out.append(f"{key} ({typ})")

        if len(out) == 1:
            return "__No stickers saved.__"

        return util.text.join_list(out)

    @command.desc("List locally saved stickers")
    async def cmd_stickersp(self, ctx: command.Context) -> str:
        out = ["**Stickers saved:**"]

        key: str
        value: str
        async for key, value in self.db:
            if value.endswith(".webp"):
                out.append(key)

        if len(out) == 1:
            return "__No stickers saved.__"

        return util.text.join_list(out)

    @command.desc("Delete a saved sticker")
    @command.usage("[sticker name]")
    async def cmd_sdel(self, ctx: command.Context) -> str:
        name = ctx.input

        if not await self.db.has(name):
            return "__That sticker doesn't exist.__"

        await self.db.delete(name)
        return f"Sticker `{name}` deleted."

    @command.desc("Fetch a sticker by name")
    @command.usage("[sticker name]")
    async def cmd_s(self, ctx: command.Context) -> Optional[str]:
        name = ctx.input

        path = await self.db.get(name)
        if path is None:
            return "__That sticker doesn't exist.__"

        await ctx.respond("Uploading sticker...")
        await ctx.respond(file=path, mode="repost")

    @command.desc("Fetch a sticker by name and send it as a photo")
    @command.usage("[sticker name]")
    @command.alias("sphoto")
    async def cmd_sp(self, ctx: command.Context) -> Optional[str]:
        name = ctx.input

        _webp_path: Optional[str] = await self.db.get(name)
        if _webp_path is None:
            return "__That sticker doesn't exist.__"

        webp_path = Path(_webp_path)
        if webp_path.suffix != ".webp":
            return "__That sticker can't be sent as a photo.__"

        await ctx.respond("Uploading sticker...")
        png_path = webp_path.with_suffix(".png")
        if not os.path.isfile(png_path):
            await util.image.img_to_png(webp_path, dest=png_path)

        await ctx.respond(file=png_path, mode="repost")
        return None

    @command.desc("Create a sticker from an image and add it to the given pack")
    @command.usage("[sticker pack name] [emoji to associate?]")
    async def cmd_sticker(self, ctx: command.Context) -> Optional[str]:
        if not (ctx.msg.is_reply or ctx.msg.file):
            return "__Reply to or embed an image to sticker it.__"

        reply_msg = ctx.msg if ctx.msg.file else await ctx.msg.get_reply_message()
        if not reply_msg.file:
            return "__That message doesn't contain an image.__"

        pack_name = ctx.args[0]
        emoji = ctx.args[1] if len(ctx.args) > 1 else "❓"

        await ctx.respond("Creating sticker...")

        sticker_bytes = await reply_msg.download_media(file=bytes)
        sticker_buf = io.BytesIO(sticker_bytes)

        png_buf = io.BytesIO()
        webp_buf = io.BytesIO()
        await util.image.img_to_sticker(sticker_buf, {"png": png_buf, "webp": webp_buf})

        png_buf.seek(0)
        png_buf.name = "sticker.png"
        status, result = await self.add_sticker(png_buf, pack_name, emoji=emoji)
        if status:
            await self.bot.log_stat("stickers_created")
            await ctx.respond(f"[Sticker created]({result}). Preview:")

            webp_buf.seek(0)
            webp_buf.name = "sticker.webp"
            await ctx.msg.respond(file=webp_buf)
            return None

        return result

    @command.desc(
        "Create a sticker from an image and save it to disk under the given name"
    )
    @command.usage("[new sticker name]")
    async def cmd_qstick(self, ctx: command.Context) -> str:
        name = ctx.input

        if not (ctx.msg.is_reply or ctx.msg.file):
            return "__Reply to an image to sticker it.__"

        if await self.db.has(name):
            return "__There's already a sticker with that name.__"

        reply_msg = ctx.msg if ctx.msg.file else await ctx.msg.get_reply_message()
        if not reply_msg.file:
            return "__That message isn't an image.__"

        await ctx.respond("Creating sticker...")

        sticker_bytes = await reply_msg.download_media(file=bytes)
        sticker_buf = io.BytesIO(sticker_bytes)

        path = Path("stickers") / f"{name}.webp"
        await util.image.img_to_sticker(sticker_buf, {"webp": path})

        await self.db.put(name, str(path))
        await self.bot.log_stat("stickers_created")
        return f"Sticker saved to disk as `{name}`."

    @command.desc("Glitch an image")
    @command.usage("[block offset strength?]", optional=True)
    async def cmd_glitch(self, ctx: command.Context) -> Optional[str]:
        if not (ctx.msg.is_reply or ctx.msg.file):
            return "__Reply to an image to glitch it.__"

        offset = 8
        if ctx.input:
            try:
                offset = int(ctx.input)
            except ValueError:
                return "__Invalid distorted block offset strength.__"

        reply_msg = ctx.msg if ctx.msg.file else await ctx.msg.get_reply_message()
        if not reply_msg.file:
            return "__That message isn't an image.__"

        await ctx.respond("Glitching image...")

        orig_bytes = await reply_msg.download_media(file=bytes)

        # Convert to PNG if necessary
        if orig_bytes.startswith(PNG_MAGIC):
            png_bytes = orig_bytes
        else:
            png_buf = io.BytesIO(orig_bytes)
            await util.image.img_to_png(png_buf)
            png_bytes = png_buf.getvalue()

        # Invoke external 'corrupter' program to glitch the image
        # Source code: https://github.com/r00tman/corrupter
        try:
            stdout, stderr, ret = await util.system.run_command(
                "corrupter",
                "-boffset",
                str(offset),
                "-",
                stderr=asyncio.subprocess.PIPE,
                in_data=png_bytes,
                text=util.system.StderrOnly,
                timeout=15,
            )
        except asyncio.TimeoutError:
            return "🕑 `corrupter` failed to finish within 15 seconds."
        except FileNotFoundError:
            return "❌ The `corrupter` [program](https://github.com/r00tman/corrupter) must be installed on the host system."

        if ret != 0:
            return (
                f"⚠️ `corrupter` failed with return code {ret}. Error: ```{stderr}```"
            )

        await ctx.respond(file=stdout, mode="repost")
        return None
