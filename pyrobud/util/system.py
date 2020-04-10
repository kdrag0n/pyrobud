import asyncio
from typing import IO, Any, Optional, Sequence, Tuple, Union

ProcessCmdline = Union[str, bytes]
ProcessStream = Union[int, IO, None]


async def _spawn_exec(
    cmdline: Sequence[ProcessCmdline],
    in_data: Optional[bytes],
    stdout: ProcessStream,
    stderr: ProcessStream,
    **kwargs: Any
) -> asyncio.subprocess.Process:
    stdin = asyncio.subprocess.PIPE if in_data else None
    return await asyncio.create_subprocess_exec(*cmdline, stdin=stdin, stdout=stdout, stderr=stderr, **kwargs)


async def _spawn_shell(
    cmdline: ProcessCmdline, in_data: Optional[bytes], stdout: ProcessStream, stderr: ProcessStream, **kwargs: Any
) -> asyncio.subprocess.Process:
    stdin = asyncio.subprocess.PIPE if in_data else None
    return await asyncio.create_subprocess_shell(cmdline, stdin=stdin, stdout=stdout, stderr=stderr, **kwargs)


async def _get_proc_output(
    proc: asyncio.subprocess.Process, in_data: Optional[bytes], timeout: int
) -> Tuple[bytes, bytes, Optional[int]]:
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(in_data), timeout)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass

        raise
    return stdout, stderr, proc.returncode


async def run_command(
    *cmdline: ProcessCmdline,
    in_data: Optional[bytes] = None,
    stdout: ProcessStream = asyncio.subprocess.PIPE,
    stderr: ProcessStream = asyncio.subprocess.STDOUT,
    timeout: int = 0,
    **kwargs: Any
) -> Tuple[bytes, bytes, Optional[int]]:
    proc = await _spawn_exec(cmdline, in_data, stdout, stderr, **kwargs)
    return await _get_proc_output(proc, in_data, timeout)


async def run_command_shell(
    cmdline: ProcessCmdline,
    in_data: Optional[bytes] = None,
    stdout: ProcessStream = asyncio.subprocess.PIPE,
    stderr: ProcessStream = asyncio.subprocess.STDOUT,
    timeout: int = 0,
    **kwargs: Any
) -> Tuple[bytes, bytes, Optional[int]]:
    proc = await _spawn_shell(cmdline, in_data, stdout, stderr, **kwargs)
    return await _get_proc_output(proc, in_data, timeout)
