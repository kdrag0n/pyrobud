import os.path
import subprocess
from typing import List, Union, Sequence, Any

from .async_helpers import run_sync

ProcessCmdline = Union[bytes, str, Sequence[Union[bytes, str]]]


def split_path(path: str) -> List[str]:
    return str(os.path.normpath(path)).lstrip(os.path.sep).split(os.path.sep)


async def run_command(cmdline: ProcessCmdline, **kwargs: Any):
    def _run_command() -> subprocess.CompletedProcess:
        return subprocess.run(
            cmdline, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, **kwargs
        )

    return await run_sync(_run_command)
