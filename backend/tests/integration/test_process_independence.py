"""The literal F0.3 proof: killing/restarting one process never affects
another's durable heartbeat -- and the local-dev supervisor restarts a
process that dies unexpectedly.

Each test spawns real OS processes via `python -m <module>` directly. On
Windows, uv's venv python.exe is a trampoline that re-spawns the real
interpreter as a *child* process (see app.contracts.proc_utils); killing
only the trampoline (`Popen.kill()`) leaves the real process running as an
orphan, which then keeps writing heartbeats and collides with whatever the
next test spawns for the same process_name. Every kill here goes through
`kill_tree`, which kills the real descendant too.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import datetime

import pytest
from app.contracts import heartbeat as hb
from app.contracts.proc_utils import is_alive, kill_tree, resolve_real_pid
from conftest import DATABASE_URL
from sqlalchemy.engine import Engine

MODULE_FOR_ROLE = {
    "api": "app.main",
    "engine": "app.engine.core",
    "feedd": "app.feedd.core",
    "worker": "app.worker.core",
}

WAIT_TIMEOUT_S = 10.0
POLL_INTERVAL_S = 0.2


@pytest.fixture()
def process_env(postgres_or_skip: str) -> dict[str, str]:
    """Also clears process_heartbeat first: these tests key rows by the real
    process_name ("engine", "api", ...), so a row left over from a previous
    run would otherwise race with this test's own spawned process."""
    engine = hb.make_engine()
    try:
        with engine.begin() as conn:
            conn.execute(hb.process_heartbeat.delete())
    finally:
        engine.dispose()
    return {**os.environ, "DATABASE_URL": DATABASE_URL}


def _spawn(role: str, env: dict[str, str]) -> tuple[subprocess.Popen[bytes], int]:
    popen = subprocess.Popen([sys.executable, "-m", MODULE_FOR_ROLE[role]], env=env)
    return popen, resolve_real_pid(popen)


def _wait_for[T](
    poll: Callable[[], T | None],
    timeout: float = WAIT_TIMEOUT_S,
    interval: float = POLL_INTERVAL_S,
) -> T:
    """Poll until `poll()` returns a non-None/non-False value, and return it."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = poll()
        if result:
            return result
        time.sleep(interval)
    pytest.fail(f"condition not met within {timeout}s")


def _row(engine: Engine, process_name: str) -> hb.HeartbeatRow | None:
    return hb.read(engine, process_name)


def _row_advanced(
    engine: Engine, process_name: str, after: datetime
) -> hb.HeartbeatRow | None:
    row = hb.read(engine, process_name)
    if row is not None and row.last_heartbeat_at > after:
        return row
    return None


def _row_with_pid(engine: Engine, process_name: str, pid: int) -> hb.HeartbeatRow | None:
    row = hb.read(engine, process_name)
    if row is not None and row.pid == pid:
        return row
    return None


def _gone(pid: int) -> bool | None:
    return True if not is_alive(pid) else None


def test_kill_api_does_not_affect_engine(process_env: dict[str, str]) -> None:
    engine = hb.make_engine()
    real_pids: list[int] = []
    try:
        _, engine_pid = _spawn("engine", process_env)
        real_pids.append(engine_pid)
        engine_row = _wait_for(lambda: _row(engine, "engine"))
        engine_started_at = engine_row.started_at
        assert engine_row.pid == engine_pid

        # Prove engine is actually heartbeating (advancing), not a static row.
        _wait_for(lambda: _row_advanced(engine, "engine", engine_row.last_heartbeat_at))

        _, api_pid = _spawn("api", process_env)
        real_pids.append(api_pid)
        _wait_for(lambda: _row(engine, "api"))

        # Forceful kill of the *real* api process -- not SIGTERM/graceful.
        # api never gets to run its own shutdown code. The point: engine
        # must not even notice.
        kill_tree(api_pid)
        _wait_for(lambda: _gone(api_pid))
        api_last = hb.read(engine, "api")
        assert api_last is not None

        before = hb.read(engine, "engine")
        assert before is not None
        after = _wait_for(lambda: _row_advanced(engine, "engine", before.last_heartbeat_at))
        assert after.pid == engine_pid, "engine restarted its own process -- it must not"
        assert after.started_at == engine_started_at
        assert after.status == "running"

        # api's row must not have advanced since the forceful kill.
        time.sleep(1.5)
        api_after = hb.read(engine, "api")
        assert api_after is not None
        assert api_after.last_heartbeat_at == api_last.last_heartbeat_at

        # Restarting api gets a fresh pid, independent of engine.
        _, api_pid_2 = _spawn("api", process_env)
        real_pids.append(api_pid_2)
        assert api_pid_2 != api_pid
        restarted = _wait_for(lambda: _row_with_pid(engine, "api", api_pid_2))
        assert restarted.pid == api_pid_2
    finally:
        for pid in real_pids:
            kill_tree(pid)


def test_kill_engine_forcefully_leaves_durable_last_heartbeat(process_env: dict[str, str]) -> None:
    engine = hb.make_engine()
    _, real_pid = _spawn("engine", process_env)
    try:
        row = _wait_for(lambda: _row(engine, "engine"))
        assert row.pid == real_pid
        _wait_for(lambda: _row_advanced(engine, "engine", row.last_heartbeat_at))
        before_kill = hb.read(engine, "engine")
        assert before_kill is not None

        kill_tree(real_pid)
        _wait_for(lambda: _gone(real_pid))

        after_kill = hb.read(engine, "engine")
        assert after_kill is not None
        assert after_kill.last_heartbeat_at >= before_kill.last_heartbeat_at
        assert after_kill.pid == real_pid
        # Forceful kill skips the graceful-shutdown path, so status is still
        # "running" -- the row reflects the last value it durably committed,
        # never a value that only ever existed in memory.
        assert after_kill.status == "running"
    finally:
        kill_tree(real_pid)


def test_supervisor_restarts_a_killed_child(process_env: dict[str, str]) -> None:
    from app.cli.supervisor import Supervisor

    engine = hb.make_engine()
    sup = Supervisor(roles=("engine", "feedd"))
    sup.start_all()
    try:
        _wait_for(lambda: _row(engine, "engine"))
        _wait_for(lambda: _row(engine, "feedd"))

        old_engine_pid = sup.children["engine"].real_pid
        old_feedd_pid = sup.children["feedd"].real_pid
        engine_row = hb.read(engine, "engine")
        assert engine_row is not None
        assert engine_row.pid == old_engine_pid

        kill_tree(old_engine_pid)
        _wait_for(lambda: _gone(old_engine_pid))

        sup.poll_and_restart()
        assert sup.children["engine"].real_pid != old_engine_pid, (
            "supervisor did not restart the child"
        )
        assert sup.children["feedd"].real_pid == old_feedd_pid, (
            "supervisor touched an untouched sibling"
        )

        new_pid = sup.children["engine"].real_pid
        _wait_for(lambda: _row_with_pid(engine, "engine", new_pid))
    finally:
        sup.stop_all()
