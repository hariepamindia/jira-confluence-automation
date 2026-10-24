import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class ConfigurationError(ValueError):
    """Raised when required application settings are invalid or missing."""


def load_env_file(path: Path, base: Mapping[str, str] | None = None) -> dict[str, str]:
    """Load literal KEY=VALUE settings, with process environment taking precedence."""
    result = dict(base if base is not None else os.environ)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise ConfigurationError(f"Could not read environment file {path}: {error}") from error

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            raise ConfigurationError(
                f"Invalid setting on line {line_number} of {path}; expected KEY=VALUE."
            )
        name, value = stripped.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", name):
            raise ConfigurationError(
                f"Invalid environment variable name on line {line_number} of {path}."
            )
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        result.setdefault(name, value)
    return result


def _csv(
    env: Mapping[str, str], name: str, default: str = ""
) -> tuple[str, ...]:
    return tuple(
        item.strip() for item in env.get(name, default).split(",") if item.strip()
    )


def _integer(
    env: Mapping[str, str], name: str, default: int, minimum: int = 1
) -> int:
    try:
        value = int(env.get(name, str(default)))
    except ValueError as error:
        raise ConfigurationError(f"{name} must be an integer.") from error
    if value < minimum:
        raise ConfigurationError(f"{name} must be at least {minimum}.")
    return value


def _boolean(env: Mapping[str, str], name: str, default: bool = False) -> bool:
    raw = env.get(name, str(default)).strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(f"{name} must be true or false.")


