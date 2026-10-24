import os
import re
from dataclasses import dataclass
from email.utils import parseaddr
from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_STATUS_CATEGORIES = {"Planned", "Active", "Blocked", "Completed"}
_REQUIRED_STATUS_MAPPINGS = {
    "to do": "Planned",
    "in progress": "Active",
    "blocked": "Blocked",
    "done": "Completed",
}
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
    env: Mapping[str, str],
    name: str,
    default: int,
    minimum: int = 1,
    maximum: int | None = None,
) -> int:
    try:
        value = int(env.get(name, str(default)))
    except ValueError as error:
        raise ConfigurationError(f"{name} must be an integer.") from error
    if value < minimum:
        raise ConfigurationError(f"{name} must be at least {minimum}.")
    if maximum is not None and value > maximum:
        raise ConfigurationError(f"{name} must be at most {maximum}.")
    return value


def _email_address(env: Mapping[str, str], name: str) -> str | None:
    raw = env.get(name, "").strip()
    if not raw:
        return None
    return _validate_email_address(raw, name)


def _validate_email_address(raw: str, name: str) -> str:
    display_name, address = parseaddr(raw)
    if (
        display_name
        or address != raw
        or "\r" in raw
        or "\n" in raw
        or not re.fullmatch(r"[^@\s]+@[^@\s.]+(?:\.[^@\s.]+)+", address)
    ):
        raise ConfigurationError(f"{name} must contain a single valid email address.")
    return address


def _status_mappings(env: Mapping[str, str]) -> tuple[tuple[str, str], ...]:
    raw = env.get(
        "REPORT_STATUS_MAPPINGS",
        "To Do=Planned,In Progress=Active,Blocked=Blocked,Done=Completed",
    )
    mappings: dict[str, tuple[str, str]] = {}
    for item in raw.split(","):
        if "=" not in item:
            raise ConfigurationError(
                "REPORT_STATUS_MAPPINGS entries must use Status=Category."
            )
        status, category = (part.strip() for part in item.split("=", 1))
        if not status or category not in _STATUS_CATEGORIES:
            raise ConfigurationError(
                "REPORT_STATUS_MAPPINGS has an empty status or unsupported category."
            )
        normalized_status = status.casefold()
        if normalized_status in mappings:
            raise ConfigurationError(
                "REPORT_STATUS_MAPPINGS must not contain duplicate statuses."
            )
        mappings[normalized_status] = (status, category)

    for status, expected_category in _REQUIRED_STATUS_MAPPINGS.items():
        configured = mappings.get(status)
        if configured is None or configured[1] != expected_category:
            raise ConfigurationError(
                "REPORT_STATUS_MAPPINGS must preserve the approved mappings for "
                "To Do, In Progress, Blocked, and Done."
            )
    return tuple(mappings.values())


def _validate_jira_scope(project_key: str | None, jql: str | None) -> None:
    if not project_key or not jql:
        return
    key = re.escape(project_key)
    project_equals = re.search(
        rf"\bproject\s*=\s*['\"]?{key}['\"]?(?![A-Z0-9_-])",
        jql,
        flags=re.IGNORECASE,
    )
    project_in = re.search(
        rf"\bproject\s+in\s*\([^)]*(?<![A-Z0-9_-])['\"]?{key}['\"]?(?![A-Z0-9_-])",
        jql,
        flags=re.IGNORECASE,
    )
    if not (project_equals or project_in):
        raise ConfigurationError(
            "JIRA_JQL must explicitly scope results to JIRA_PROJECT_KEY."
        )


def _validate_database_url(raw: str) -> str:
    try:
        parsed = urlparse(raw)
        hostname = parsed.hostname
    except ValueError as error:
        raise ConfigurationError(
            "DATABASE_URL must be a valid PostgreSQL URL."
        ) from error
    if (
        parsed.scheme not in {"postgres", "postgresql"}
        or not hostname
        or not parsed.path.strip("/")
    ):
        raise ConfigurationError(
            "DATABASE_URL must be a PostgreSQL URL with a host and database name."
        )
    return raw


