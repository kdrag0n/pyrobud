import asyncio
import os
import urllib.parse

import aiohttp
import telethon as tg

from .. import command, module, util


class NetworkModule(module.Module):
    name = "Network"

    @command.desc("Pong")
    async def cmd_ping(self, msg):
        before = util.time.msec()
        await msg.result("Calculating response time...")
        after = util.time.msec()

        return "Request response time: %d ms" % (after - before)

    async def get_text_input(self, msg, input_arg):
        if msg.is_reply:
            reply_msg = await msg.get_reply_message()

            if reply_msg.document:
                text = await util.tg.msg_download_file(reply_msg, msg)
            elif reply_msg.text:
                text = reply_msg.text
            else:
                return ("error", "__Reply to a message with text or a text file, or provide text in command.__")
        else:
            if input_arg:
                text = util.tg.filter_code_block(input_arg).encode()
            else:
                return ("error", "__Reply to a message or provide text in command.__")

        return ("success", text)

    @command.desc("Paste message text to Hastebin")
    @command.alias("hs")
    async def cmd_haste(self, msg, input_text):
        status, text = await self.get_text_input(msg, input_text)
        if status == "error":
            return text

        await msg.result("Uploading text to [Hastebin](https://hastebin.com/)...")

        async with self.bot.http_session.post("https://hastebin.com/documents", data=text) as resp:
            try:
                resp_data = await resp.json()
            except aiohttp.ContentTypeError:
                return "__Hastebin is currently experiencing issues. Try again later.__"

            return f'https://hastebin.com/{resp_data["key"]}'

    @command.desc("Paste message text to Dogbin")
    async def cmd_dog(self, msg, input_text):
        status, text = await self.get_text_input(msg, input_text)
        if status == "error":
            return text

        await msg.result("Uploading text to [Dogbin](https://del.dog/)...")

        async with self.bot.http_session.post("https://del.dog/documents", data=text) as resp:
            try:
                resp_data = await resp.json()
            except aiohttp.ContentTypeError:
                return "__Dogbin is currently experiencing issues. Try again later.__"

            return f'https://del.dog/{resp_data["key"]}'

    @command.desc("Upload given file to file.io")
    async def cmd_fileio(self, msg, expires):
        if not msg.is_reply:
            return "__Reply to a file to upload it.__"

        if expires == "help":
            return "__Expiry format: 1y/12m/52w/365d__"
        elif expires:
            if expires[-1] not in ["y", "m", "w", "d"]:
                return "__Unknown unit. Expiry format: 1y/12m/52w/365d__"
            else:
                try:
                    int(expires[:-1])
                except ValueError:
                    return "__Invalid number. Expiry format: 1y/12m/52w/365d__"
        else:
            expires = "2d"

        reply_msg = await msg.get_reply_message()
        if not reply_msg.document:
            return "__That message doesn't contain a file.__"

        data = await util.tg.msg_download_file(reply_msg, msg)

        await msg.result("Uploading file to [file.io](https://file.io/)...")

        async with self.bot.http_session.post(f"https://file.io/?expires={expires}", data={"file": data}) as resp:
            resp_data = await resp.json()

            if not resp_data["success"]:
                return f"__Error uploading file — status code {resp.status}__"

            return resp_data["link"]

    @command.desc("Upload given file to transfer.sh")
    async def cmd_transfer(self, msg):
        if not msg.is_reply:
            return "__Reply to a file to upload it.__"

        reply_msg = await msg.get_reply_message()
        if not reply_msg.document:
            return "__That message doesn't contain a file.__"

        data = await util.tg.msg_download_file(reply_msg, msg)

        await msg.result("Uploading file to [transfer.sh](https://transfer.sh/)...")

        filename = reply_msg.file.name
        async with self.bot.http_session.put(f"https://transfer.sh/{filename}", data=data) as resp:
            if resp.status != 200:
                return f"__Error uploading file — status code {resp.status}__"

            return await resp.text()

    @command.desc("Update the embed for a link")
    @command.alias("upde", "updl", "updatelink", "ul", "ulink")
    async def cmd_update_link(self, msg, link):
        if not link and not msg.is_reply:
            return "__Provide or reply to a link to update it.__"

        if not link:
            reply_msg = await msg.get_reply_message()

            for entity, text in reply_msg.get_entities_text():
                if isinstance(entity, (tg.types.MessageEntityUrl, tg.types.MessageEntityTextUrl)):
                    link = text

        if not link:
            return "__That message doesn't contain any links."

        await msg.result(f"Updating embed for [link]({link})...")

        async with self.bot.client.conversation("WebpageBot") as conv:
            await conv.send_message(link)

            response = await conv.get_response()
            await conv.mark_read()

            if "Link previews was updated successfully" in response.raw_text:
                # Provide a status update
                await msg.result("Waiting for embed update to propagate...")

                # Give Telegram some time to propagate the update
                await asyncio.sleep(1)

                # Send the new preview
                await msg.result(f"Updated embed for link: {link}", link_preview=True)
            else:
                # Failed for some reason, send the error
                await msg.result(f"Error updating embed for [link]({link}): `{response.raw_text}`")

    @command.desc("Generate a LMGTFY link (Let Me Google That For You)")
    async def cmd_lmgtfy(self, msg, query):
        if not query:
            return "__Provide the search terms to use in the link.__"

        params = urllib.parse.urlencode({"q": query})
        return f"https://lmgtfy.com/?{params}"