@dataclass(frozen=True)
class Settings:
    project_name: str
    timezone_name: str
    jira_base_url: str | None
    jira_email: str | None
    jira_api_token: str | None
    jira_jql: str | None
    jira_timeout_seconds: int
    jira_page_size: int
    jira_max_retries: int
    jira_story_points_field: str | None
    done_statuses: tuple[str, ...]
    in_progress_statuses: tuple[str, ...]
    blocked_statuses: tuple[str, ...]
    blocked_labels: tuple[str, ...]
    at_risk_labels: tuple[str, ...]
    at_risk_priorities: tuple[str, ...]
    due_soon_days: int
    red_blocked_threshold: int
    red_overdue_threshold: int
    yellow_risk_threshold: int
    smtp_host: str | None
    smtp_port: int
    smtp_max_retries: int
    smtp_sender: str | None
    smtp_recipients: tuple[str, ...]
    smtp_username: str | None
    smtp_password: str | None
    smtp_use_ssl: bool
    smtp_starttls: bool

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone_name)

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str] | None = None,
        *,
        require_jira: bool = True,
        require_email: bool = False,
    ) -> "Settings":
        values = os.environ if env is None else env
        timezone_name = values.get("REPORT_TIMEZONE", "UTC").strip()
        try:
            ZoneInfo(timezone_name)
        except (ZoneInfoNotFoundError, ValueError) as error:
            raise ConfigurationError(
                "REPORT_TIMEZONE must be a valid IANA timezone."
            ) from error

        jira_base_url = values.get("JIRA_BASE_URL", "").strip().rstrip("/") or None
        jira_email = values.get("JIRA_EMAIL", "").strip() or None
        jira_api_token = values.get("JIRA_API_TOKEN", "").strip() or None
        jira_jql = values.get("JIRA_JQL", "").strip() or None
        if jira_base_url:
            parsed_url = urlparse(jira_base_url)
            if parsed_url.scheme != "https" or not parsed_url.netloc:
                raise ConfigurationError("JIRA_BASE_URL must be an HTTPS URL.")
        if require_jira:
            missing = [
                name
                for name, value in (
                    ("JIRA_BASE_URL", jira_base_url),
                    ("JIRA_EMAIL", jira_email),
                    ("JIRA_API_TOKEN", jira_api_token),
                    ("JIRA_JQL", jira_jql),
                )
                if not value
            ]
            if missing:
                raise ConfigurationError(
                    "Missing Jira configuration: " + ", ".join(missing) + "."
                )

        smtp_host = values.get("SMTP_HOST", "").strip() or None
        smtp_sender = values.get("SMTP_SENDER", "").strip() or None
        smtp_recipients = _csv(values, "SMTP_RECIPIENTS")
        smtp_username = values.get("SMTP_USERNAME", "").strip() or None
        smtp_password = values.get("SMTP_PASSWORD", "").strip() or None
        if require_email:
            missing = [
                name
                for name, value in (
                    ("SMTP_HOST", smtp_host),
                    ("SMTP_SENDER", smtp_sender),
                    ("SMTP_RECIPIENTS", smtp_recipients),
                )
                if not value
            ]
            if missing:
                raise ConfigurationError(
                    "Missing email configuration: " + ", ".join(missing) + "."
                )
            if bool(smtp_username) != bool(smtp_password):
                raise ConfigurationError(
                    "Set both SMTP_USERNAME and SMTP_PASSWORD, or neither."
                )

        story_points_field = (
            values.get("JIRA_STORY_POINTS_FIELD", "customfield_10016").strip()
            or None
        )
        project_name = values.get("REPORT_PROJECT_NAME", "Jira Project").strip()
        if not project_name:
            raise ConfigurationError("REPORT_PROJECT_NAME must not be empty.")

        return cls(
            project_name=project_name,
            timezone_name=timezone_name,
            jira_base_url=jira_base_url,
            jira_email=jira_email,
            jira_api_token=jira_api_token,
            jira_jql=jira_jql,
            jira_timeout_seconds=_integer(values, "JIRA_TIMEOUT_SECONDS", 20),
            jira_page_size=_integer(values, "JIRA_PAGE_SIZE", 100),
            jira_max_retries=_integer(values, "JIRA_MAX_RETRIES", 3),
            jira_story_points_field=story_points_field,
            done_statuses=tuple(
                status.casefold()
                for status in _csv(
                    values, "REPORT_DONE_STATUSES", "Done,Closed,Resolved"
                )
            ),
            in_progress_statuses=tuple(
                status.casefold()
                for status in _csv(
                    values,
                    "REPORT_IN_PROGRESS_STATUSES",
                    "In Progress,In Review",
                )
            ),
            blocked_statuses=tuple(
                status.casefold()
                for status in _csv(values, "REPORT_BLOCKED_STATUSES", "Blocked")
            ),
            blocked_labels=tuple(
                label.casefold()
                for label in _csv(values, "REPORT_BLOCKED_LABELS", "blocked")
            ),
            at_risk_labels=tuple(
                label.casefold()
                for label in _csv(values, "REPORT_AT_RISK_LABELS", "at-risk,risk")
            ),
            at_risk_priorities=tuple(
                priority.casefold()
                for priority in _csv(
                    values, "REPORT_AT_RISK_PRIORITIES", "Highest,High"
                )
            ),
            due_soon_days=_integer(values, "REPORT_DUE_SOON_DAYS", 7),
            red_blocked_threshold=_integer(
                values, "REPORT_RED_BLOCKED_THRESHOLD", 1
            ),
            red_overdue_threshold=_integer(
                values, "REPORT_RED_OVERDUE_THRESHOLD", 1
            ),
            yellow_risk_threshold=_integer(
                values, "REPORT_YELLOW_RISK_THRESHOLD", 1
            ),
            smtp_host=smtp_host,
            smtp_port=_integer(values, "SMTP_PORT", 587),
            smtp_max_retries=_integer(values, "SMTP_MAX_RETRIES", 3),
            smtp_sender=smtp_sender,
            smtp_recipients=smtp_recipients,
            smtp_username=smtp_username,
            smtp_password=smtp_password,
            smtp_use_ssl=_boolean(values, "SMTP_USE_SSL"),
            smtp_starttls=_boolean(values, "SMTP_STARTTLS", True),
        )
