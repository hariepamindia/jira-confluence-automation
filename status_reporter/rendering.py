from .models import IssueRecord, Report


def _issue_line(issue: IssueRecord) -> str:
    details = [issue.key, issue.summary]
    if issue.assignee:
        details.append(f"Owner: {issue.assignee}")
    if issue.due_date:
        details.append(f"Due: {issue.due_date.isoformat()}")
    return "- " + " | ".join(details)


def render_subject(report: Report) -> str:
    return f"[Weekly Status] {report.project_name} - Week of {report.period_start.isoformat()}"


def render_report(report: Report, due_soon_days: int) -> str:
    lines = [
        f"Weekly Status Report - {report.project_name}",
        f"Reporting period: {report.period_start.isoformat()} to {report.period_end.isoformat()}",
        "",
        f"Project Health: {report.health}",
        *[f"- {reason}" for reason in report.health_reasons],
        "",
        "Summary",
        f"- Total issues in scope: {report.total_issues}",
        f"- Open: {report.open_issues}",
        f"- Completed this period: {len(report.completed_issues)}",
        f"- In progress: {len(report.in_progress_issues)}",
        f"- Blocked: {len(report.blocked_issues)}",
        f"- At risk: {len(report.at_risk_issues)}",
        f"- Overdue: {len(report.overdue_issues)}",
        f"- Due within {due_soon_days} days: {len(report.due_soon_issues)}",
        f"- Updated this period: {report.updated_in_period}",
        "",
        "Highlights / Completed Work",
    ]
    lines.extend(
        _issue_line(issue) for issue in report.completed_issues[:10]
    )
    if not report.completed_issues:
        lines.append("- No issues were resolved during this reporting period.")

    lines.extend(["", "Current Risks and Blockers"])
    risk_items = {issue.key: issue for issue in (*report.blocked_issues, *report.at_risk_issues)}
    if risk_items:
        lines.extend(_issue_line(issue) for issue in risk_items.values())
    else:
        lines.append("- No configured risk labels, priorities, or blocked items were found.")

    lines.extend(["", "Milestone Status"])
    if report.milestones:
        for milestone in report.milestones:
            target = (
                milestone.release_date.isoformat()
                if milestone.release_date
                else "target date not set"
            )
            lines.append(
                f"- {milestone.name}: {milestone.status} "
                f"({milestone.completed_issues}/{milestone.total_issues} issues; {target})"
            )
    else:
        lines.append("- No milestone data was provided by Jira fix versions.")

    lines.extend(["", "Upcoming Actions"])
    upcoming = report.due_soon_issues[:10]
    if upcoming:
        lines.extend(_issue_line(issue) for issue in upcoming)
    else:
        lines.append(f"- No open issues are due within the next {due_soon_days} days.")

    lines.extend(["", "Recommended Next Steps"])
    lines.extend(f"- {recommendation}" for recommendation in report.recommendations)
    lines.append("")
    return "\n".join(lines)
