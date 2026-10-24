import io
import json
import os
import smtplib
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from email.message import EmailMessage
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from status_reporter.cli import main
from status_reporter.config import ConfigurationError, Settings, load_env_file
from status_reporter.email_delivery import DeliveryError, send_report
from status_reporter.jira import fetch_issues, normalize_issue
from status_reporter.reporting import build_report
from status_reporter.rendering import render_report, render_subject

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "weekly_issues.json"
PERIOD_START = date(2026, 10, 19)
PERIOD_END = date(2026, 10, 25)


def _settings(**overrides):
    values = {
        "REPORT_PROJECT_NAME": "Example Project",
        "REPORT_TIMEZONE": "UTC",
        "REPORT_YELLOW_RISK_THRESHOLD": "2",
    }
    values.update(overrides)
    return Settings.from_env(values, require_jira=False)


def _issues(settings=None):
    selected = settings or _settings()
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return [
        normalize_issue(item, selected.timezone, selected.jira_story_points_field)
        for item in fixture["issues"]
    ]


def _smtp_mock():
    client = MagicMock()
    client.__enter__.return_value = client
    client.send_message.return_value = {}
    return client


class ConfigurationTests(unittest.TestCase):
    def test_jira_settings_are_required_for_live_use(self):
        with self.assertRaisesRegex(ConfigurationError, "JIRA_BASE_URL"):
            Settings.from_env({}, require_jira=True)

    def test_email_requires_host_sender_and_recipients(self):
        with self.assertRaisesRegex(ConfigurationError, "SMTP_HOST"):
            Settings.from_env({}, require_jira=False, require_email=True)

    def test_invalid_timezone_is_rejected(self):
        with self.assertRaisesRegex(ConfigurationError, "REPORT_TIMEZONE"):
            Settings.from_env(
                {"REPORT_TIMEZONE": "Not/AZone"}, require_jira=False
            )

    def test_smtp_auth_requires_username_and_password_together(self):
        with self.assertRaisesRegex(ConfigurationError, "both SMTP_USERNAME"):
            Settings.from_env(
                {
                    "SMTP_HOST": "smtp.example.com",
                    "SMTP_SENDER": "reports@example.com",
                    "SMTP_RECIPIENTS": "lead@example.com",
                    "SMTP_USERNAME": "reporter",
                },
                require_jira=False,
                require_email=True,
            )

    def test_http_jira_url_is_rejected_before_credentials_are_used(self):
        with self.assertRaisesRegex(ConfigurationError, "HTTPS"):
            Settings.from_env(
                {
                    "JIRA_BASE_URL": "http://jira.example.com",
                    "JIRA_EMAIL": "bot@example.com",
                    "JIRA_API_TOKEN": "secret",
                    "JIRA_JQL": "project = EXAMPLE",
                }
            )

    def test_env_file_does_not_override_process_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.env"
            path.write_text(
                '# example\nREPORT_PROJECT_NAME="File Project"\n',
                encoding="utf-8",
            )
            loaded = load_env_file(
                path, {"REPORT_PROJECT_NAME": "Process Project"}
            )
        self.assertEqual(loaded["REPORT_PROJECT_NAME"], "Process Project")


