from typing import Any, Iterable, Mapping, Optional

import emoji.unicode_codes

ITEM_SEPARATOR = "\n    • "


def join_list(items: Iterable[str]) -> str:
    """Joins the given items into an indented bullet list."""

    return ITEM_SEPARATOR.join(items)


def join_map(
    items: Mapping[str, Any],
    heading: Optional[str] = None,
    parse_mode: str = "markdown",
) -> str:
    """Joins the given key-value pairs into an indented bullet list, with bolded labels."""

    if parse_mode == "html":
        start = "<b>"
        end = "</b>"
    else:
        start = "**"
        end = "**"

    return join_list(
        (
            *((f"{start}{heading}:{end}",) if heading else ()),
            *(f"{start}{key}:{end} {value}" for key, value in items.items()),
        )
    )


def has_emoji(text: str) -> bool:
    return any(c in emoji.unicode_codes.UNICODE_EMOJI for c in text)
