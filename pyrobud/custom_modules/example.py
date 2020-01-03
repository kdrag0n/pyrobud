import asyncio
import io
from pathlib import PurePosixPath
from typing import IO

import telethon as tg

from .. import command, module, util


class ExampleModule(module.Module):
    name = "Example"
    disabled = True

    db: util.db.AsyncDB

    async def on_load(self) -> None:
        self.db = self.bot.get_db("example")

    async def on_message(self, event: tg.events.NewMessage.Event) -> None:
        self.log.info(f"Received message: {event.message}")
        await self.db.inc("messages_received")

    @command.desc("Simple echo/test command")
    @command.alias("echotest", "test2")
    @command.usage("[text to echo?, or reply]", optional=True, reply=True)
    async def cmd_test(self, ctx: command.Context) -> str:
        await ctx.respond("Processing...")
        await asyncio.sleep(1)

        if ctx.input:
            return ctx.input
        else:
            return "It works!"

    async def get_cat(self) -> IO[bytes]:
        # Get the link to a random cat picture
        async with self.bot.http.get("https://aws.random.cat/meow") as resp:
            # Read and parse the response as JSON
            json = await resp.json()
            # Get the "file" field from the parsed JSON object
            cat_url = json["file"]

        # Get the actual cat picture
        async with self.bot.http.get(cat_url) as resp:
            # Get the data as a byte array (bytes object)
            cat_data = await resp.read()

        # Construct a byte stream from the data.
        # This is necessary because the bytes object is immutable, but we need to add a "name" attribute to set the
        # filename. This facilitates the setting of said attribute without altering behavior.
        cat_stream = io.BytesIO(cat_data)

        # Set the name of the cat picture before sending.
        # This is necessary for Telethon to detect the file type and send it as a photo/GIF rather than just a plain
        # unnamed file that doesn't render as media in clients.
        # We abuse pathlib to extract the filename section here for convenience, since URLs are *mostly* POSIX paths
        # with the exception of the protocol part, which we don't care about here.
        cat_stream.name = PurePosixPath(cat_url).name

        return cat_stream

    @command.desc("Get a random cat picture")
    async def cmd_cat(self, ctx: command.Context) -> None:
        await ctx.respond("Fetching cat...")
        cat_stream = await self.get_cat()

        await ctx.respond(file=cat_stream, mode="repost")