class JiraNormalizationTests(unittest.TestCase):
    def test_normalizes_optional_values_and_timezone(self):
        issue = _issues()[2]
        self.assertEqual(issue.key, "EXAMPLE-103")
        self.assertIsNone(issue.assignee)
        self.assertEqual(issue.updated_date.isoformat(), "2026-10-23T11:00:00+00:00")
        self.assertEqual(issue.due_date, date(2026, 10, 20))
        self.assertIsNone(issue.story_points)

    def test_missing_required_status_is_reported_with_issue_key(self):
        raw = {"key": "EXAMPLE-9", "fields": {"summary": "Missing status"}}
        with self.assertRaisesRegex(ValueError, "EXAMPLE-9"):
            normalize_issue(raw, _settings().timezone, None)

    def test_null_optional_collections_are_normalized_to_empty(self):
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))["issues"][2]
        raw["fields"]["labels"] = None
        raw["fields"]["components"] = None
        raw["fields"]["fixVersions"] = None
        issue = normalize_issue(raw, _settings().timezone, None)
        self.assertEqual(issue.labels, ())
        self.assertEqual(issue.components, ())
        self.assertEqual(issue.versions, ())

    def test_invalid_date_reports_issue_key(self):
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))["issues"][0]
        raw["fields"]["updated"] = "not-a-date"
        with self.assertRaisesRegex(ValueError, "EXAMPLE-101"):
            normalize_issue(raw, _settings().timezone, None)

    @patch("status_reporter.jira.time.sleep")
    @patch("status_reporter.jira.urlopen")
    def test_paginates_and_retries_rate_limit(self, urlopen, sleep):
        settings = _settings(
            JIRA_BASE_URL="https://example.atlassian.net",
            JIRA_EMAIL="bot@example.com",
            JIRA_API_TOKEN="test-secret",
            JIRA_JQL="project = EXAMPLE",
            JIRA_PAGE_SIZE="2",
            JIRA_MAX_RETRIES="2",
        )
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))["issues"]

        def response(payload):
            mock = MagicMock()
            mock.__enter__.return_value.read.return_value = json.dumps(payload).encode()
            return mock

        rate_limit = HTTPError(
            "https://example.atlassian.net",
            429,
            "Too Many Requests",
            {"Retry-After": "0"},
            io.BytesIO(b""),
        )
        urlopen.side_effect = [
            rate_limit,
            response({"total": 3, "issues": fixture[:2]}),
            response({"total": 3, "issues": fixture[2:]}),
        ]
        issues = fetch_issues(settings)
        self.assertEqual([issue.key for issue in issues], [
            "EXAMPLE-101", "EXAMPLE-102", "EXAMPLE-103"
        ])
        self.assertEqual(urlopen.call_count, 3)
        sleep.assert_called_once_with(0.0)


class ReportingTests(unittest.TestCase):
    def test_builds_metrics_health_and_milestone_progress(self):
        settings = _settings(REPORT_YELLOW_RISK_THRESHOLD="1")
        report = build_report(
            _issues(settings),
            settings,
            PERIOD_START,
            PERIOD_END,
            today=date(2026, 10, 24),
        )
        self.assertEqual(report.health, "Red")
        self.assertEqual(report.total_issues, 3)
        self.assertEqual(report.open_issues, 2)
        self.assertEqual(len(report.completed_issues), 1)
        self.assertEqual(len(report.in_progress_issues), 1)
        self.assertEqual(len(report.blocked_issues), 1)
        self.assertEqual(len(report.at_risk_issues), 2)
        self.assertEqual(len(report.overdue_issues), 1)
        self.assertEqual(len(report.due_soon_issues), 1)
        self.assertEqual(report.milestones[0].name, "October Release")
        self.assertEqual(report.milestones[0].completed_issues, 1)

    def test_health_thresholds_can_be_configured(self):
        settings = _settings(
            REPORT_RED_BLOCKED_THRESHOLD="2",
            REPORT_RED_OVERDUE_THRESHOLD="2",
            REPORT_YELLOW_RISK_THRESHOLD="3",
            REPORT_DUE_SOON_DAYS="3",
        )
        report = build_report(
            _issues(settings),
            settings,
            PERIOD_START,
            PERIOD_END,
            today=date(2026, 10, 24),
        )
        self.assertEqual(report.health, "Green")

    def test_empty_scope_is_not_reported_as_green(self):
        report = build_report(
            [],
            _settings(),
            PERIOD_START,
            PERIOD_END,
            today=date(2026, 10, 24),
        )
        self.assertEqual(report.health, "Yellow")
        self.assertIn("No Jira issues", report.health_reasons[0])

    def test_period_end_before_start_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "cannot precede"):
            build_report(
                [],
                _settings(),
                PERIOD_END,
                PERIOD_START,
            )


