import argparse
import json
import logging
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from .config import ConfigurationError, Settings, load_env_file
from .email_delivery import DeliveryError, send_report
from .jira import fetch_issues, normalize_issues
from .reporting import build_report
from .rendering import render_report, render_subject

LOGGER = logging.getLogger("status_reporter")


def _period(today: date) -> tuple[date, date]:
    current_monday = today - timedelta(days=today.weekday())
    previous_monday = current_monday - timedelta(days=7)
    return previous_monday, current_monday - timedelta(days=1)


def _load_fixture(path: Path, settings: Settings) -> list:
    try:
        with path.open(encoding="utf-8") as fixture_file:
            payload: Any = json.load(fixture_file)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not read Jira fixture {path}: {error}") from error
    raw_issues = payload.get("issues") if isinstance(payload, dict) else payload
    if not isinstance(raw_issues, list):
        raise ValueError("Jira fixture must be a list or an object with an issues list.")
    return normalize_issues(
        raw_issues, settings.timezone, settings.jira_story_points_field
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a weekly Jira stakeholder report."
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        help="Read Jira search-result JSON from a local file instead of calling Jira.",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        help="Read literal KEY=VALUE settings from a file; process variables take precedence.",
    )
    parser.add_argument(
        "--period-start",
        type=date.fromisoformat,
        help="Inclusive reporting-period start date (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--period-end",
        type=date.fromisoformat,
        help="Inclusive reporting-period end date (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Send the report via SMTP. Without this option, only print a preview.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write the rendered report to this file instead of standard output.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        environment = (
            load_env_file(args.env_file)
            if args.env_file is not None
            else None
        )
        settings = Settings.from_env(
            environment,
            require_jira=args.fixture is None, require_email=args.send
        )
        default_start, default_end = _period(
            datetime.now(settings.timezone).date()
        )
        period_start = args.period_start or default_start
        period_end = args.period_end or default_end
        if period_end < period_start:
            raise ConfigurationError("--period-end cannot precede --period-start.")

        LOGGER.info(
            "Starting report for %s (%s through %s).",
            settings.project_name,
            period_start,
            period_end,
        )
        issues = (
            _load_fixture(args.fixture, settings)
            if args.fixture is not None
            else fetch_issues(settings)
        )
        report = build_report(
            issues, settings, period_start, period_end
        )
        body = render_report(report, settings.due_soon_days)
        if args.output is not None:
            args.output.write_text(body, encoding="utf-8")
            LOGGER.info("Report preview written to %s.", args.output)
        else:
            print(body)
        if args.send:
            delivery = send_report(report, settings)
            if delivery.failed_count:
                LOGGER.warning(
                    "Report delivery outcome: %s (%s accepted, %s failed).",
                    delivery.outcome,
                    delivery.accepted_count,
                    delivery.failed_count,
                )
            else:
                LOGGER.info(
                    "Report delivery outcome: %s (%s accepted).",
                    delivery.outcome,
                    delivery.accepted_count,
                )
        else:
            LOGGER.info("Dry run complete; no email was sent.")
        return 0
    except (ConfigurationError, DeliveryError, OSError, RuntimeError, ValueError) as error:
        LOGGER.error("%s", error)
        return 1


if __name__ == "__main__":
    sys.exit(main())
