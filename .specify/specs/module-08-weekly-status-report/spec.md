# Module 08: Weekly Stakeholder Status Reporting

**Source specification:** [`project_spec.md`](../../../project_spec.md)

## User need

Leadership needs a concise, consistent weekly view of project health, completed work, active risks and blockers, milestones, and next actions. The report should be generated from Jira and delivered by email on a configurable weekly schedule.

## Functional requirements

- Read Jira scope and credentials, report timezone, status/risk rules, and mail settings from environment configuration.
- Retrieve configured Jira issues with required fields and pagination; normalize optional and missing values without dropping otherwise valid issues.
- Calculate open, completed-in-period, in-progress, blocked, at-risk, overdue, and due-soon metrics, plus milestone progress where Jira supplies fix-version data.
- Classify health as Green, Yellow, or Red using configurable thresholds and include the reasons for the classification.
- Render a concise email with health, period, highlights, risks/blockers, milestones, upcoming actions, recommendations, and a project/week subject.
- Support fixture input and a non-sending dry run. Send mail only after explicit operator opt-in.
- Return a failing status and clear error on invalid required configuration or failed Jira/email operations.

## Safety and operational constraints

- No credentials in source, committed examples, report output, or logs.
- No Jira writes; only issue search requests are permitted.
- Retries are bounded and limited to transient Jira failures.
- Scheduler deployment is external to the application; document a Windows Task Scheduler example and the configured timezone.

## Acceptance checks

- A fixture-backed command creates a readable report without network access.
- Unit tests verify Jira normalization, metrics and thresholds, milestones, report sections, configuration validation, pagination/retries, and delivery failure handling.
- Live Jira and SMTP operation are available only when the operator supplies configuration; email requires an explicit send option.
