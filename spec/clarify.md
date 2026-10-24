# Specification Review — Module 08

**Reviewed:** [`specification.md`](./specification.md) and [`constitution.md`](./constitution.md)  
**Source of truth:** [`project_spec.md`](../project_spec.md)

The specification establishes the report's broad purpose and safe default behavior, but several business rules and operational contracts remain open. Resolve the priority decisions below before treating the acceptance criteria as testable or deploying live delivery.

## Missing requirements

- **Define report-period semantics.** Specify the exact start/end boundaries, whether a Monday report covers the prior Monday–Sunday or the previous seven rolling days, which timezone determines the period, and how daylight-saving transitions are handled.
Resolution: The report period will cover the previous Monday through Sunday. All dates will use the Jira project timezone. Daylight-saving transitions will use the Jira instance timezone.
- **Define the Jira population.** Specify the initial project(s), saved filters or JQL, and whether each query must return both current unresolved work and issues resolved during the period. State how archived, canceled, duplicate, or out-of-scope issues are treated.
Resolution: The prototype will use one Jira project initially. Project selection will be configured through an environment variable. Canceled and duplicate issues will be excluded from reporting.
- **Define the reporting fields and requiredness.** List the Jira fields and custom-field identifiers needed for metrics, milestones, and estimates. Distinguish required fields (a missing value fails or excludes the issue) from optional fields (render as unavailable); define behavior for malformed records and partial pages.
Resolution: Required fields:

Issue Key
Summary
Status
Assignee
Due Date
Optional fields:

Epic
Story Points
Fix Version
Records missing required fields will be excluded from metrics and reported as validation warnings.
- **Make metrics reproducible.** Define the exact meaning and denominator for open, completed, in-progress, blocked, at-risk, overdue, and due-soon. State whether counts are distinct issue keys, how status changes and reopened issues are handled, and which date field determines completion during the period.
Resolution: Metrics will be calculated using unique issue keys.

Completed: Status = Done

Blocked: Issue contains the label blocked.

At Risk: Issue past due date and not completed.

Overdue: Current date greater than due date and status not Done.
- **Specify business rules.** Define status-to-category mappings, how blockers and at-risk items are identified, the due-soon window, and configurable Green/Yellow/Red thresholds, precedence, and boundary conditions. Explain how missing or contradictory signals affect health.
Resolution: Status mappings:

Done → Completed
In Progress → Active
Blocked → Blocked
To Do → Planned
At Risk: Issue due within 7 days and not completed.

Blocked: Issue contains the label "blocked" or status "Blocked".

Health thresholds:

Green: Less than 10% overdue issues
Yellow: 10%-20% overdue issues
Red: More than 20% overdue issues
- **Specify milestone calculations.** Identify the source field(s), whether Jira fix versions are authoritative, how progress percentage and target dates are derived, how multiple versions per issue are counted, and how missing, changed, or released versions are represented.
Resolution:

Milestones are derived from Jira Fix Versions.

Progress Percentage = Completed Issues / Total Issues × 100

Multiple Fix Versions: Count the issue in each assigned milestone.

Released milestones are shown as completed.
- **Define report completeness and size.** Set limits or prioritization for long issue lists, truncation behavior, treatment of empty sections, and whether the report includes decisions/support needed. Specify plain text versus HTML and any accessibility or formatting constraints.
Resolution:

Maximum report size: 100 issues.

When more than 100 issues are present:

Include summary statistics.
Include top priority issues.
Truncate remaining issue details.
Reports will be generated in plain-text format.
- **Define scheduling and operational outcomes.** Name the deployment target, Monday run time, timezone, behavior on missed/overlapping runs, alerting/ownership for failures, and how a successful run is distinguished from partial data retrieval or partial recipient delivery.
Resolution:

Schedule: Every Monday at 09:00.

Timezone: Project Jira timezone.

Successful run:

Jira data retrieved successfully.
Report rendered successfully.
Email sent successfully.
Failed runs generate an error log.
- **Define email delivery expectations.** Specify sender authorization, recipient configuration/validation, whether partial recipient rejection fails the run, and whether a delivery receipt or audit record is required.
Resolution:

Sender: Configured in environment variables.

Recipients: Configured in environment variables.

If one recipient fails:

Continue sending to other recipients.
Log failed recipient addresses.
Audit logging required for all deliveries.
- **Add measurable acceptance criteria.** Include examples or fixtures for metric edge cases, threshold boundaries, missing data, JQL pagination, schedule behavior, and email failure. State performance expectations (issue volume and maximum acceptable run duration) if they matter.
Resolution:

Acceptance Criteria:

Report generated in less than 60 seconds.
Process up to 100 Jira issues.
Handle paginated Jira API responses.
Missing optional fields do not fail processing.
Missing required fields are logged.
SMTP failures are reported clearly.
## Contradictions and tensions

