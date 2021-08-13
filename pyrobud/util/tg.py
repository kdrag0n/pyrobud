import asyncio
import os
from datetime import datetime
from typing import Any, Optional, Tuple, Type, Union

import bprint
import telethon as tg

from .. import command

MESSAGE_CHAR_LIMIT = 4096
TRUNCATION_SUFFIX = "... (truncated)"

SKIP_ATTR_NAMES = (
    "CONSTRUCTOR_ID",
    "SUBCLASS_OF_ID",
    "access_hash",
    "message",
    "raw_text",
    "phone",
)
SKIP_ATTR_VALUES = (False,)
SKIP_ATTR_TYPES = ()


def mention_user(user: tg.types.User) -> str:
    """Returns a string that mentions the given user, regardless of whether they have a username."""

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
    """Returns the content inside the given Markdown code block or inline code."""

    if inp.startswith("```") and inp.endswith("```"):
        inp = inp[3:][:-3]
    elif inp.startswith("`") and inp.endswith("`"):
        inp = inp[1:][:-1]

    return inp


def _bprint_skip_predicate(name: str, value: Any) -> bool:
    return (
        name.startswith("_")
        or value is None
        or callable(value)
        or name in SKIP_ATTR_NAMES
        or value in SKIP_ATTR_VALUES
        or type(value) in SKIP_ATTR_TYPES
    )


def pretty_print_entity(entity: tg.tl.TLObject) -> str:
    """Pretty-prints the given Telegram entity with recursive details."""

    return bprint.bprint(entity, stream=str, skip_predicate=_bprint_skip_predicate)


async def download_file(
    ctx: command.Context,
    msg: tg.custom.Message,
    dest: Union[tg.hints.FileLike, os.PathLike, Type[bytes]] = bytes,
    file_type: str = "file",
) -> Any:
    """Downloads the file embedded in the given message with live progress updates."""

    last_update_time = None

    def prog_func(current_bytes: int, total_bytes: int) -> None:
        nonlocal last_update_time

        if not ctx:
            return

        # Only edit message once every 5 seconds to avoid ratelimits
        percent = int((current_bytes / total_bytes) * 100)
        now = datetime.now()
        if last_update_time is None or (now - last_update_time).total_seconds() >= 5:
            loop = asyncio.get_event_loop()
            loop.create_task(
                ctx.respond(f"Downloading {file_type}... {percent}% complete")
            )

            last_update_time = now

    return await msg.download_media(file=dest, progress_callback=prog_func)


def truncate(text: str) -> str:
    """Truncates the given text to fit in one Telegram message."""

    if len(text) > MESSAGE_CHAR_LIMIT:
        return text[: MESSAGE_CHAR_LIMIT - len(TRUNCATION_SUFFIX)] + TRUNCATION_SUFFIX

    return text


async def get_text_input(
    ctx: command.Context, input_arg: Optional[str]
) -> Tuple[bool, Optional[Union[str, bytes]]]:
    """Returns input text from various sources in the given command context."""

    if ctx.msg.document:
        bin_data = await download_file(ctx, ctx.msg)
        text = bin_data.decode(errors="replace")
    elif input_arg:
        text = filter_code_block(input_arg)
    elif ctx.msg.is_reply:
        reply_msg = await ctx.msg.get_reply_message()

        if reply_msg.document:
            bin_data = await download_file(ctx, reply_msg)
            text = bin_data.decode(errors="replace")
        elif reply_msg.text:
            text = filter_code_block(reply_msg.text)
        else:
            return (
                False,
                "__Reply to a message with text or a text file, or provide text in command.__",
            )
    else:
        return False, "__Reply to a message or provide text in command.__"

    return True, text