class RenderingAndDeliveryTests(unittest.TestCase):
    def test_render_includes_required_sections_and_week_subject(self):
        settings = _settings()
        report = build_report(
            _issues(settings),
            settings,
            PERIOD_START,
            PERIOD_END,
            today=date(2026, 10, 24),
        )
        body = render_report(report, settings.due_soon_days)
        self.assertEqual(
            render_subject(report),
            "[Weekly Status] Example Project - Week of 2026-10-19",
        )
        for section in (
            "Project Health:",
            "Highlights / Completed Work",
            "Current Risks and Blockers",
            "Milestone Status",
            "Upcoming Actions",
            "Recommended Next Steps",
        ):
            self.assertIn(section, body)
        self.assertIn("EXAMPLE-101", body)

    @patch("status_reporter.email_delivery.smtplib.SMTP")
    def test_delivery_uses_configured_subject_and_recipients(self, smtp_class):
        settings = _settings(
            SMTP_HOST="smtp.example.com",
            SMTP_SENDER="reports@example.com",
            SMTP_RECIPIENTS="lead@example.com,team@example.com",
        )
        report = build_report(
            _issues(settings),
            settings,
            PERIOD_START,
            PERIOD_END,
            today=date(2026, 10, 24),
        )
        client = _smtp_mock()
        smtp_class.return_value = client
        send_report(report, settings)
        message = client.send_message.call_args.args[0]
        self.assertIsInstance(message, EmailMessage)
        self.assertEqual(message["To"], "lead@example.com, team@example.com")
        self.assertIn("2026-10-19", message["Subject"])

    @patch("status_reporter.email_delivery.smtplib.SMTP")
    def test_delivery_rejection_is_not_reported_as_success(self, smtp_class):
        settings = _settings(
            SMTP_HOST="smtp.example.com",
            SMTP_SENDER="reports@example.com",
            SMTP_RECIPIENTS="lead@example.com",
        )
        report = build_report([], settings, PERIOD_START, PERIOD_END)
        client = _smtp_mock()
        smtp_class.return_value = client
        client.send_message.return_value = {"lead@example.com": (550, b"rejected")}
        with self.assertRaisesRegex(DeliveryError, "refused delivery"):
            send_report(report, settings)

    @patch("status_reporter.email_delivery.time.sleep")
    @patch("status_reporter.email_delivery.smtplib.SMTP")
    def test_temporary_smtp_response_is_retried(self, smtp_class, sleep):
        settings = _settings(
            SMTP_HOST="smtp.example.com",
            SMTP_SENDER="reports@example.com",
            SMTP_RECIPIENTS="lead@example.com",
            SMTP_MAX_RETRIES="2",
        )
        report = build_report([], settings, PERIOD_START, PERIOD_END)
        first = _smtp_mock()
        first.send_message.side_effect = smtplib.SMTPDataError(
            451, b"temporary failure"
        )
        second = _smtp_mock()
        smtp_class.side_effect = [first, second]
        send_report(report, settings)
        self.assertEqual(smtp_class.call_count, 2)
        sleep.assert_called_once_with(1)

    @patch("status_reporter.email_delivery.time.sleep")
    @patch("status_reporter.email_delivery.smtplib.SMTP")
    def test_transient_connection_failure_is_retried(self, smtp_class, sleep):
        settings = _settings(
            SMTP_HOST="smtp.example.com",
            SMTP_SENDER="reports@example.com",
            SMTP_RECIPIENTS="lead@example.com",
            SMTP_MAX_RETRIES="2",
        )
        report = build_report([], settings, PERIOD_START, PERIOD_END)
        successful_client = _smtp_mock()
        smtp_class.side_effect = [OSError("connection unavailable"), successful_client]
        send_report(report, settings)
        self.assertEqual(smtp_class.call_count, 2)
        sleep.assert_called_once_with(1)


class CliTests(unittest.TestCase):
    def test_fixture_run_defaults_to_dry_run(self):
        output = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), redirect_stdout(output):
            result = main(
                [
                    "--fixture",
                    str(FIXTURE),
                    "--period-start",
                    "2026-10-19",
                    "--period-end",
                    "2026-10-25",
                ]
            )
        self.assertEqual(result, 0)
        self.assertIn("Weekly Status Report", output.getvalue())
        self.assertIn("Current Risks and Blockers", output.getvalue())

    def test_send_requires_smtp_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            result = main(["--fixture", str(FIXTURE), "--send"])
        self.assertEqual(result, 1)


if __name__ == "__main__":
    unittest.main()
