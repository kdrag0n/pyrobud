import asyncio
import os
from typing import Union, Optional, Tuple, Type

import telethon as tg

from .. import command

TRUNCATION_SUFFIX = "... (truncated)"


def mention_user(user: tg.types.User) -> str:
    if user.username:
        # Use username mention if possible
        name = f"@{user.username}"
    else:
        # Use the first and last name otherwise
        name = tg.utils.get_display_name(user)
        if not name:
            # Deleted accounts have no name; behave like the official clients
            name = "Deleted Account"

    return f"[{name}](tg://user?id={user.id})"


def filter_code_block(inp: str) -> str:
    if inp.startswith("```") and inp.endswith("```"):
        inp = inp[3:][:-3]
    elif inp.startswith("`") and inp.endswith("`"):
        inp = inp[1:][:-1]

    return inp


async def download_file(
    ctx: command.Context,
    msg: tg.custom.Message,
    dest: Union[tg.hints.FileLike, os.PathLike, Type[bytes]] = bytes,
    file_type: str = "file",
) -> Union[str, bytes, None]:
    last_percent = -5

    def prog_func(current_bytes: int, total_bytes: int) -> None:
        nonlocal last_percent

        if not ctx:
            return

        # Only edit message if progress >= 5% to mitigate API flooding
        percent = int((current_bytes / total_bytes) * 100)
        if abs(percent - last_percent) >= 5:
            loop = asyncio.get_event_loop()
            loop.create_task(ctx.respond(f"Downloading {file_type}... {percent}% complete"))

        last_percent = percent

    return await msg.download_media(file=dest, progress_callback=prog_func)


def truncate(text: str) -> str:
    if len(text) > 4096:
        return text[: 4096 - len(TRUNCATION_SUFFIX)] + TRUNCATION_SUFFIX
    else:
        return text


async def get_text_input(ctx: command.Context, input_arg: Optional[str]) -> Tuple[bool, Optional[Union[str, bytes]]]:
    if ctx.msg.is_reply:
        reply_msg = await ctx.msg.get_reply_message()

        if reply_msg.document:
            text = await download_file(ctx, reply_msg)
        elif reply_msg.text:
            text = filter_code_block(reply_msg.text)
        else:
            return False, "__Reply to a message with text or a text file, or provide text in command.__"
    else:
        if ctx.msg.document:
            text = await download_file(ctx, ctx.msg)
        elif input_arg:
            text = filter_code_block(input_arg)
        else:
            return False, "__Reply to a message or provide text in command.__"

    return True, text
