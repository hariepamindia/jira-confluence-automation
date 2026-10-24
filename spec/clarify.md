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
At Risk: Issue due within 7 days and not completed.
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
Denominator: Total active issues included in the report.

Boundary Rules:

Green = 0% through 10% overdue issues
Yellow = More than 10% through 20% overdue issues
Red = More than 20% overdue issues
Empty Data Behavior: If there are no active issues, Health = Green.

Precedence: Blocked status overrides At Risk status. At Risk overrides Planned.
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
T01 Final Decision Record
Required Fields and Invalid Records
Resolution:

Required fields:

Issue Key
Summary
Status
Assignee
Due Date
If any required field is missing:

The issue is excluded from the report.
A validation warning is logged.
The report generation continues.
This overrides the constitution wording for the prototype.

Unassigned issues:

Excluded from reporting.
Issues without Due Dates:

Excluded from reporting.
At-Risk Definition
Resolution:

At Risk:

Due date is within 7 calendar days
Status is not Done
Past-due issues are classified as Overdue, not At Risk.

This is the only authoritative definition.

Blocked Definition
Resolution:

Blocked:

Issue status = Blocked
OR

Issue contains the label "blocked"
Either condition qualifies as Blocked.

Completion-In-Period Semantics
Resolution:

Completion Date:

Jira Resolution Date
Completed During Reporting Period:

Resolution Date falls between the reporting period start and end.
Reopened Issues:

Excluded from completed counts once reopened.
Timezone and DST
Resolution:

Authoritative timezone:

Jira Project Timezone
Daylight Saving Time:

Determined exclusively from the Jira Project Timezone.
The Jira Instance Timezone is ignored.

Partial Email Delivery
Resolution:

If one recipient fails:

Continue sending to remaining recipients.
Mark run status as Success With Warnings.
Log failed recipients.
Partial recipient failures do not fail the run.

Audit Logging
Resolution:

Audit log required.

Audit log contents:

Run timestamp
Reporting period
Recipient list
Delivery result
Error messages
Retention:

90 days
Storage:

Application log storage
Failure to write audit logs causes the run to fail.

Priority Ordering
Resolution:

Priority ranking:

Highest
High
Medium
Low
Tie-breaker:

Earliest Due Date
Then oldest creation date
Scheduling and Ownership
Resolution:

Schedule:

Every Monday at 09:00
Deployment Target:

Docker container
Owner:

Project Administrator
Missed Runs:

Execute immediately on next startup.
Overlapping Runs:

Not allowed.
Existing run must complete first.
Performance Conditions
Resolution:

60-second requirement includes:

Jira API calls
Pagination
Email delivery
Database operations
Maximum scope:

100 issues processed per run.
The report may display fewer than 100 issues if prioritization is applied.

Scope and Query Completeness
Resolution:

The query must include:

Current unresolved issues
Issues resolved during the reporting period
Canceled Issues:

Status = Cancelled
Duplicate Issues:

Resolution = Duplicate
Excluded from metrics and reporting.

Approval
Approved By: Project Owner

Approval Date: Module 17 Prototype Review

Status: Approved for implementation.
T01 Final Boundary Decisions
Field Validation
Malformed Values:

Missing required fields:

Exclude issue from reporting.
Log validation warning.
Continue processing.
Malformed values:

Exclude issue from reporting.
Log validation warning.
Continue processing.
Prototype Exception:

For this prototype, validation warnings do not fail the report run.

Active Issue Definition
Active Issues:

To Do
In Progress
Blocked
Completed Issues:

Done
Unmapped Statuses:

Treated as Active.
Included in denominator.
Logged as unmapped status.
At Risk Boundary Rules
At Risk:

Due date is today through seven calendar days in the future.
Status is not Done.
Examples:

Due today → At Risk
Due in 7 days → At Risk
Due in 8 days → Not At Risk
Past due yesterday → Overdue
Reopened Issues
Reopened Issues:

Reopened issues are removed from completed counts.
If completed again later:
Count using the latest Resolution Date.
Include only if the latest Resolution Date falls within the reporting period.
Priority Ordering
Priority Order:

Highest
High
Medium
Low
Tie-breakers:

Earliest Due Date
Oldest Creation Date
Lowest Jira Issue Key
Issue Volume Policy
Maximum Processing Volume:

Unlimited issue retrieval through Jira pagination.
Maximum Detailed Report Listing:

100 issues.
If more than 100 issues exist:

