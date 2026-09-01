"""Minimal local-dev process supervisor (ADR-0002 invariant 6).

Not a production service manager -- Epic 13 replaces this with
containerized/systemd supervision on Linux. This exists only so local
Windows development has one command that starts all four processes and
restarts one that exits unexpectedly, proving the supervisor half of
ADR-0002's "starts and observes processes independently."

Crash detection watches the *real* interpreter pid (see
app.contracts.proc_utils), not the immediate subprocess.Popen handle --
on Windows, uv's venv python.exe is a trampoline whose own exit does not
reliably track the actual process it launched.
"""

from __future__ import annotations

import signal
import subprocess
import sys
import time
from dataclasses import dataclass

from app.contracts.proc_utils import is_alive, kill_tree, resolve_real_pid

MODULE_FOR_ROLE = {
    "api": "app.main",
    "engine": "app.engine.core",
    "feedd": "app.feedd.core",
    "worker": "app.worker.core",
}

POLL_INTERVAL_S = 1.0


@dataclass
class Child:
    popen: subprocess.Popen[bytes]
    real_pid: int


class Supervisor:
    def __init__(self, roles: tuple[str, ...] = tuple(MODULE_FOR_ROLE)) -> None:
        self.roles = roles
        self.children: dict[str, Child] = {}
        self._stopping = False

    def _spawn(self, role: str) -> Child:
        module = MODULE_FOR_ROLE[role]
        popen = subprocess.Popen([sys.executable, "-m", module])
        real_pid = resolve_real_pid(popen)
        print(f"[supervisor] started {role} (pid={real_pid})", flush=True)
        return Child(popen=popen, real_pid=real_pid)

    def start_all(self) -> None:
        for role in self.roles:
            self.children[role] = self._spawn(role)

    def stop_all(self) -> None:
        self._stopping = True
        for role, child in self.children.items():
            if is_alive(child.real_pid):
                print(f"[supervisor] stopping {role} (pid={child.real_pid})", flush=True)
        for child in self.children.values():
            kill_tree(child.real_pid)
            kill_tree(child.popen.pid)
        for child in self.children.values():
            try:
                child.popen.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass

    def poll_and_restart(self) -> None:
        if self._stopping:
            return
        for role, child in list(self.children.items()):
            if not is_alive(child.real_pid):
                print(f"[supervisor] {role} (pid={child.real_pid}) is gone; restarting", flush=True)
                self.children[role] = self._spawn(role)

    def run_forever(self) -> None:
        self.start_all()

        def _handle_signal(signum: int, _frame: object) -> None:
            print(f"[supervisor] received signal {signum}, shutting down", flush=True)
            self.stop_all()
            sys.exit(0)

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)

        try:
            while True:
                time.sleep(POLL_INTERVAL_S)
                self.poll_and_restart()
        except KeyboardInterrupt:
            self.stop_all()


def main() -> None:
    Supervisor().run_forever()


if __name__ == "__main__":
    main()
