import logging
from collections import defaultdict
from datetime import date, datetime, timedelta

from .config import Settings
from .models import IssueRecord, Milestone, Report

LOGGER = logging.getLogger(__name__)
_PRIORITY_ORDER = {"highest": 0, "high": 1, "medium": 2, "low": 3}


def _status_mapping(settings: Settings) -> dict[str, str]:
    return {status.casefold(): category for status, category in settings.status_mappings}


def _mapped_category(issue: IssueRecord, settings: Settings) -> str:
    return _status_mapping(settings).get(issue.status.casefold(), "Active")


def _is_done(issue: IssueRecord, settings: Settings) -> bool:
    return _mapped_category(issue, settings) == "Completed"


def _is_blocked(issue: IssueRecord, settings: Settings) -> bool:
    return (
        _mapped_category(issue, settings) == "Blocked"
        or "blocked" in {label.casefold() for label in issue.labels}
    )


def _is_at_risk(issue: IssueRecord, settings: Settings, today: date) -> bool:
    return (
        not _is_done(issue, settings)
        and issue.due_date is not None
        and today <= issue.due_date <= today + timedelta(days=7)
    )


def _category(issue: IssueRecord, settings: Settings, today: date) -> str:
    if _is_blocked(issue, settings):
        return "Blocked"
    if _is_at_risk(issue, settings, today):
        return "At Risk"
    mapping = _status_mapping(settings)
    category = mapping.get(issue.status.casefold())
    return category or "Active"


def _eligible_issues(issues: list[IssueRecord]) -> list[IssueRecord]:
    eligible: list[IssueRecord] = []
    seen_keys: set[str] = set()
    for issue in issues:
        key = issue.key.casefold()
        if key in seen_keys:
            continue
        seen_keys.add(key)
        if issue.status.casefold() == "cancelled":
            continue
        if (issue.resolution or "").casefold() == "duplicate":
            continue
        eligible.append(issue)
    return eligible


def _detail_sort_key(issue: IssueRecord) -> tuple[int, date, float, str]:
    return (
        _PRIORITY_ORDER.get((issue.priority or "").casefold(), 4),
        issue.due_date or date.max,
        issue.created_date.timestamp()
        if issue.created_date is not None
        else float("inf"),
        issue.key.casefold(),
    )


def _milestones(
    issues: list[IssueRecord], settings: Settings, today: date
) -> tuple[Milestone, ...]:
    grouped: dict[str, dict[str, object]] = defaultdict(
        lambda: {"total": 0, "completed": 0, "release_date": None, "released": False}
    )
    for issue in issues:
        for version in issue.versions:
            data = grouped[version.name]
            data["total"] = int(data["total"]) + 1
            if _is_done(issue, settings):
                data["completed"] = int(data["completed"]) + 1
            data["released"] = bool(data["released"]) or version.released
            release_date = data["release_date"]
            if version.release_date and (
                release_date is None or version.release_date < release_date
            ):
                data["release_date"] = version.release_date

    results = []
    for name, data in sorted(grouped.items()):
        total = int(data["total"])
        completed = int(data["completed"])
        release_date = data["release_date"]
        if completed == total or data["released"]:
            status = "Complete"
        elif isinstance(release_date, date) and release_date < today:
            status = "Delayed"
        elif isinstance(release_date, date) and release_date <= today + timedelta(
            days=settings.due_soon_days
        ):
            status = "At risk"
        else:
            status = "On track"
        results.append(
            Milestone(
                name=name,
                release_date=release_date if isinstance(release_date, date) else None,
                status=status,
                completed_issues=completed,
                total_issues=total,
            )
        )
    return tuple(results)


