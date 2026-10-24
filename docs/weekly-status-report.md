# Weekly Jira Status Report

This application reads a configured Jira Cloud search scope, calculates the weekly status metrics, and renders a plain-text email report. It only reads Jira issues; it does not create or update tickets. It uses Python 3.11 or newer and the standard library (Windows installs also need the declared `tzdata` package).

## Setup

1. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -e .
   ```

2. Copy `weekly-status.env.example` to `weekly-status.env`. The latter is ignored by Git. Configure the Jira base URL, Jira account email, API token, project name, and a JQL scope that includes the current work and recently completed work needed for the report. The account needs permission to browse the selected Jira projects.
3. Set `JIRA_STORY_POINTS_FIELD` to the story-point custom field key used by your Jira instance, or leave it blank if story points are not used.
4. Keep Jira and SMTP credentials in the ignored environment file or inject them from the deployment secret store. The committed example contains placeholders only.

The file parser accepts one literal `KEY=VALUE` per line, ignores blank lines and full-line comments, and strips matching surrounding quotes. It does not expand variables or execute shell content. Process environment variables override values in the file.

## Run and preview

Use a fictional fixture to validate the workflow without Jira access:

```powershell
python -m status_reporter --fixture tests/fixtures/weekly_issues.json --env-file weekly-status.env
```

For a live Jira preview, omit `--fixture`. A normal run never sends email. The default reporting period is the previous Monday through Sunday, calculated in `REPORT_TIMEZONE`. To select an inclusive custom date range, pass both `--period-start YYYY-MM-DD` and `--period-end YYYY-MM-DD`. Use `--output preview.txt` to save a local report preview; store previews securely because issue summaries and assignees can be sensitive.

Send only after reviewing the report and configuring `SMTP_HOST`, `SMTP_PORT`, `SMTP_SENDER`, and `SMTP_RECIPIENTS`:

```powershell
python -m status_reporter --env-file weekly-status.env --send
```

SMTP authentication is optional. If used, provide both `SMTP_USERNAME` and `SMTP_PASSWORD`. Port 587 with STARTTLS is the default; set `SMTP_USE_SSL=true` for implicit TLS (typically port 465) and `SMTP_STARTTLS=false` when appropriate. Connection failures and temporary SMTP 4xx responses receive bounded retries (`SMTP_MAX_RETRIES`); permanent errors and uncertain disconnects during message delivery fail visibly without a potentially duplicating resend.

## Report definitions and assumptions

- **Open** means the Jira status is not in `REPORT_DONE_STATUSES`; done statuses default to Done, Closed, and Resolved.
- **Completed this period** means the issue has a done status and its Jira `resolutiondate` falls within the selected dates. The configured JQL must include those completed issues.
- **In progress** matches `REPORT_IN_PROGRESS_STATUSES`.
- **Blocked** matches a status in `REPORT_BLOCKED_STATUSES` or a label in `REPORT_BLOCKED_LABELS`.
- **At risk** matches a configured risk label, a configured high-priority value, or an overdue open due date.
- **Overdue** is an open issue whose due date is earlier than the report run date. **Due soon** is an open issue due between the run date and `REPORT_DUE_SOON_DAYS`, inclusive.
- **Milestones** are grouped from Jira fix versions. Completion is based on the done-status mapping; a past release date is Delayed, a release date within the due-soon window is At risk, and absent fix-version data is reported explicitly.
- **Health** is Red when the blocked or overdue count reaches its configured red threshold. Otherwise it is Yellow when the at-risk count reaches its threshold or a milestone is at risk/delayed. An empty Jira result is Yellow because there is no data on which to claim Green. Otherwise health is Green.
- Labels, status names, priorities, timezone, due-soon window, and health thresholds are configurable in the environment file. Status and label comparisons are case-insensitive.

Jira query scope is configured in `JIRA_JQL`; the application retrieves the matching set and paginates all results. Narrowing the query to only issues updated during the week can omit open work, due items, and older unresolved issues, so include the project or team scope needed for current metrics as well as recently resolved issues. Milestones are limited to fix versions attached to returned issues; no milestone is invented when Jira has no corresponding data.

## Weekly scheduling on Windows

Create a Windows Task Scheduler task for Monday morning in the same timezone as `REPORT_TIMEZONE`. Set the action's program to the Python executable from the project's virtual environment (for example, `C:\path\to\project\.venv\Scripts\python.exe`), arguments to:

```text
-m status_reporter --env-file weekly-status.env --send
```

Set **Start in** to the project directory. First run the same command without `--send` to review its preview and confirm the configured period and recipients. Store the environment file with restrictive filesystem permissions and disable the task or remove `--send` to stop delivery.

## Tests and troubleshooting

Run the offline suite with:

```powershell
python -m unittest discover -s tests -v
```

- **Missing/invalid settings:** the command names required variables and exits without sending.
- **Jira HTTP 401/403:** check the account email, API token, base URL, and Browse Projects permission. Credentials are not included in application logs.
- **Jira network or rate-limit errors:** transient failures are retried a bounded number of times (`JIRA_MAX_RETRIES`); persistent failures stop the run.
- **No completed work or missing milestones:** check the configured JQL includes recently resolved issues and issues linked to relevant fix versions.
- **Email rejected:** verify sender, recipients, SMTP security mode, credentials, and mail-server policy. A rejected message is not reported as delivered.
- **Rotate credentials:** replace the secret in the deployment environment/secret store and revoke the old Jira token or SMTP credential; do not add secrets to Git.