def _validate_jira_base_url(raw: str) -> str:
    try:
        parsed = urlparse(raw)
        hostname = parsed.hostname
    except ValueError as error:
        raise ConfigurationError("JIRA_BASE_URL must be a valid HTTPS URL.") from error
    if (
        parsed.scheme != "https"
        or not hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ConfigurationError("JIRA_BASE_URL must be an HTTPS URL.")
    return raw


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
    jira_project_key: str | None
    timezone_name: str
    jira_base_url: str | None
    jira_email: str | None
    jira_api_token: str | None
    jira_jql: str | None
    jira_timeout_seconds: int
    jira_page_size: int
    jira_max_retries: int
    jira_story_points_field: str | None
    jira_required_fields: tuple[str, ...]
    jira_optional_fields: tuple[str, ...]
    done_statuses: tuple[str, ...]
    in_progress_statuses: tuple[str, ...]
    blocked_statuses: tuple[str, ...]
    status_mappings: tuple[tuple[str, str], ...]
    status_precedence: tuple[str, ...]
    due_soon_days: int
    health_green_max_percent: float
    health_yellow_max_percent: float
    report_detail_limit: int
    database_url: str | None
    audit_retention_days: int
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
        require_database: bool = False,
    ) -> "Settings":
        values = os.environ if env is None else env
        project_timezone = values.get("JIRA_PROJECT_TIMEZONE", "").strip()
        legacy_timezone = values.get("REPORT_TIMEZONE", "").strip()
        if (
            project_timezone
            and legacy_timezone
            and project_timezone != legacy_timezone
        ):
            raise ConfigurationError(
                "REPORT_TIMEZONE conflicts with the authoritative JIRA_PROJECT_TIMEZONE."
            )
        timezone_name = project_timezone or (
            legacy_timezone if not require_jira else ""
        ) or "UTC"
        try:
            ZoneInfo(timezone_name)
        except (ZoneInfoNotFoundError, ValueError) as error:
            raise ConfigurationError(
                "JIRA_PROJECT_TIMEZONE (or offline REPORT_TIMEZONE) must be a valid IANA timezone."
            ) from error

        jira_base_url = values.get("JIRA_BASE_URL", "").strip().rstrip("/") or None
        jira_email = _email_address(values, "JIRA_EMAIL")
        jira_api_token = values.get("JIRA_API_TOKEN", "").strip() or None
        jira_jql = values.get("JIRA_JQL", "").strip() or None
        jira_project_key = values.get("JIRA_PROJECT_KEY", "").strip() or None
        if jira_project_key and not re.fullmatch(
            r"[A-Z][A-Z0-9_]{0,49}", jira_project_key
        ):
            raise ConfigurationError(
                "JIRA_PROJECT_KEY must be a valid uppercase Jira project key."
            )
        if jira_base_url:
            jira_base_url = _validate_jira_base_url(jira_base_url)
        _validate_jira_scope(jira_project_key, jira_jql)
        if require_jira:
            missing = [
                name
                for name, value in (
                    ("JIRA_BASE_URL", jira_base_url),
                    ("JIRA_EMAIL", jira_email),
                    ("JIRA_API_TOKEN", jira_api_token),
                    ("JIRA_PROJECT_KEY", jira_project_key),
                    ("JIRA_JQL", jira_jql),
                    ("JIRA_PROJECT_TIMEZONE", project_timezone),
                )
                if not value
            ]
            if missing:
                raise ConfigurationError(
                    "Missing Jira configuration: " + ", ".join(missing) + "."
                )

        smtp_host = values.get("SMTP_HOST", "").strip() or None
        smtp_sender = _email_address(values, "SMTP_SENDER")
        raw_recipients = _csv(values, "SMTP_RECIPIENTS")
        smtp_recipients = tuple(
            _validate_email_address(item, "SMTP_RECIPIENTS")
            for item in raw_recipients
        )
        if len({address.casefold() for address in smtp_recipients}) != len(
            smtp_recipients
        ):
            raise ConfigurationError("SMTP_RECIPIENTS must not contain duplicates.")
        smtp_username = values.get("SMTP_USERNAME", "").strip() or None
        smtp_password = values.get("SMTP_PASSWORD", "").strip() or None
        smtp_use_ssl = _boolean(values, "SMTP_USE_SSL")
        smtp_starttls = _boolean(values, "SMTP_STARTTLS", True)
        if smtp_use_ssl and smtp_starttls:
            raise ConfigurationError(
                "Use either SMTP_USE_SSL or SMTP_STARTTLS, not both."
            )
        if smtp_host and not (smtp_use_ssl or smtp_starttls):
            raise ConfigurationError(
                "SMTP requires TLS: enable SMTP_USE_SSL or SMTP_STARTTLS."
            )
        if bool(smtp_username) != bool(smtp_password):
            raise ConfigurationError(
                "Set both SMTP_USERNAME and SMTP_PASSWORD, or neither."
            )
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
        database_url = values.get("DATABASE_URL", "").strip() or None
        if database_url:
            database_url = _validate_database_url(database_url)
        if require_database and not database_url:
            raise ConfigurationError(
                "Missing database configuration: DATABASE_URL."
            )
        audit_retention_days = _integer(
            values, "AUDIT_RETENTION_DAYS", 90
        )
        if audit_retention_days != 90:
            raise ConfigurationError(
                "AUDIT_RETENTION_DAYS must be 90 per the approved audit policy."
            )
        due_soon_days = _integer(values, "REPORT_DUE_SOON_DAYS", 7, maximum=7)
        if due_soon_days != 7:
            raise ConfigurationError(
                "REPORT_DUE_SOON_DAYS must be 7 per the approved risk policy."
            )

        story_points_field = (
            values.get("JIRA_STORY_POINTS_FIELD", "customfield_10016").strip()
            or None
        )
        project_name = values.get("REPORT_PROJECT_NAME", "Jira Project").strip()
        if not project_name:
            raise ConfigurationError("REPORT_PROJECT_NAME must not be empty.")

        try:
            green_max = float(
                values.get("REPORT_HEALTH_GREEN_MAX_PERCENT", "10")
            )
            yellow_max = float(
                values.get("REPORT_HEALTH_YELLOW_MAX_PERCENT", "20")
            )
        except ValueError as error:
            raise ConfigurationError(
                "Health percentage thresholds must be numbers."
            ) from error
        if not 0 <= green_max < yellow_max <= 100:
            raise ConfigurationError(
                "Health thresholds must satisfy 0 <= green < yellow <= 100."
            )

        status_mappings = _status_mappings(values)
        legacy_status_settings = {
            "REPORT_DONE_STATUSES",
            "REPORT_IN_PROGRESS_STATUSES",
            "REPORT_BLOCKED_STATUSES",
        } & values.keys()
        if legacy_status_settings:
            raise ConfigurationError(
                "Use REPORT_STATUS_MAPPINGS instead of legacy status settings: "
                + ", ".join(sorted(legacy_status_settings))
                + "."
            )
        legacy_metric_settings = {
            "REPORT_BLOCKED_LABELS",
            "REPORT_AT_RISK_LABELS",
            "REPORT_AT_RISK_PRIORITIES",
            "REPORT_RED_BLOCKED_THRESHOLD",
            "REPORT_RED_OVERDUE_THRESHOLD",
            "REPORT_YELLOW_RISK_THRESHOLD",
        } & values.keys()
        if legacy_metric_settings:
            raise ConfigurationError(
                "Remove legacy metric settings; use the approved status and "
                "percentage policies: "
                + ", ".join(sorted(legacy_metric_settings))
                + "."
            )

        return cls(
            project_name=project_name,
            jira_project_key=jira_project_key,
            timezone_name=timezone_name,
            jira_base_url=jira_base_url,
            jira_email=jira_email,
            jira_api_token=jira_api_token,
            jira_jql=jira_jql,
            jira_timeout_seconds=_integer(
                values, "JIRA_TIMEOUT_SECONDS", 20, maximum=300
            ),
            jira_page_size=_integer(
                values, "JIRA_PAGE_SIZE", 100, maximum=100
            ),
            jira_max_retries=_integer(
                values, "JIRA_MAX_RETRIES", 3, maximum=10
            ),
            jira_story_points_field=story_points_field,
            jira_required_fields=("key", "summary", "status", "assignee", "duedate"),
            jira_optional_fields=("epic", "story_points", "fixVersions"),
            done_statuses=tuple(
                status.casefold()
                for status, category in status_mappings
                if category == "Completed"
            ),
            in_progress_statuses=tuple(
                status.casefold()
                for status, category in status_mappings
                if category == "Active"
            ),
            blocked_statuses=tuple(
                status.casefold()
                for status, category in status_mappings
                if category == "Blocked"
            ),
            status_mappings=status_mappings,
            status_precedence=("Blocked", "At Risk", "Active", "Planned", "Completed"),
            due_soon_days=due_soon_days,
            health_green_max_percent=green_max,
            health_yellow_max_percent=yellow_max,
            report_detail_limit=_integer(
                values, "REPORT_DETAIL_LIMIT", 100, maximum=100
            ),
            database_url=database_url,
            audit_retention_days=audit_retention_days,
            smtp_host=smtp_host,
            smtp_port=_integer(values, "SMTP_PORT", 587, maximum=65535),
            smtp_max_retries=_integer(
                values, "SMTP_MAX_RETRIES", 3, maximum=10
            ),
            smtp_sender=smtp_sender,
            smtp_recipients=smtp_recipients,
            smtp_username=smtp_username,
            smtp_password=smtp_password,
            smtp_use_ssl=smtp_use_ssl,
            smtp_starttls=smtp_starttls,
        )