def build_report(
    issues: list[IssueRecord],
    settings: Settings,
    period_start: date,
    period_end: date,
    *,
    today: date | None = None,
) -> Report:
    if period_end < period_start:
        raise ValueError("The reporting period end cannot precede its start.")
    report_date = today or datetime.now(settings.timezone).date()
    period_start_datetime = datetime.combine(
        period_start, datetime.min.time(), tzinfo=settings.timezone
    )
    period_end_exclusive = datetime.combine(
        period_end + timedelta(days=1), datetime.min.time(), tzinfo=settings.timezone
    )

    eligible = _eligible_issues(issues)
    status_mapping = _status_mapping(settings)
    for issue in eligible:
        if issue.status.casefold() not in status_mapping:
            LOGGER.warning(
                "Unmapped Jira status for issue %s; treating it as Active.",
                issue.key,
            )
    categorized = {
        issue.key: _category(issue, settings, report_date) for issue in eligible
    }
    active = [
        issue for issue in eligible if categorized[issue.key] != "Completed"
    ]
    planned = tuple(
        issue for issue in eligible if categorized[issue.key] == "Planned"
    )
    in_progress = tuple(
        issue for issue in eligible if _mapped_category(issue, settings) == "Active"
    )
    blocked = tuple(
        issue for issue in eligible if categorized[issue.key] == "Blocked"
    )
    completed = tuple(
        issue
        for issue in eligible
        if categorized[issue.key] == "Completed"
        and issue.resolution_date is not None
        and period_start_datetime <= issue.resolution_date < period_end_exclusive
    )
    at_risk = tuple(
        issue for issue in eligible if _is_at_risk(issue, settings, report_date)
    )
    overdue = tuple(
        issue
        for issue in active
        if issue.due_date is not None and issue.due_date < report_date
    )
    due_soon = tuple(
        issue for issue in eligible if _is_at_risk(issue, settings, report_date)
    )
    active_denominator = len(active)
    overdue_percent = (
        len(overdue) * 100.0 / active_denominator if active_denominator else 0.0
    )
    if active_denominator == 0 or (
        len(overdue) * 100
        <= settings.health_green_max_percent * active_denominator
    ):
        health = "Green"
    elif (
        len(overdue) * 100
        <= settings.health_yellow_max_percent * active_denominator
    ):
        health = "Yellow"
    else:
        health = "Red"
    health_reasons = (
        f"{len(overdue)} overdue of {active_denominator} active issue(s) "
        f"({overdue_percent:.2f}%). "
        f"Green <= {settings.health_green_max_percent:g}%; "
        f"Yellow <= {settings.health_yellow_max_percent:g}%; "
        f"otherwise Red.",
    )

    milestones = _milestones(eligible, settings, report_date)
    updated = sum(
        1
        for issue in eligible
        if issue.updated_date is not None
        and period_start_datetime <= issue.updated_date < period_end_exclusive
    )
    recommendations = []
    if blocked:
        recommendations.append("Assign owners and unblock the listed blocked work.")
    if overdue:
        recommendations.append("Reconfirm dates and recovery plans for overdue items.")
    if at_risk and not blocked:
        recommendations.append("Review at-risk items with their owners before the next report.")
    if any(item.status in {"At risk", "Delayed"} for item in milestones):
        recommendations.append("Confirm milestone scope, target dates, and recovery actions.")
    if not recommendations:
        recommendations.append(
            "No active issues require immediate action; continue routine tracking."
        )

    ordered_details = sorted(eligible, key=_detail_sort_key)
    detail_issues = tuple(ordered_details[: settings.report_detail_limit])
    omitted_detail_count = max(0, len(ordered_details) - len(detail_issues))

    return Report(
        project_name=settings.project_name,
        period_start=period_start,
        period_end=period_end,
        health=health,
        health_reasons=health_reasons,
        total_issues=len(eligible),
        open_issues=active_denominator,
        planned_issues=planned,
        completed_issues=completed,
        in_progress_issues=in_progress,
        blocked_issues=blocked,
        at_risk_issues=at_risk,
        overdue_issues=overdue,
        due_soon_issues=due_soon,
        milestones=milestones,
        updated_in_period=updated,
        recommendations=tuple(recommendations),
        active_denominator=active_denominator,
        overdue_percent=overdue_percent,
        detail_issues=detail_issues,
        omitted_detail_count=omitted_detail_count,
    )
