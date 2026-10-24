import base64
import json
import logging
import time
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from .config import Settings
from .models import IssueRecord, VersionRecord

LOGGER = logging.getLogger(__name__)
JIRA_FIELDS = (
    "summary",
    "status",
    "priority",
    "assignee",
    "project",
    "duedate",
    "created",
    "updated",
    "resolutiondate",
    "labels",
    "components",
    "fixVersions",
)


def _parse_datetime(value: Any, timezone: ZoneInfo) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Expected a Jira date/time string.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"Invalid Jira date/time value: {value!r}.") from error
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone)
    return parsed.astimezone(timezone)


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Expected a Jira date string.")
    try:
        return date.fromisoformat(value[:10])
    except ValueError as error:
        raise ValueError(f"Invalid Jira date value: {value!r}.") from error


def normalize_issue(
    raw: Any, timezone: ZoneInfo, story_points_field: str | None
) -> IssueRecord:
    if not isinstance(raw, dict):
        raise ValueError("Jira issue must be an object.")
    key = raw.get("key")
    fields = raw.get("fields")
    if not isinstance(key, str) or not key.strip():
        raise ValueError("Jira issue is missing its key.")
    if not isinstance(fields, dict):
        raise ValueError(f"Jira issue {key} is missing its fields object.")

    summary = fields.get("summary")
    status_data = fields.get("status")
    project_data = fields.get("project")
    if not isinstance(summary, str):
        raise ValueError(f"Jira issue {key} is missing its summary.")
    if not isinstance(status_data, dict) or not isinstance(
        status_data.get("name"), str
    ):
        raise ValueError(f"Jira issue {key} is missing its status.")
    if not isinstance(project_data, dict) or not isinstance(
        project_data.get("key"), str
    ):
        raise ValueError(f"Jira issue {key} is missing its project key.")
    for field_name in ("created", "updated"):
        if not isinstance(fields.get(field_name), str) or not fields[field_name]:
            raise ValueError(f"Jira issue {key} is missing its {field_name} date.")

    assignee_data = fields.get("assignee")
    if assignee_data is not None and not isinstance(assignee_data, dict):
        raise ValueError(f"Jira issue {key} has an invalid assignee.")
    priority_data = fields.get("priority")
    if priority_data is not None and not isinstance(priority_data, dict):
        raise ValueError(f"Jira issue {key} has an invalid priority.")

    labels = fields.get("labels", [])
    components = fields.get("components", [])
    versions = fields.get("fixVersions", [])
    labels = [] if labels is None else labels
    components = [] if components is None else components
    versions = [] if versions is None else versions
    if not isinstance(labels, list) or not all(
        isinstance(label, str) for label in labels
    ):
        raise ValueError(f"Jira issue {key} has invalid labels.")
    if not isinstance(components, list) or not all(
        isinstance(item, dict) and isinstance(item.get("name"), str)
        for item in components
    ):
        raise ValueError(f"Jira issue {key} has invalid components.")
    if not isinstance(versions, list) or not all(
        isinstance(item, dict) and isinstance(item.get("name"), str)
        for item in versions
    ):
        raise ValueError(f"Jira issue {key} has invalid fix versions.")

    try:
        normalized_versions = tuple(
            VersionRecord(
                name=item["name"],
                release_date=_parse_date(item.get("releaseDate")),
                released=item.get("released") is True,
            )
            for item in versions
        )
        due_date = _parse_date(fields.get("duedate"))
        created_date = _parse_datetime(fields.get("created"), timezone)
        updated_date = _parse_datetime(fields.get("updated"), timezone)
        resolution_date = _parse_datetime(fields.get("resolutiondate"), timezone)
    except ValueError as error:
        raise ValueError(f"Jira issue {key} has invalid date data: {error}") from error
    story_points = (
        fields.get(story_points_field) if story_points_field is not None else None
    )
    if story_points is not None:
        if isinstance(story_points, bool) or not isinstance(story_points, (int, float)):
            raise ValueError(f"Jira issue {key} has invalid story points.")
        story_points = float(story_points)

    return IssueRecord(
        key=key,
        summary=summary,
        status=status_data["name"],
        priority=(priority_data or {}).get("name"),
        assignee=(assignee_data or {}).get("displayName"),
        project=project_data["key"],
        due_date=due_date,
        created_date=created_date,
        updated_date=updated_date,
        resolution_date=resolution_date,
        labels=tuple(labels),
        components=tuple(item["name"] for item in components),
        story_points=story_points,
        versions=normalized_versions,
    )