Process all issues.
Calculate metrics from all issues.
Report details limited to the highest-priority 100 issues.
Audit Access Controls
Audit Access:

Project Administrator only.
Stored Fields:

Timestamp
Reporting period
Recipient count
Delivery result
Error summary
Not Stored:

Email content
API tokens
Secrets
Passwords
Retention:

90 days
Scheduler Definition
Scheduler:

Docker scheduled task.
Runs every Monday at 09:00 Jira Project Timezone.
Missed Run:

Execute once at next startup.
Overlap Prevention:

New run cannot start while a previous run is active.
Performance Test Conditions
Performance Target:

Process 100 issues in under 60 seconds.
Measurement Includes:

Jira API retrieval
Pagination
Database operations
Report generation
Email delivery
Measurement Excludes:

Manual user approval time
Test Environment:

Docker deployment
PostgreSQL running
Jira API reachable
Approval Test Cases
At Risk Example:

Due in 7 days → At Risk
Due in 8 days → Not At Risk
Health Example:

0 active issues → Green
10 overdue of 100 active → Green
11 overdue of 100 active → Yellow
20 overdue of 100 active → Yellow
21 overdue of 100 active → Red
Partial Delivery Example:

4 recipients succeed
1 recipient fails
Result:

Success With Warnings

Approved By: Project Owner

Status: Approved for Implementation
T01 Final Reconciliation and Test Cases
Constitution Exception
Prototype Exception:

The constitution's fail-on-incomplete-data rule is modified for the prototype.

Missing or malformed required fields:

Exclude the issue from reporting.
Record validation warnings.
Continue processing other issues.
This exception is approved by the Project Owner and applies only to the prototype.

Reporting Period Boundaries
Reporting Period:

Start: Monday 00:00:00 (Jira Project Timezone)

End: Sunday 23:59:59 (Jira Project Timezone)

Examples:

Monday 00:00:00 → Included
Sunday 23:59:59 → Included
Sunday 23:59:58 → Included
Next Monday 00:00:00 → Excluded
Priority Ordering Examples
Example A:

Issue A: Priority = High Due Date = Jan 1

Issue B: Priority = High Due Date = Jan 5

Result: Issue A ranked before Issue B.

Example B:

Issue A: Priority = High Due Date = Jan 1 Created = Jan 1

Issue B: Priority = High Due Date = Jan 1 Created = Jan 5

Result: Issue A ranked before Issue B.

Example C:

Priority, Due Date and Creation Date identical

Result: Lowest Jira Issue Key wins.

PostgreSQL Usage
PostgreSQL stores:

Report execution history
Generated report metadata
Audit metadata
Audit logs remain in application logs.

Database operations included in performance testing:

Report metadata writes
Report execution history writes
Performance Test Procedure
Test Environment:

Docker deployment
PostgreSQL running
Jira API available
Network Assumption:

Stable network connection
No artificial throttling
Procedure:

Query Jira
Process 100 issues
Generate report
Store metadata
Send email
Pass Criteria:

Complete in under 60 seconds.

Scheduler Implementation
Scheduler Mechanism:

Node.js scheduled job using cron scheduling.

Execution:

Every Monday at 09:00 using Jira Project Timezone.

Missed Run:

Execute on next startup.

Overlap Protection:

Only one active run allowed.

Audit Field Reconciliation
Superseding Decision:

Recipient Count replaces Recipient List.

Stored:

Recipient Count
Not Stored:

Recipient email addresses
Reason:

Reduce exposure of personal information.

Status Mapping Completion
Final Status Mapping (Authoritative)

This mapping supersedes all previous mappings.

To Do -> Planned
In Progress -> Active
Blocked -> Blocked
Done -> Completed

Denominator Membership:

Planned -> Included
Active -> Included
Blocked -> Included
Completed -> Excluded

Unmapped Statuses:

Treated as Active
Included in denominator
Logged as warning

Precedence:

1. Blocked
2. At Risk
3. Active
4. Planned
5. Completed

Examples:

Status = Blocked
Result = Blocked

Status = In Progress and due in 5 days
Result = At Risk

Status = In Progress and due in 30 days
Result = Active

Status = To Do
Result = Planned

Status = Done
Result = Completed
Reopened Issue Example
Issue completed on Wednesday: Counted as completed.

Issue reopened on Thursday: Removed from completed count.

Issue completed again on Saturday: Counted using Saturday Resolution Date.

Approval
Approved By: Project Owner

Status: Final Approval Granted

Implementation Authorized.