import io
import json
import os
import smtplib
import ssl
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from email.message import EmailMessage
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse

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


def _jira_settings(**overrides):
    values = {
        "JIRA_BASE_URL": "https://example.atlassian.net",
        "JIRA_EMAIL": "bot@example.com",
        "JIRA_API_TOKEN": "test-secret",
        "JIRA_PROJECT_KEY": "EXAMPLE",
        "JIRA_PROJECT_TIMEZONE": "UTC",
        "JIRA_JQL": "project = EXAMPLE ORDER BY updated DESC",
        "JIRA_PAGE_SIZE": "2",
        "JIRA_MAX_RETRIES": "2",
    }
    values.update(overrides)
    return _settings(**values)


def _jira_response(payload):
    response = MagicMock()
    response.__enter__.return_value.read.return_value = json.dumps(payload).encode()
    return response


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

    def test_live_configuration_requires_jira_project_timezone(self):
        values = {
            "JIRA_BASE_URL": "https://example.atlassian.net",
            "JIRA_EMAIL": "bot@example.com",
            "JIRA_API_TOKEN": "secret",
            "JIRA_PROJECT_KEY": "EXAMPLE",
            "JIRA_JQL": "project = EXAMPLE",
            "REPORT_TIMEZONE": "UTC",
        }
        with self.assertRaisesRegex(ConfigurationError, "JIRA_PROJECT_TIMEZONE"):
            Settings.from_env(values)

    def test_live_jira_configuration_accepts_project_scoped_settings(self):
        settings = Settings.from_env(
            {
                "JIRA_BASE_URL": "https://example.atlassian.net",
                "JIRA_EMAIL": "bot@example.com",
                "JIRA_API_TOKEN": "test-secret",
                "JIRA_PROJECT_KEY": "EXAMPLE",
                "JIRA_PROJECT_TIMEZONE": "America/New_York",
                "JIRA_JQL": "project = EXAMPLE ORDER BY updated DESC",
            }
        )
        self.assertEqual(settings.jira_project_key, "EXAMPLE")
        self.assertEqual(settings.timezone_name, "America/New_York")
        self.assertEqual(
            settings.jira_required_fields,
            ("key", "summary", "status", "assignee", "duedate"),
        )

    def test_jira_scope_must_match_configured_project(self):
        with self.assertRaisesRegex(ConfigurationError, "JIRA_JQL"):
            Settings.from_env(
                {
                    "JIRA_PROJECT_KEY": "EXAMPLE",
                    "JIRA_JQL": "project = OTHER",
                },
                require_jira=False,
            )

    def test_approved_status_mapping_cannot_be_overridden(self):
        with self.assertRaisesRegex(ConfigurationError, "approved mappings"):
            Settings.from_env(
                {
                    "REPORT_STATUS_MAPPINGS":
                        "To Do=Active,In Progress=Active,Blocked=Blocked,Done=Completed"
                },
                require_jira=False,
            )

    def test_status_categories_drive_legacy_status_sets(self):
        settings = Settings.from_env(
            {
                "REPORT_STATUS_MAPPINGS":
                    "To Do=Planned,In Progress=Active,Blocked=Blocked,"
                    "Done=Completed,On Hold=Active"
            },
            require_jira=False,
        )
        self.assertIn("on hold", settings.in_progress_statuses)
        self.assertEqual(settings.done_statuses, ("done",))
        with self.assertRaisesRegex(ConfigurationError, "REPORT_STATUS_MAPPINGS"):
            Settings.from_env(
                {"REPORT_DONE_STATUSES": "Done,Resolved"},
                require_jira=False,
            )

    def test_health_thresholds_and_report_detail_limit_are_bounded(self):
        with self.assertRaisesRegex(ConfigurationError, "thresholds"):
            Settings.from_env(
                {
                    "REPORT_HEALTH_GREEN_MAX_PERCENT": "20",
                    "REPORT_HEALTH_YELLOW_MAX_PERCENT": "10",
                },
                require_jira=False,
            )
        with self.assertRaisesRegex(ConfigurationError, "at most 100"):
            Settings.from_env(
                {"REPORT_DETAIL_LIMIT": "101"}, require_jira=False
            )

    def test_smtp_requires_tls_and_valid_unique_recipients(self):
        with self.assertRaisesRegex(ConfigurationError, "requires TLS"):
            Settings.from_env(
                {
                    "SMTP_HOST": "smtp.example.com",
                    "SMTP_USE_SSL": "false",
                    "SMTP_STARTTLS": "false",
                },
                require_jira=False,
            )
        with self.assertRaisesRegex(ConfigurationError, "not both"):
            Settings.from_env(
                {
                    "SMTP_HOST": "smtp.example.com",
                    "SMTP_USE_SSL": "true",
                    "SMTP_STARTTLS": "true",
                },
                require_jira=False,
            )
        with self.assertRaisesRegex(ConfigurationError, "single valid email"):
            Settings.from_env(
                {"SMTP_RECIPIENTS": "good@example.com,not-an-email"},
                require_jira=False,
            )
        with self.assertRaisesRegex(ConfigurationError, "duplicates"):
            Settings.from_env(
                {
                    "SMTP_RECIPIENTS":
                        "lead@example.com,LEAD@example.com"
                },
                require_jira=False,
            )

    def test_database_and_retention_settings_are_validated(self):
        with self.assertRaisesRegex(ConfigurationError, "PostgreSQL URL"):
            Settings.from_env(
                {"DATABASE_URL": "https://db.example.com/reporting"},
                require_jira=False,
            )
        with self.assertRaisesRegex(ConfigurationError, "at least 1"):
            Settings.from_env(
                {"AUDIT_RETENTION_DAYS": "0"}, require_jira=False
            )
        with self.assertRaisesRegex(ConfigurationError, "must be 90"):
            Settings.from_env(
                {"AUDIT_RETENTION_DAYS": "120"}, require_jira=False
            )
        with self.assertRaisesRegex(ConfigurationError, "DATABASE_URL"):
            Settings.from_env({}, require_jira=False, require_database=True)

    def test_validation_errors_do_not_echo_credentials(self):
        secret = "never-print-this-token"
        with self.assertRaises(ConfigurationError) as raised:
            Settings.from_env(
                {
                    "JIRA_API_TOKEN": secret,
                    "SMTP_RECIPIENTS": "not-an-email",
                },
                require_jira=False,
            )
        self.assertNotIn(secret, str(raised.exception))

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

    def test_malformed_urls_raise_actionable_configuration_errors(self):
        with self.assertRaisesRegex(ConfigurationError, "JIRA_BASE_URL"):
            Settings.from_env(
                {"JIRA_BASE_URL": "https://[invalid"},
                require_jira=False,
            )
        with self.assertRaisesRegex(ConfigurationError, "DATABASE_URL"):
            Settings.from_env(
                {"DATABASE_URL": "postgresql://[invalid/db"},
                require_jira=False,
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
        settings = _jira_settings()
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))["issues"]

        rate_limit = HTTPError(
            "https://example.atlassian.net",
            429,
            "Too Many Requests",
            {"Retry-After": "0"},
            io.BytesIO(b""),
        )
        urlopen.side_effect = [
            rate_limit,
            _jira_response(
                {"startAt": 0, "maxResults": 2, "total": 3, "issues": fixture[:2]}
            ),
            _jira_response(
                {"startAt": 2, "maxResults": 2, "total": 3, "issues": fixture[2:]}
            ),
        ]
        issues = fetch_issues(settings)
        self.assertEqual(
            [issue.key for issue in issues],
            ["EXAMPLE-101", "EXAMPLE-102", "EXAMPLE-103"],
        )
        self.assertEqual(urlopen.call_count, 3)
        sleep.assert_called_once_with(0.0)
        for call, expected_start in zip(
            urlopen.call_args_list, (0, 0, 2), strict=True
        ):
            request = call.args[0]
            parsed_url = urlparse(request.full_url)
            self.assertEqual(parsed_url.path, "/rest/api/3/search")
            parameters = parse_qs(parsed_url.query)
            self.assertEqual(parameters["jql"], [settings.jira_jql])
            self.assertEqual(parameters["startAt"], [str(expected_start)])
            self.assertEqual(parameters["maxResults"], ["2"])
            requested_fields = set(parameters["fields"][0].split(","))
            self.assertTrue(
                {
                    "summary",
                    "status",
                    "assignee",
                    "project",
                    "duedate",
                    "created",
                    "updated",
                    "resolutiondate",
                    "labels",
                    "components",
                    "fixVersions",
                }.issubset(requested_fields)
            )
            self.assertEqual(request.get_header("Accept"), "application/json")
            self.assertTrue(
                request.get_header("Authorization").startswith("Basic ")
            )
            self.assertTrue(call.kwargs["context"].check_hostname)
            self.assertEqual(
                call.kwargs["context"].verify_mode,
                ssl.CERT_REQUIRED,
            )

    @patch("status_reporter.jira.time.sleep")
    @patch("status_reporter.jira.urlopen")
    def test_permanent_http_failure_is_not_retried(self, urlopen, sleep):
        urlopen.side_effect = HTTPError(
            "https://example.atlassian.net",
            401,
            "Unauthorized",
            {},
            io.BytesIO(b"secret response details"),
        )
        with self.assertRaisesRegex(RuntimeError, "HTTP 401") as raised:
            fetch_issues(_jira_settings())
        self.assertNotIn("test-secret", str(raised.exception))
        self.assertEqual(urlopen.call_count, 1)
        sleep.assert_not_called()

    @patch("status_reporter.jira.time.sleep")
    @patch("status_reporter.jira.urlopen")
    def test_retry_exhaustion_fails_without_returning_partial_issues(
        self, urlopen, sleep
    ):
        urlopen.side_effect = [
            _jira_response(
                {
                    "startAt": 0,
                    "maxResults": 2,
                    "total": 3,
                    "issues": json.loads(FIXTURE.read_text(encoding="utf-8"))[
                        "issues"
                    ][:2],
                }
            ),
            HTTPError(
                "https://example.atlassian.net",
                503,
                "Service Unavailable",
                {},
                io.BytesIO(b""),
            ),
            HTTPError(
                "https://example.atlassian.net",
                503,
                "Service Unavailable",
                {},
                io.BytesIO(b""),
            ),
        ]
        with self.assertRaisesRegex(RuntimeError, "HTTP 503"):
            fetch_issues(_jira_settings())
        self.assertEqual(urlopen.call_count, 3)
        sleep.assert_called_once_with(1)

    @patch("status_reporter.jira.urlopen")
    def test_malformed_or_incomplete_pages_fail_closed(self, urlopen):
        cases = (
            (
                {"issues": [], "total": 0},
                "pagination metadata",
            ),
            (
                {"startAt": 0, "maxResults": 2, "total": 1, "issues": []},
                "empty page",
            ),
            (
                {
                    "startAt": 0,
                    "maxResults": 2,
                    "total": 1,
                    "issues": [{}, {}],
                },
                "inconsistent pagination",
            ),
        )
        for payload, message in cases:
            with self.subTest(payload=payload):
                urlopen.reset_mock()
                urlopen.return_value = _jira_response(payload)
                with self.assertRaisesRegex(RuntimeError, message):
                    fetch_issues(_jira_settings(JIRA_MAX_RETRIES="1"))

    @patch("status_reporter.jira.urlopen")
    def test_invalid_json_response_fails_visibly(self, urlopen):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b"{not json"
        urlopen.return_value = response
        with self.assertRaisesRegex(RuntimeError, "invalid JSON"):
            fetch_issues(_jira_settings(JIRA_MAX_RETRIES="1"))

    @patch("status_reporter.jira.time.sleep")
    @patch("status_reporter.jira.urlopen")
    def test_transient_network_failure_retries(self, urlopen, sleep):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))["issues"][:1]
        urlopen.side_effect = [
            URLError(ConnectionError("temporarily unavailable")),
            _jira_response(
                {
                    "startAt": 0,
                    "maxResults": 2,
                    "total": 1,
                    "issues": fixture,
                }
            ),
        ]
        self.assertEqual(len(fetch_issues(_jira_settings())), 1)
        self.assertEqual(urlopen.call_count, 2)
        sleep.assert_called_once_with(1)

    @patch("status_reporter.jira.urlopen")
    def test_tls_certificate_failure_is_not_retried(self, urlopen):
        urlopen.side_effect = URLError(ssl.SSLCertVerificationError("invalid cert"))
        with self.assertRaisesRegex(RuntimeError, "non-retryable"):
            fetch_issues(_jira_settings())
        self.assertEqual(urlopen.call_count, 1)

    @patch("status_reporter.jira.urlopen")
    def test_duplicate_issue_keys_are_returned_once(self, urlopen):
        issue = json.loads(FIXTURE.read_text(encoding="utf-8"))["issues"][0]
        urlopen.return_value = _jira_response(
            {
                "startAt": 0,
                "maxResults": 2,
                "total": 2,
                "issues": [issue, issue],
            }
        )
        result = fetch_issues(_jira_settings())
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].key, "EXAMPLE-101")


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
