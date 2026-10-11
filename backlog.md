# Weekly Stakeholder Status Reporting — Implementation Backlog

## Prioritization and sequencing

This backlog follows the selected MVP-first approach: establish a secure, runnable project; build Jira data extraction and report generation; then connect live email delivery and scheduling. Testing and documentation cover the complete implementation. Priorities indicate relative importance: **P0** is required for the first usable weekly report, **P1** completes reliable automation, and **P2** improves operational readiness or extensibility.

## Setup

- [ ] **P0 — Establish the Python project environment.** Select and document the supported Python version, create a project-local virtual environment, and add the minimal runtime and development dependencies to a dependency manifest.
- [ ] **P0 — Define the application layout.** Create separate modules or packages for configuration, Jira access, report models and processing, rendering, email delivery, scheduling, and the command-line entry point.
- [ ] **P0 — Define configuration and secret handling.** Add typed configuration for Jira URL and authentication, project keys/JQL, reporting period and timezone, recipients, email transport, schedule, and status thresholds; load credentials only from environment variables or a secret store.
- [ ] **P0 — Add a safe configuration example.** Provide a committed example configuration with placeholders only, validate required settings at startup, and ensure secret files are ignored by version control.
- [ ] **P0 — Specify Jira query scope.** Record the initial project or saved-filter/JQL inputs, reporting-period boundaries, relevant statuses, and fields to retrieve; make project/filter selection configurable rather than hard-coded.
- [ ] **P1 — Specify business mappings and thresholds.** Define configurable Jira status-to-category mappings, the team's blocked and at-risk rules, the meaning of “due soon,” milestone source fields, and Green/Yellow/Red health thresholds.

## Core Features

- [ ] **P0 — Define typed issue and report models.** Represent the required Jira issue fields and derived flags, allowing absent assignees, due dates, estimates, labels, and components without losing valid issues.
- [ ] **P0 — Implement Jira query and extraction logic.** Build the configured JQL for the reporting window and relevant current work; request the specified fields and retrieve all matching issues across Jira pagination.
- [ ] **P0 — Normalize Jira responses.** Convert API values into the report models, normalize dates consistently using the configured timezone, and surface malformed or incomplete required data with issue context.
- [ ] **P0 — Calculate weekly and current-work aggregates.** Produce counts for open, completed in-period, and in-progress issues; identify changes during the reporting period and avoid counting an issue more than once in a metric.
- [ ] **P0 — Identify blockers, risks, and due dates.** Apply the configured status/risk rules and calculate blocked, at-risk, due-soon, and overdue items; include the issue, impact, owner, and due date where Jira provides them.
- [ ] **P0 — Summarize milestones.** Read the configured Jira milestone source and produce milestone target dates, status, and progress; report missing milestone data explicitly rather than inventing a status.
- [ ] **P0 — Classify overall project health.** Implement configurable Green, Yellow, and Red rules using milestone progress, risks, blockers, and schedule variance, and retain a concise explanation of the classification.
- [ ] **P0 — Render the stakeholder report.** Use the existing report template as a starting point and produce a concise leadership-ready report with health summary, highlights, risks and blockers, milestone status, upcoming actions, recommended next steps, and decisions/support needed.
- [ ] **P0 — Add report subject and period labels.** Generate the required subject pattern with project name and reporting-week reference, and show the reporting period in the report body.
- [ ] **P1 — Support multiple configured projects or teams.** Generate clearly separated project summaries from configured project/filter entries without changing reporting logic.

## Integration

- [ ] **P0 — Connect to Jira REST API.** Implement the configured authentication method, request timeouts, pagination, and field selection; never log authorization headers, tokens, or other credentials.
- [ ] **P0 — Deliver email through the selected mail transport.** Configure sender, recipients, subject, and report body from settings; fail clearly when delivery is rejected or configuration is invalid.
- [ ] **P0 — Add a safe test/dry-run mode.** Allow report generation and email preview without sending to the stakeholder list; require explicit configuration or invocation to send a real report.
- [ ] **P1 — Add bounded retries for transient failures.** Retry transient network errors and Jira rate-limit responses using bounded backoff; do not retry permanent authentication, validation, or recipient errors as though delivery succeeded.
- [ ] **P1 — Add weekly automation entry point.** Provide a command that runs data retrieval, aggregation, rendering, and delivery in order, with a nonzero failure result if a required stage fails.
- [ ] **P1 — Configure the deployment scheduler.** Select and document one deployment target (for example, Windows Task Scheduler, cron, GitHub Actions, or a cloud scheduler) and schedule the report weekly on Monday morning in the configured timezone.
- [ ] **P1 — Add operational logging.** Log run start/end, selected reporting period, project, issue counts, and stage failures without exposing secrets or unnecessary personal data.

## Testing

- [ ] **P0 — Test Jira response normalization.** Cover complete issues, optional/missing fields, date parsing, unexpected statuses, and malformed responses.
- [ ] **P0 — Test query and pagination behavior.** Verify configured project/filter and period boundaries, requested fields, multi-page results, and no duplicate issue aggregation.
- [ ] **P0 — Test report metrics and classification.** Cover completed-in-period, in-progress, blocked, at-risk, overdue, due-soon, milestone status, and Green/Yellow/Red outcomes at configured thresholds.
- [ ] **P0 — Test report rendering.** Assert that the output contains every required section, the project/week subject, counts, issue context, and a clear explanation when milestone or Jira data is unavailable.
- [ ] **P1 — Test configuration and secret safety.** Verify missing/invalid settings fail with actionable errors and confirm credentials do not appear in logs, rendered reports, or sample configuration.
- [ ] **P1 — Test Jira and email failures.** Simulate authentication failure, rate limiting, transient network errors, exhausted retries, and mail rejection; verify failures are visible and are not reported as successful sends.
- [ ] **P1 — Run an end-to-end dry-run with fixtures.** Exercise the full command from fixture Jira data through rendered email preview and check the resulting weekly report against the acceptance criteria.
- [ ] **P1 — Verify scheduled execution.** Run the configured scheduler or its equivalent command in a test environment and verify it uses the intended timezone and reporting period.

## Documentation

- [ ] **P0 — Document local setup and execution.** Explain supported Python version, environment creation, dependency installation, configuration, tests, dry-run, and manual report generation.
- [ ] **P0 — Document Jira setup.** List required Jira permissions, supported authentication configuration, required fields, project/JQL setup, pagination behavior, and how to configure multiple projects.
- [ ] **P0 — Document report interpretation.** Describe metric definitions, status mappings, risk and due-soon rules, milestone source, configurable health thresholds, and assumptions about incomplete Jira data.
- [ ] **P1 — Document email and schedule deployment.** Explain mail transport settings, safe recipient configuration, deployment target, weekly schedule and timezone, and how to disable or rerun delivery.
- [ ] **P1 — Document operations and troubleshooting.** Describe logs, retry behavior, common Jira/email failures, credential rotation, and recovery steps for a failed weekly run.
- [ ] **P1 — Provide a sample output.** Include a clearly fictional report demonstrating all required sections without real project data, personal information, or credentials.