1. **Required-data failure versus tolerant normalization.** The constitution says incomplete required Jira data must fail; the specification says to normalize missing/optional values without dropping otherwise valid issues, but does not define which fields are required. Agree on a required-field list and per-field failure/exclusion policy so the two rules can be tested together.
2. **Credential safety versus issue-data previews.** The constitution prohibits secrets in previews and reports, while the application renders Jira summaries and may include assignees. Clarify that credentials must never appear, and separately classify issue content and personal data as sensitive: define preview access, storage/retention, and whether assignee names are necessary for the audience.
3. **Retry requirement is incomplete.** The constitution and specification require bounded Jira retries, but do not define retryable conditions, attempt limits, backoff, or whether a failed page invalidates the entire report. The specification also says failures must be visible; prohibit presenting incomplete results as a successful complete report.
4. **Scheduling is external but the acceptance criterion is automatic scheduling.** The specification says scheduler deployment is external, yet acceptance requires the solution can be scheduled. Clarify whether providing a documented scheduler configuration/run command is sufficient, or whether deployment and verification of an actual scheduler are in scope.
5. **Email is required but delivery mode and acceptance are underspecified.** Email is the stated delivery method, but the requirements do not decide plain text versus HTML, SMTP versus a mail service, or how rejected recipients and ambiguous send outcomes are reported. Decide the transport contract while preserving explicit send opt-in.

## Ambiguous requirements — decisions to record

- What is the authoritative project/team scope, and who owns the JQL or saved filter?
- Does “completed in the period” use Jira resolution date, status-change history, or another event? How are reopenings handled?
- Are blocked status, labels, priority, issue links, or a combination authoritative? Which exact Jira values apply to this team?
- What qualifies as at risk, and what counts as a milestone being on track, at risk, or delayed?
- What does “configurable” mean in deployment: environment variables only, a committed non-secret settings file, or a secret manager as well?
- Should a failed project/page prevent the entire multi-project report, or can a clearly marked partial report be sent?
- Should delivery to any recipient be sufficient, or must every configured recipient accept the message?
- Is the scheduled Monday run expected before a particular leadership meeting, and should the schedule be expressed in a named business timezone?

## Security and privacy concerns

- **Secret storage and exposure:** environment variables satisfy the stated configuration option but may be exposed through process inspection, diagnostic dumps, or scheduler configuration. Define approved secret storage, access controls, rotation, and prohibition on logging environment values, authorization headers, SMTP credentials, or tokens.
- **Transport security:** require HTTPS for Jira and certificate verification; define SMTP TLS requirements and prohibit insecure fallback. Specify how proxy settings and custom certificate authorities are approved.
- **Least privilege:** require a dedicated Jira identity with read-only access to only the configured projects and a mail identity restricted to approved recipients where supported. Confirm the application never invokes Jira write endpoints.
- **Sensitive report contents:** issue summaries, assignee names, risks, and project status can be confidential or personal data. Define recipient authorization, preview file permissions, retention/deletion, log minimization, and whether names can be omitted or pseudonymized.
- **Recipient and sender control:** define how recipient lists are changed and reviewed, protect against accidental external delivery, and validate sender/recipient configuration before a send.
- **Untrusted Jira content:** if HTML is selected, escape Jira-provided text to prevent markup injection and unsafe links. For either format, prevent control characters or crafted issue text from corrupting logs, headers, or report structure.
- **Fixture and sample-data safety:** require fictional or sanitized data only in committed fixtures and examples; ensure test failures do not print credentials or sensitive fixture contents.

## Deployment assumptions to confirm

- The target runtime is Python 3.11 or newer, with dependencies installable in the deployment environment and a supported timezone database available.
- The service can reach the configured Jira host and mail endpoint from the scheduler's network, with required proxy, firewall, and certificate configuration documented.
- The selected Jira deployment supports the chosen REST API/authentication method and exposes the required fields/custom fields to the reporting account.
- Jira JQL can return the complete metric population within API limits; define expected maximum projects/issues and the policy when limits or pagination fail.
- A scheduler (for example, Windows Task Scheduler) is installed, has a stable working directory and Python environment, can read secrets securely, and runs with the intended timezone and service identity.
- The deployment owner will supply valid Jira credentials, sender authorization, recipients, business mappings, and milestones; fixture success alone does not prove live integration readiness.
- Define operational ownership for logs, alerting, credential rotation, missed reports, recovery, and upgrades. No monitoring or hosting platform is currently selected.

## Recommended clarification order

1. Agree on scope, period boundaries, field requiredness, metric definitions, risk rules, and milestone source.
2. Decide partial-data failure behavior, report sensitivity/retention, delivery policy, and approved secret/TLS controls.
3. Select the scheduler and deployment identity, set run time/timezone, and define monitoring and recovery ownership.
4. Convert the decisions into explicit acceptance examples and threshold-boundary tests before production delivery.
