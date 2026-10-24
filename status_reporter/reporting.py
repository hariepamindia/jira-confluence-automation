from collections import defaultdict
from datetime import date, datetime, timedelta

from .config import Settings
from .models import IssueRecord, Milestone, Report


def _is_done(issue: IssueRecord, settings: Settings) -> bool:
    return issue.status.casefold() in settings.done_statuses


def _is_blocked(issue: IssueRecord, settings: Settings) -> bool:
    labels = {label.casefold() for label in issue.labels}
    return (
        issue.status.casefold() in settings.blocked_statuses
        or bool(labels.intersection(settings.blocked_labels))
    )


def _is_at_risk(issue: IssueRecord, settings: Settings, today: date) -> bool:
    labels = {label.casefold() for label in issue.labels}
    return (
        bool(labels.intersection(settings.at_risk_labels))
        or (issue.priority or "").casefold() in settings.at_risk_priorities
        or (issue.due_date is not None and issue.due_date < today and not _is_done(issue, settings))
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

    completed = tuple(
        issue
        for issue in issues
        if _is_done(issue, settings)
        and issue.resolution_date is not None
        and period_start_datetime <= issue.resolution_date < period_end_exclusive
    )
    active = [issue for issue in issues if not _is_done(issue, settings)]
    in_progress = tuple(
        issue
        for issue in active
        if issue.status.casefold() in settings.in_progress_statuses
    )
    blocked = tuple(issue for issue in active if _is_blocked(issue, settings))
    at_risk = tuple(
        issue for issue in active if _is_at_risk(issue, settings, report_date)
    )
    overdue = tuple(
        issue
        for issue in active
        if issue.due_date is not None and issue.due_date < report_date
    )
    due_soon = tuple(
        issue
        for issue in active
        if issue.due_date is not None
        and report_date <= issue.due_date <= report_date + timedelta(days=settings.due_soon_days)
    )
    milestones = _milestones(issues, settings, report_date)
    updated = sum(
        1
        for issue in issues
        if issue.updated_date is not None
        and period_start_datetime <= issue.updated_date < period_end_exclusive
    )

    health_reasons = []
    if len(blocked) >= settings.red_blocked_threshold:
        health_reasons.append(
            f"{len(blocked)} blocked issue(s) meet the red threshold "
            f"({settings.red_blocked_threshold})."
        )
    if len(overdue) >= settings.red_overdue_threshold:
        health_reasons.append(
            f"{len(overdue)} overdue issue(s) meet the red threshold "
            f"({settings.red_overdue_threshold})."
        )
    if health_reasons:
        health = "Red"
    elif not issues:
        health = "Yellow"
        health_reasons.append("No Jira issues matched the configured scope.")
    else:
        warning_reasons = []
        if len(at_risk) >= settings.yellow_risk_threshold:
            warning_reasons.append(
                f"{len(at_risk)} issue(s) meet the at-risk rule "
                f"(threshold {settings.yellow_risk_threshold})."
            )
        delayed = sum(milestone.status == "Delayed" for milestone in milestones)
        near_term_risk = sum(milestone.status == "At risk" for milestone in milestones)
        if delayed:
            warning_reasons.append(f"{delayed} milestone(s) are delayed.")
        if near_term_risk:
            warning_reasons.append(f"{near_term_risk} milestone(s) are at risk.")
        health = "Yellow" if warning_reasons else "Green"
        health_reasons.extend(warning_reasons or ["No configured health thresholds were exceeded."])

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
        recommendations.append("Continue tracking active work and confirm upcoming owners.")

    return Report(
        project_name=settings.project_name,
        period_start=period_start,
        period_end=period_end,
        health=health,
        health_reasons=tuple(health_reasons),
        total_issues=len(issues),
        open_issues=len(active),
        completed_issues=completed,
        in_progress_issues=in_progress,
        blocked_issues=blocked,
        at_risk_issues=at_risk,
        overdue_issues=overdue,
        due_soon_issues=due_soon,
        milestones=milestones,
        updated_in_period=updated,
        recommendations=tuple(recommendations),
    )
