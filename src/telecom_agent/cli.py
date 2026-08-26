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
    SeedResult,
    seed_synthetic_customer,
)
from telecom_agent.adapters.sambanova.current_plan_answers import SambaNovaSettings
from telecom_agent.api.composition import create_postgres_app
from telecom_agent.development import DEVELOPMENT_CUSTOMER


class ServerRunner(Protocol):
    def __call__(self, app: FastAPI, *, host: str, port: int) -> None: ...


class ApplicationFactory(Protocol):
    def __call__(
        self,
        database_url: str,
        sambanova_settings: SambaNovaSettings,
    ) -> FastAPI: ...


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
    app_factory: ApplicationFactory = create_postgres_app,
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

    required_model_settings = (
        "SAMBANOVA_BASE_URL",
        "SAMBANOVA_MODEL",
        "SAMBANOVA_API_KEY",
    )
    missing_model_settings = [
        name for name in required_model_settings if not environ.get(name)
    ]
    if missing_model_settings:
        print(
            "The serve command requires: " + ", ".join(missing_model_settings) + ".",
            file=error_output,
        )
        return 2

    sambanova_settings = SambaNovaSettings(
        base_url=environ["SAMBANOVA_BASE_URL"],
        model=environ["SAMBANOVA_MODEL"],
        api_key=environ["SAMBANOVA_API_KEY"],
    )
    app = app_factory(database_url, sambanova_settings)
    server_runner(app, host="127.0.0.1", port=8000)
    return 0


def main() -> int:
    return run_cli()
