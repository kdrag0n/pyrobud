import subprocess
from typing import Any, Sequence, Union

from .async_helpers import run_sync

ProcessCmdline = Union[bytes, str, Sequence[Union[bytes, str]]]


async def run_command(cmdline: ProcessCmdline, **kwargs: Any):
    def _run_command() -> subprocess.CompletedProcess:
        return subprocess.run(
            cmdline, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, **kwargs
        )

    return await run_sync(_run_command)