def _retry_delay(error: HTTPError, attempt: int) -> float:
    retry_after = error.headers.get("Retry-After")
    if retry_after:
        try:
            return min(max(float(retry_after), 0.0), 30.0)
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(retry_after)
                return min(
                    max(
                        (retry_at - datetime.now(retry_at.tzinfo)).total_seconds(),
                        0.0,
                    ),
                    30.0,
                )
            except (TypeError, ValueError, OverflowError):
                pass
    return min(2 ** (attempt - 1), 30)


def fetch_issues(settings: Settings) -> list[IssueRecord]:
    if not (
        settings.jira_base_url
        and settings.jira_email
        and settings.jira_api_token
        and settings.jira_jql
    ):
        raise ValueError("Jira settings are required to fetch live issues.")

    auth = base64.b64encode(
        f"{settings.jira_email}:{settings.jira_api_token}".encode("utf-8")
    ).decode("ascii")
    fields = list(JIRA_FIELDS)
    if settings.jira_story_points_field:
        fields.append(settings.jira_story_points_field)
    issues: list[IssueRecord] = []
    seen_keys: set[str] = set()
    start_at = 0
    total: int | None = None
    endpoint = f"{settings.jira_base_url}/rest/api/3/search"

    while total is None or start_at < total:
        query = urlencode(
            {
                "jql": settings.jira_jql,
                "startAt": start_at,
                "maxResults": settings.jira_page_size,
                "fields": ",".join(fields),
            }
        )
        request = Request(
            f"{endpoint}?{query}",
            headers={
                "Accept": "application/json",
                "Authorization": f"Basic {auth}",
            },
        )
        payload = None
        for attempt in range(1, settings.jira_max_retries + 1):
            try:
                with urlopen(request, timeout=settings.jira_timeout_seconds) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                break
            except HTTPError as error:
                error.close()
                retryable = error.code == 429 or 500 <= error.code < 600
                if not retryable or attempt >= settings.jira_max_retries:
                    raise RuntimeError(
                        f"Jira request failed with HTTP {error.code}."
                    ) from error
                delay = _retry_delay(error, attempt)
                LOGGER.warning(
                    "Jira returned HTTP %s; retrying attempt %s/%s after %.1f seconds.",
                    error.code,
                    attempt + 1,
                    settings.jira_max_retries,
                    delay,
                )
                time.sleep(delay)
            except (URLError, TimeoutError) as error:
                if attempt >= settings.jira_max_retries:
                    raise RuntimeError(
                        "Jira request failed after transient network errors."
                    ) from error
                delay = min(2 ** (attempt - 1), 30)
                LOGGER.warning(
                    "Jira network request failed; retrying attempt %s/%s after %.1f seconds.",
                    attempt + 1,
                    settings.jira_max_retries,
                    delay,
                )
                time.sleep(delay)

        if not isinstance(payload, dict) or not isinstance(payload.get("issues"), list):
            raise RuntimeError("Jira returned an invalid search response.")
        page_issues = payload["issues"]
        total_value = payload.get("total")
        if total_value is not None and (
            isinstance(total_value, bool) or not isinstance(total_value, int)
        ):
            raise RuntimeError("Jira returned an invalid result total.")
        total = total_value if total_value is not None else start_at + len(page_issues)
        if not page_issues and start_at < total:
            raise RuntimeError("Jira returned an empty page before all results.")
        for raw_issue in page_issues:
            issue = normalize_issue(
                raw_issue, settings.timezone, settings.jira_story_points_field
            )
            if issue.key not in seen_keys:
                issues.append(issue)
                seen_keys.add(issue.key)
        start_at += len(page_issues)
        if not page_issues:
            break
    return issues
