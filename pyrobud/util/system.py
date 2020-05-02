import asyncio
import sys
from typing import IO, Any, Optional, Sequence, Tuple, Union

ProcessData = Union[str, bytes]
ProcessStream = Union[int, IO, None]


class FormatType:
    pass


StderrOnly = FormatType()


def get_venv_path() -> Optional[str]:
    """Returns the current venv's path prefix, or None if not running in a venv."""

    if hasattr(sys, "real_prefix") or sys.base_prefix != sys.prefix:
        return sys.prefix

    return None


async def _spawn_exec(
    cmdline: Sequence[ProcessData],
    in_data: Optional[bytes],
    stdout: ProcessStream,
    stderr: ProcessStream,
    **kwargs: Any
) -> asyncio.subprocess.Process:
    stdin = asyncio.subprocess.PIPE if in_data else None
    return await asyncio.create_subprocess_exec(
        *cmdline, stdin=stdin, stdout=stdout, stderr=stderr, **kwargs
    )


async def _spawn_shell(
    cmdline: ProcessData,
    in_data: Optional[bytes],
    stdout: ProcessStream,
    stderr: ProcessStream,
    **kwargs: Any
) -> asyncio.subprocess.Process:
    stdin = asyncio.subprocess.PIPE if in_data else None
    return await asyncio.create_subprocess_shell(
        cmdline, stdin=stdin, stdout=stdout, stderr=stderr, **kwargs
    )


async def _get_proc_output(
    proc: asyncio.subprocess.Process,
    in_data: Optional[bytes],
    timeout: Optional[int],
    text: Union[bool, FormatType],
) -> Tuple[ProcessData, ProcessData, Optional[int]]:
    stdout: Any
    stderr: Any
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(in_data), timeout)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass

        raise

    if text:
        if text is not StderrOnly and stdout is not None:
            stdout = stdout.decode(errors="replace").strip()

        if stderr is not None:
            stderr = stderr.decode(errors="replace").strip()

    return stdout, stderr, proc.returncode


async def run_command(
    *cmdline: ProcessData,
    in_data: Optional[bytes] = None,
    stdout: ProcessStream = asyncio.subprocess.PIPE,
    stderr: ProcessStream = asyncio.subprocess.STDOUT,
    timeout: Optional[int] = None,
    shell: bool = False,
    text: Union[bool, FormatType] = True,
    **kwargs: Any
) -> Tuple[Any, Any, Optional[int]]:
    """Runs the given command (with optional input) using asyncio.subprocess."""

    if shell:
        proc = await _spawn_shell(cmdline[0], in_data, stdout, stderr, **kwargs)
    else:
        proc = await _spawn_exec(cmdline, in_data, stdout, stderr, **kwargs)

    return await _get_proc_output(proc, in_data, timeout, text)
