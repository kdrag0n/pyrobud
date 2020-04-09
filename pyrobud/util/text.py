from typing import Any, Iterable, Mapping, Optional

ITEM_SEPARATOR = "\n    • "


def join_list(items: Iterable[str]) -> str:
    return ITEM_SEPARATOR.join(items)


def join_map(items: Mapping[str, Any], heading: Optional[str] = None, parse_mode: str = "markdown") -> str:
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
