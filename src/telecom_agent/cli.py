import argparse
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from typing import Protocol, TextIO

import uvicorn
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from telecom_agent.adapters.postgres.seeding import (
    DEVELOPMENT_CUSTOMER,
    SeedResult,
    seed_synthetic_customer,
)
from telecom_agent.api.composition import create_postgres_app


class ServerRunner(Protocol):
    def __call__(self, app: FastAPI, *, host: str, port: int) -> None: ...


def seed_development_customer(database_url: str) -> SeedResult:
    engine = create_engine(database_url)
    try:
        session_factory = sessionmaker[Session](engine, expire_on_commit=False)
        return seed_synthetic_customer(session_factory, DEVELOPMENT_CUSTOMER)
    finally:
        engine.dispose()


def run_cli(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] = os.environ,
    seed_customer: Callable[[str], SeedResult] = seed_development_customer,
    app_factory: Callable[[str], FastAPI] = create_postgres_app,
    server_runner: ServerRunner = uvicorn.run,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    output = stdout or sys.stdout
    error_output = stderr or sys.stderr
    parser = argparse.ArgumentParser(prog="telecom-agent")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("seed", help="Create approved synthetic development customers")
    commands.add_parser("serve", help="Start the localhost API")
    args = parser.parse_args(argv)

    database_url = environ.get("DATABASE_URL")
    if not database_url:
        print(
            "DATABASE_URL is required. Load .env or export it before running this command.",
            file=error_output,
        )
        return 2

    if args.command == "seed":
        result = seed_customer(database_url)
        if result is SeedResult.CREATED:
            action = "Created"
        else:
            action = f"{DEVELOPMENT_CUSTOMER.display_name} already exists."
            print(
                f"{action} Development token: {DEVELOPMENT_CUSTOMER.raw_token}",
                file=output,
            )
            return 0
        print(
            f"{action} {DEVELOPMENT_CUSTOMER.display_name}. "
            f"Development token: {DEVELOPMENT_CUSTOMER.raw_token}",
            file=output,
        )
        return 0

    app = app_factory(database_url)
    server_runner(app, host="127.0.0.1", port=8000)
    return 0


def main() -> int:
    return run_cli()
