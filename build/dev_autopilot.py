"""CLI for the bounded ShreeNexa local development autopilot.

Run from the repository root through the locked environment:
    python -m uv run python build/dev_autopilot.py run
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from autopilot.controller import AutopilotError, PilotController, Policy, atomic_write_json

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "build/autopilot/policy.yaml"


def make_controller() -> PilotController:
    return PilotController(REPO_ROOT, Policy.load(POLICY_PATH))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run", help="run the pilot in the foreground from a clean setup")
    subparsers.add_parser("resume", help="reconcile durable state and resume in the foreground")
    subparsers.add_parser("status", help="print redacted durable controller status")
    subparsers.add_parser("stop", help="request safe cancellation; evidence and branches remain")
    subparsers.add_parser("start", help="start a detached local controller process")
    internal = subparsers.add_parser("_run", help=argparse.SUPPRESS)
    internal.add_argument("--resume", action="store_true")
    return parser.parse_args(argv)


def start_detached() -> int:
    controller = make_controller()
    runtime = controller.runtime_root
    runtime.mkdir(parents=True, exist_ok=True)
    log_path = runtime / "launcher.log"
    command = [sys.executable, str(Path(__file__).resolve()), "_run"]
    creationflags = 0
    if os.name == "nt":
        creationflags = (
            subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.DETACHED_PROCESS
            | subprocess.CREATE_NO_WINDOW
        )
    with log_path.open("a", encoding="utf-8") as log:
        process = subprocess.Popen(
            command,
            cwd=REPO_ROOT,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
            close_fds=True,
        )
    atomic_write_json(runtime / "launcher.json", {"pid": process.pid, "command": "_run"})
    print(json.dumps({"started": True, "pid": process.pid, "status_command": status_command()}))
    return 0


def status_command() -> str:
    return "python -m uv run python build/dev_autopilot.py status"


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        controller = make_controller()
        if args.command == "status":
            print(json.dumps(controller.status(), indent=2, sort_keys=True))
            return 0
        if args.command == "stop":
            controller.request_stop()
            print("Stop requested; active work will be cancelled safely and evidence preserved.")
            return 0
        if args.command == "start":
            return start_detached()
        state = controller.run(resume=args.command == "resume" or getattr(args, "resume", False))
        print(json.dumps(state.__dict__, indent=2, sort_keys=True))
        return 0 if state.phase == "complete" else 2
    except AutopilotError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
