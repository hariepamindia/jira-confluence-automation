import unicodedata

from .models import IssueRecord, Report


def _safe_text(value: str) -> str:
    return "".join(
        " " if unicodedata.category(character) in {"Cc", "Zl", "Zp"} else character
        for character in value
    ).strip()


def _issue_line(issue: IssueRecord) -> str:
    details = [_safe_text(issue.key), _safe_text(issue.summary)]
    if issue.assignee:
        details.append(f"Owner: {_safe_text(issue.assignee)}")
    if issue.due_date:
        details.append(f"Due: {issue.due_date.isoformat()}")
    return "- " + " | ".join(details)


def render_subject(report: Report) -> str:
    return (
        f"[Weekly Status] {_safe_text(report.project_name)} - "
        f"Week of {report.period_start.isoformat()}"
    )


def render_report(report: Report, due_soon_days: int) -> str:
    lines = [
        f"Weekly Status Report - {_safe_text(report.project_name)}",
        f"Reporting period: {report.period_start.isoformat()} to {report.period_end.isoformat()}",
        "",
        f"Project Health: {report.health}",
        *[f"- {_safe_text(reason)}" for reason in report.health_reasons],
        "",
        "Summary",
        f"- Total issues in scope: {report.total_issues}",
        f"- Open: {report.open_issues}",
        f"- Planned: {len(report.planned_issues)}",
        f"- In progress: {len(report.in_progress_issues)}",
        f"- Completed this period: {len(report.completed_issues)}",
        f"- Blocked: {len(report.blocked_issues)}",
        f"- At risk: {len(report.at_risk_issues)}",
        f"- Overdue: {len(report.overdue_issues)}",
        f"- Due within {due_soon_days} days: {len(report.due_soon_issues)}",
        f"- Updated this period: {report.updated_in_period}",
    ]
    listed: set[str] = set()

    def append_details(heading: str, issues: tuple[IssueRecord, ...]) -> None:
        lines.extend(["", heading])
        prioritized_candidates = [
            issue
            for issue in issues
            if any(selected.key == issue.key for selected in report.detail_issues)
        ]
        matching = [
            issue
            for issue in report.detail_issues
            if issue.key not in listed
            and any(candidate.key == issue.key for candidate in issues)
        ]
        for issue in matching:
            lines.append(_issue_line(issue))
            listed.add(issue.key)
        if not matching:
            if prioritized_candidates:
                lines.append("- Details are shown in an earlier section.")
            else:
                lines.append("- None within the configured detail limit.")

    append_details("Highlights / Completed Work", report.completed_issues)
    append_details(
        "Current Risks and Blockers",
        (*report.blocked_issues, *report.at_risk_issues, *report.overdue_issues),
    )
    lines.extend(["", "Milestone Status"])
    if report.milestones:
        for milestone in report.milestones:
            target = (
                milestone.release_date.isoformat()
                if milestone.release_date
                else "target date not set"
            )
            lines.append(
                f"- {_safe_text(milestone.name)}: {milestone.status} "
                f"({milestone.completed_issues}/{milestone.total_issues} issues; {target})"
            )
    else:
        lines.append("- No milestone data was provided by Jira fix versions.")

    append_details("Upcoming Actions", report.due_soon_issues)
    remaining = tuple(
        issue for issue in report.detail_issues if issue.key not in listed
    )
    if remaining:
        append_details("Other Prioritized Issues", remaining)
    if report.omitted_detail_count:
        lines.extend(
            [
                "",
                f"- {report.omitted_detail_count} additional issue detail(s) omitted "
                "by the configured reporting limit.",
            ]
        )

    lines.extend(["", "Recommended Next Steps"])
    lines.extend(f"- {_safe_text(item)}" for item in report.recommendations)
    lines.append("")
    return "\n".join(lines)
