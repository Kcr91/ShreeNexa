"""Management commands: console-script entry points for the four processes
plus the local-dev supervisor (per ADR-0004, an approved namespace).

Wired in pyproject.toml [project.scripts] as exactly `api`, `engine`,
`feedd`, `worker`, `supervisor` -- ADR-0004 requires these names not be
renamed.
"""

from __future__ import annotations


def run_api() -> None:
    from app.main import run

    run()


def run_engine() -> None:
    from app.engine.core import run

    run()


def run_feedd() -> None:
    from app.feedd.core import run

    run()


def run_worker() -> None:
    from app.worker.core import run

    run()


def run_supervisor() -> None:
    from app.cli.supervisor import main

    main()
