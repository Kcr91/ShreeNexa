"""Process-identity helpers working around a Windows-specific quirk.

uv creates each venv's Scripts/python.exe as a small "trampoline" that
re-spawns the real base CPython interpreter as a *child* process rather
than exec-replacing itself (Windows has no POSIX exec()). That means
`subprocess.Popen([sys.executable, ...]).pid` is the trampoline's pid, not
the actual running interpreter's -- and the trampoline's own exit does not
reliably track its child's lifetime either. Both the supervisor's
crash-detection and any test asserting "this pid is the same/different
process" need the *real* descendant pid, found here via psutil.

On platforms without this trampoline (Linux/macOS, or a non-uv venv),
`Popen.pid` already is the real process; `resolve_real_pid` detects that
case (no child appears) and returns it unchanged.
"""

from __future__ import annotations

import subprocess
import time

import psutil

_HANDOFF_GRACE_S = 2.0
_HANDOFF_POLL_S = 0.05


def resolve_real_pid(popen: subprocess.Popen[bytes], grace_s: float = _HANDOFF_GRACE_S) -> int:
    """Return the pid of the process actually running our target module."""
    trampoline = psutil.Process(popen.pid)
    deadline = time.time() + grace_s
    while time.time() < deadline:
        try:
            children = trampoline.children(recursive=True)
        except psutil.NoSuchProcess:
            children = []
        if children:
            return int(children[-1].pid)
        time.sleep(_HANDOFF_POLL_S)
    # No child appeared -- this platform/venv has no trampoline; Popen.pid
    # is already the real process.
    return int(popen.pid)


def is_alive(pid: int) -> bool:
    return bool(psutil.pid_exists(pid))


def kill_tree(pid: int, timeout: float = 5.0) -> None:
    """Kill a pid and every descendant it (or a trampoline handoff) spawned."""
    try:
        proc = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return

    procs = [proc, *proc.children(recursive=True)]
    for p in procs:
        try:
            p.kill()
        except psutil.NoSuchProcess:
            pass
    psutil.wait_procs(procs, timeout=timeout)
