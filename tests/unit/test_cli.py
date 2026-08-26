from collections.abc import Mapping
from io import StringIO

from fastapi import FastAPI

from telecom_agent.adapters.postgres.seeding import SeedResult
from telecom_agent.adapters.sambanova.current_plan_answers import SambaNovaSettings
from telecom_agent.cli import run_cli

DATABASE_URL = "postgresql+psycopg://local/test"
SERVE_ENVIRONMENT = {
    "DATABASE_URL": DATABASE_URL,
    "SAMBANOVA_BASE_URL": "https://api.sambanova.ai/v1",
    "SAMBANOVA_MODEL": "MiniMax-M3",
    "SAMBANOVA_API_KEY": "test-key",
}


def test_seed_requires_database_url() -> None:
    stderr = StringIO()

    exit_code = run_cli(["seed"], environ={}, stderr=stderr)

    assert exit_code == 2
    assert stderr.getvalue() == (
        "DATABASE_URL is required. Load .env or export it before running this command.\n"
    )


def test_seed_reports_created_customer_and_development_token() -> None:
    stdout = StringIO()
    received_urls: list[str] = []

    def seed_customer(database_url: str) -> SeedResult:
        received_urls.append(database_url)
        return SeedResult.CREATED

    exit_code = run_cli(
        ["seed"],
        environ={"DATABASE_URL": DATABASE_URL},
        seed_customer=seed_customer,
        stdout=stdout,
    )

    assert exit_code == 0
    assert received_urls == [DATABASE_URL]
    assert stdout.getvalue() == (
        "Created Synthetic Alice. Development token: synthetic-alice-token\n"
    )


def test_seed_reports_existing_customer_when_repeated() -> None:
    stdout = StringIO()

    exit_code = run_cli(
        ["seed"],
        environ={"DATABASE_URL": DATABASE_URL},
        seed_customer=lambda _database_url: SeedResult.EXISTING,
        stdout=stdout,
    )

    assert exit_code == 0
    assert stdout.getvalue() == (
        "Synthetic Alice already exists. Development token: synthetic-alice-token\n"
    )


def test_serve_composes_database_app_and_binds_only_to_localhost() -> None:
    expected_app = FastAPI()
    compositions: list[tuple[str, SambaNovaSettings]] = []
    server_calls: list[tuple[FastAPI, str, int]] = []

    def app_factory(
        database_url: str,
        sambanova_settings: SambaNovaSettings,
    ) -> FastAPI:
        compositions.append((database_url, sambanova_settings))
        return expected_app

    def server_runner(app: FastAPI, *, host: str, port: int) -> None:
        server_calls.append((app, host, port))

    exit_code = run_cli(
        ["serve"],
        environ=SERVE_ENVIRONMENT,
        app_factory=app_factory,
        server_runner=server_runner,
    )

    assert exit_code == 0
    assert compositions == [
        (
            DATABASE_URL,
            SambaNovaSettings(
                base_url="https://api.sambanova.ai/v1",
                model="MiniMax-M3",
                api_key="test-key",
            ),
        )
    ]
    assert server_calls == [(expected_app, "127.0.0.1", 8000)]


def test_serve_reports_missing_sambanova_settings_without_exposing_values() -> None:
    stderr = StringIO()

    exit_code = run_cli(
        ["serve"],
        environ={"DATABASE_URL": DATABASE_URL, "SAMBANOVA_MODEL": "MiniMax-M3"},
        stderr=stderr,
    )

    assert exit_code == 2
    assert stderr.getvalue() == (
        "The serve command requires: SAMBANOVA_BASE_URL, SAMBANOVA_API_KEY.\n"
    )


def test_cli_uses_only_the_supplied_environment_mapping() -> None:
    environment: Mapping[str, str] = {}

    assert run_cli(["serve"], environ=environment, stderr=StringIO()) == 2
