import io
import os
from typing import IO, Mapping, Optional, Union

from PIL import Image

from .async_helpers import run_sync

FileLike = Union[str, os.PathLike, IO[bytes]]
FormatMap = Mapping[str, FileLike]


async def img_to_png(src: FileLike, dest: Optional[FileLike] = None) -> FileLike:
    """Coverts the given image to a PNG using Pillow."""

    if dest is None:
        dest = src

    def _img_to_png() -> None:
        im = Image.open(src).convert("RGBA")
        if isinstance(dest, io.BufferedIOBase):
            dest.seek(0)
        im.save(dest, "png")

    await run_sync(_img_to_png)
    return dest


async def img_to_sticker(src: FileLike, formats: FormatMap) -> FormatMap:
    """Coverts the given image to a Telegram WebP sticker PNG using Pillow."""

    def _img_to_sticker() -> None:
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

    await run_sync(_img_to_sticker)
    return formats
