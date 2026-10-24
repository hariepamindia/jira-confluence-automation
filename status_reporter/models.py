from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class VersionRecord:
    name: str
    release_date: date | None
    released: bool


@dataclass(frozen=True)
class IssueRecord:
    key: str
    summary: str
    status: str
    resolution: str | None
    priority: str | None
    assignee: str | None
    project: str | None
    due_date: date | None
    created_date: datetime | None
    updated_date: datetime | None
    resolution_date: datetime | None
    labels: tuple[str, ...]
    components: tuple[str, ...]
    story_points: float | None
    versions: tuple[VersionRecord, ...]


@dataclass(frozen=True)
class Milestone:
    name: str
    release_date: date | None
    status: str
    completed_issues: int
    total_issues: int


@dataclass(frozen=True)
class Report:
    project_name: str
    period_start: date
    period_end: date
    health: str
    health_reasons: tuple[str, ...]
    total_issues: int
    open_issues: int
    planned_issues: tuple[IssueRecord, ...]
    completed_issues: tuple[IssueRecord, ...]
    in_progress_issues: tuple[IssueRecord, ...]
    blocked_issues: tuple[IssueRecord, ...]
    at_risk_issues: tuple[IssueRecord, ...]
    overdue_issues: tuple[IssueRecord, ...]
    due_soon_issues: tuple[IssueRecord, ...]
    milestones: tuple[Milestone, ...]
    updated_in_period: int
    recommendations: tuple[str, ...]
    active_denominator: int
    overdue_percent: float
    detail_issues: tuple[IssueRecord, ...]
    omitted_detail_count: int
