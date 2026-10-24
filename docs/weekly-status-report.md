# Weekly Jira Status Report

This application reads a configured Jira Cloud search scope, calculates the weekly status metrics, and renders a plain-text email report. It only reads Jira issues; it does not create or update tickets. It uses Python 3.11 or newer and the standard library (Windows installs also need the declared `tzdata` package).

## Setup

1. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -e .
   ```

2. Copy `weekly-status.env.example` to `weekly-status.env`. The latter is ignored by Git. Configure `JIRA_PROJECT_KEY`, `JIRA_PROJECT_TIMEZONE`, the Jira base URL, account email, API token, project name, and a JQL scope containing that project which includes current work and recently completed work. The account needs permission to browse the project.
3. Set `JIRA_STORY_POINTS_FIELD` to the story-point custom field key used by your Jira instance, or leave it blank if story points are not used.
4. For local development, keep credentials only in the ignored environment file with restrictive filesystem permissions. In production, inject credentials through the deployment environment or secret store; do not bake them into container images or commit them. The committed example contains placeholders only.

The file parser accepts one literal `KEY=VALUE` per line, ignores blank lines and full-line comments, and strips matching surrounding quotes. It does not expand variables or execute shell content. Process environment variables override values in the file. Live Jira runs require `JIRA_PROJECT_TIMEZONE`; `REPORT_TIMEZONE` is accepted only for offline/legacy use and cannot override the Jira project timezone.

`JIRA_JQL` must explicitly scope the search to `JIRA_PROJECT_KEY`. The configuration requests Issue Key, Summary, Status, Assignee, and Due Date as required fields. Use a PostgreSQL `DATABASE_URL` for the audit/metadata integration; `AUDIT_RETENTION_DAYS` is 90. These database settings are validated here and are consumed by the persistence integration.
Issues missing or containing malformed required values, including an unassigned issue or missing due date, are excluded with a warning; other issues continue. A failed or malformed Jira page still fails the entire retrieval rather than returning a partial result.

## Run and preview

Use a fictional fixture to validate the workflow without Jira access:

```powershell
python -m status_reporter --fixture tests/fixtures/weekly_issues.json --env-file weekly-status.env
```

For a live Jira preview, omit `--fixture`. A normal run never sends email. The default reporting period is the previous Monday through Sunday, calculated in `JIRA_PROJECT_TIMEZONE`. To select an inclusive custom date range, pass both `--period-start YYYY-MM-DD` and `--period-end YYYY-MM-DD`. Use `--output preview.txt` to save a local report preview; store previews securely because issue summaries and assignees can be sensitive.

Send only after reviewing the report and configuring `SMTP_HOST`, `SMTP_PORT`, `SMTP_SENDER`, and `SMTP_RECIPIENTS`:

```powershell
python -m status_reporter --env-file weekly-status.env --send
```

SMTP authentication is optional. If used, provide both `SMTP_USERNAME` and `SMTP_PASSWORD`. SMTP must use TLS: port 587 with STARTTLS is the default; for implicit TLS (typically port 465), set `SMTP_USE_SSL=true` and `SMTP_STARTTLS=false`. Enabling both or disabling both is rejected. The sender and every recipient must be a single valid email address, and duplicate recipients are rejected. Delivery is attempted separately for each configured recipient. Partial recipient rejection continues to remaining recipients and returns “Success With Warnings”; if all recipients are rejected, the run fails. Ambiguous transport failures are not retried to avoid duplicate delivery. Retries for known transient rejections are bounded by `SMTP_MAX_RETRIES`.

## Report definitions and assumptions

The report applies the approved policy below.

- **Status mapping** is configured in `REPORT_STATUS_MAPPINGS`; the approved mappings are To Do → Planned, In Progress → Active, Blocked → Blocked, and Done → Completed. Unmapped statuses are treated as Active and logged.
- **Completed this period** uses Jira's resolution date. Reopened issues do not count as completed; if completed again, the latest resolution date applies. Exclude status `Cancelled` and resolution `Duplicate`.
- **Blocked** means status Blocked or the `blocked` label.
- **At risk** means a non-Done issue due today through the next seven calendar days. Past-due items are Overdue, not At Risk. `REPORT_DUE_SOON_DAYS` is fixed at 7. Legacy label/priority risk settings are rejected.
- **Health** uses Planned, Active, Blocked, At Risk, and unmapped active statuses as its denominator; Completed is excluded. Green is 0–10% overdue, Yellow is over 10% through 20%, and Red is over 20%. Zero active issues is Green. Percentage boundaries use `REPORT_HEALTH_GREEN_MAX_PERCENT` and `REPORT_HEALTH_YELLOW_MAX_PERCENT`.
- **Detail cap** is `REPORT_DETAIL_LIMIT` and cannot exceed 100. All metrics use the full eligible issue population. Detailed issues are ordered by priority (Highest, High, Medium, Low), earliest due date, oldest creation date, then Jira key. Each issue is listed at most once; the report states how many details were omitted.
- **Milestones** are grouped from Jira fix versions. Completion is based on the done-status mapping; a past release date is Delayed, a release date within the due-soon window is At risk, and absent fix-version data is reported explicitly.

Jira query scope is configured in `JIRA_JQL`; the application retrieves the matching set and paginates all results. Narrowing the query to only issues updated during the week can omit open work, due items, and older unresolved issues, so include the configured project scope and recently resolved issues. Milestones are limited to fix versions attached to returned issues; no milestone is invented when Jira has no corresponding data.

Jira search requests use the configured JQL and report fields over HTTPS with certificate verification and a bounded request timeout. The adapter follows Jira pagination metadata, validates each page, and deduplicates issues by key. Rate limits, server errors, timeouts, connection failures, and DNS lookup failures receive bounded retries with capped backoff; authentication and other permanent HTTP errors are not retried. Invalid JSON, inconsistent pagination, incomplete pages, or exhausted retries fail the fetch, so collected pages are never returned as a successful partial result.

When some recipients accept email and others reject it, the CLI reports “Success With Warnings” and exits successfully after attempting all configured recipients. Refused recipient addresses are not included in the outcome log.

## Production deployment assumptions

The approved production target is a Docker deployment with reachable Jira and PostgreSQL, plus a Node.js cron job owned by the Project Administrator. Schedule the report for Monday at 09:00 in `JIRA_PROJECT_TIMEZONE`; recover a missed run on next startup and allow only one active run at a time. The scheduler and persistence integration are separate implementation tasks; this configuration task does not install or start them.

The production environment must provide Docker, PostgreSQL, network access to Jira, and stable network conditions. Do not deploy a Windows Task Scheduler job as the production scheduler.

## Tests and troubleshooting

Run the offline suite with:

```powershell
python -m unittest discover -s tests -v
```

- **Missing/invalid settings:** the command names required variables and exits without sending.
- **Jira HTTP 401/403:** check the account email, API token, base URL, and Browse Projects permission. Credentials are not included in application logs.
- **Jira network or rate-limit errors:** transient failures are retried a bounded number of times (`JIRA_MAX_RETRIES`) with capped backoff; permanent HTTP errors, invalid responses, incomplete pages, and exhausted retries stop the run without returning partial results.
- **No completed work or missing milestones:** check the configured JQL includes recently resolved issues and issues linked to relevant fix versions.
- **Email rejected:** verify sender, recipients, SMTP security mode, credentials, and mail-server policy. A rejected message is not reported as delivered.
- **Rotate credentials:** replace the secret in the deployment environment/secret store and revoke the old Jira token or SMTP credential; do not add secrets to Git.
