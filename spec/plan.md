# Implementation Plan — Module 08 Weekly Stakeholder Status Reporting

**Inputs:** [constitution](./constitution.md), [specification](./specification.md), [clarification review](./clarify.md)  
**Source of truth:** [project specification](../project_spec.md)

## Objective

Deliver a read-only Jira reporting application that produces a plain-text weekly report for one configured project, then emails it to configured recipients. The schedule is Monday at 09:00 in the agreed Jira project timezone. A normal/manual run previews the report and never sends mail; sending requires explicit operator opt-in.

Build on the existing `status_reporter` package, fixture, tests, `pyproject.toml`, environment example, and operations guide where they meet these decisions. Refine existing behavior rather than creating a parallel implementation.

## Decisions recorded in `clarify.md`

- Initially report one project, selected through environment configuration; exclude canceled and duplicate issues.
- Use unique Jira issue keys for counting. The clarified status mapping is Done → Completed, In Progress → Active, Blocked → Blocked, and To Do → Planned.
- A blocked issue is identified by the `blocked` label or Blocked status. The clarification gives two conflicting definitions of At Risk: overdue and not completed, versus due within seven days and not completed. Resolve this before finalizing the classifier.
- Derive milestones from Jira Fix Versions. Progress is completed assigned issues divided by total assigned issues; an issue assigned to multiple versions counts in each. Released milestones are complete.
- Reports are plain text and summarize at most 100 issue details; when over the limit, retain summary statistics and the highest-priority issue details.
- Run every Monday at 09:00 in the project Jira timezone. Jira retrieval, report rendering, and email delivery must all succeed for a successful run.
- Continue delivery to other recipients if one recipient is refused, and keep an audit record for every delivery.
- Target up to 100 issues and report generation in under 60 seconds; support Jira pagination and clear SMTP error reporting.

## Decision gates before production semantics are frozen

These items are unresolved or contradictory in the source documents. Record an agreed answer in `clarify.md` before relying on affected behavior in production:

1. **Required versus optional fields.** The clarified required-field list includes Assignee and Due Date, although Jira issues can legitimately have no assignee or due date. The constitution requires incomplete required data to fail, while the clarification says to exclude incomplete records and log warnings. Approve field-by-field handling and whether any excluded issue makes the run fail.
2. **Health thresholds and denominator.** Clarify whether overdue percentage is calculated over all issues or open issues, whether Green is `<10%`, Yellow is `10–20%` inclusive, and Red is `>20%`, and the intended outcome at exactly 20%. Specify how an empty denominator is classified.
3. **At-risk boundary.** Select one definition (overdue open work or open work due within seven days), or explicitly keep separate “at risk” and “overdue” categories. Confirm inclusive/exclusive date boundaries and the run-date timezone.
4. **Timezone source.** Identify the authoritative Jira project timezone setting and how Task Scheduler applies it across daylight-saving changes. Clarify the relation to the Jira instance timezone also named in the clarification.
5. **Delivery audit and partial-recipient result.** Select audit storage, access and retention; define which recipient identifiers may be logged, how partial delivery is reported, and whether it fails the overall run despite continuing delivery to other recipients.
6. **Top-priority ordering.** Define priority ordering and a deterministic tie-breaker for selecting issue details when more than 100 issues match.
7. **Deployment target and ownership.** Confirm Windows Task Scheduler as the production scheduler, the service identity and secure secret provision, failure alerting/ownership, missed-run behavior, and overlap prevention.
8. **60-second target conditions.** Define whether the target includes Jira/SMTP network time and retries, and the test environment and representative response latency.

No production email rollout should proceed while these gates affect report correctness, privacy, or whether delivery is considered successful.

## Architecture and responsibilities

Keep the application modular and Jira read-only:

1. **Configuration and secrets:** Validate project/JQL scope, reporting timezone, Jira and mail endpoints, field mappings, status rules, thresholds, report limit, and credentials. Load secrets only from environment variables or an approved secret store. Reject insecure transport configuration.
2. **Jira adapter:** Query the configured project and required reporting population; request required and optional fields; follow every result page; apply bounded retries only to transient failures. Never log credentials or return an incomplete result as complete.
3. **Normalization and validation:** Convert Jira values into typed issue records keyed by unique issue key. Distinguish a legitimate absent value from a malformed/missing field. Apply the approved required-field policy and emit contextual, secret-free warnings or errors.
4. **Reporting domain:** Calculate distinct issue metrics, weekly completions, current status groups, blockers, risks, due dates, overdue percentage, and Fix Version progress using the approved rules and boundaries. Keep classification reasons alongside the health result.
5. **Plain-text renderer:** Produce the subject and required report sections, period and health rationale, concise issue context, milestone progress, recommendations, and the agreed capped list. Treat Jira content as untrusted text and prevent control characters from changing report structure.
6. **Email delivery and audit:** Validate sender and recipients; use authenticated TLS SMTP or the approved mail transport. Attempt delivery for each recipient according to the partial-refusal policy, record success/failure without secrets, and surface the overall result accurately.
7. **Command and scheduler:** Provide fixture-backed preview, live Jira preview, and explicit send modes. Return a nonzero exit on required-stage failure. Keep scheduling external to the application and document the approved Windows Task Scheduler setup.

## Phased implementation

### Phase 1 — Resolve business and operational decisions

- Resolve the decision gates above with the project owner and update `spec/clarify.md`.
- Translate the accepted definitions into configuration names, field mappings, report behavior, and boundary examples.
- Confirm the project scope/JQL includes both current open work and issues completed in the reporting period; document exclusions for canceled and duplicate issues.
- Confirm that the report period is the previous Monday through Sunday, and identify the authoritative project timezone and daylight-saving behavior.

**Exit criteria:** No unresolved choice remains for required-field handling, risk/health calculations, timezone, recipient/audit semantics, or priority truncation.

### Phase 2 — Secure configuration and validated Jira data

- Reuse and review the current configuration loader; validate the configured project and HTTPS Jira endpoint, TLS verification, timezone, field identifiers, thresholds, recipient allowlist/policy, and required secrets.
- Request issue key, summary, status, assignee, due date, resolution/completion data, priority, labels, and Fix Version fields, plus configured optional/custom fields.
- Implement/verify pagination, duplicate-key de-duplication, bounded transient retry/backoff, timeout behavior, and explicit failure if a page cannot be retrieved.
- Normalize Jira dates consistently in the approved project timezone. Apply the agreed missing-field policy; never silently treat malformed data as valid.
- Use a dedicated read-only Jira identity with access limited to the configured project. Confirm no write endpoint is called.

**Exit criteria:** Fixtures cover complete records, legitimate empty optional values, missing required values, malformed values, duplicate keys, multiple pages, and exhausted retries. Failures cannot yield a success-shaped partial report.

### Phase 3 — Implement deterministic metrics and health

- Calculate distinct total/current-open issues, Done issues for the reporting period, In Progress and To Do groups, blocked, at-risk, overdue, and due-within-seven-days counts using approved status/date boundaries.
- Calculate overdue percentage with the approved denominator and exact Green/Yellow/Red boundaries; include numerator, denominator, threshold, and explanation in the report rationale where useful.
- Aggregate Fix Version milestones; count an issue once per assigned version, calculate completed/total progress, preserve target date, and treat released versions as complete.
- Exclude canceled and duplicate issues according to the approved rule and make exclusions visible in validation diagnostics without exposing sensitive issue content unnecessarily.
- Generate next steps from the actual blockers, risks, overdue items, and milestone state; do not infer missing milestone or date values.

**Exit criteria:** Unit tests exercise every category, date edge, reopened/done status interpretation, exact health boundary, empty denominator, duplicate, multi-version issue, released milestone, and missing milestone case.

### Phase 4 — Render and cap the stakeholder report

- Render the configured project and Monday–Sunday reporting period, health and explanation, summary metrics, completed highlights, current risks/blockers, milestone status, upcoming actions, and recommended next steps in plain text.
- Limit detailed issue entries to 100. Above the configured report cap, retain aggregate statistics and choose detail rows by the approved priority order and tie-breaker; state how many details were omitted.
- Handle empty categories and absent optional values consistently; include missing-data warnings without fabricating values.
- Sanitize untrusted Jira text for plain-text layout and email headers. Do not put credentials, tokens, or unnecessary personal data in the report.

**Exit criteria:** Rendering tests assert required sections, subject format, reporting dates, accurate metrics, truncation behavior, empty sections, safe Jira text, and absence of secrets.

### Phase 5 — Deliver email and audit outcomes

- Validate the sender and each configured recipient against the approved delivery policy before sending. Require explicit `--send` (or an equally explicit invocation) for live delivery.
- Use TLS with certificate verification and the selected authentication method; do not fall back to plaintext.
- Continue to remaining recipients after a recipient-specific refusal, record per-recipient outcomes in the approved audit store, and return/report the agreed partial-delivery outcome.
- Retry only approved transient connection/server failures with a bounded attempt count. Do not blindly resend after an ambiguous outcome where the server may already have accepted the message.
- Ensure logs/audit entries exclude credentials and minimize report content and personal data; enforce the approved access and retention policy.

**Exit criteria:** Mocked tests cover full success, one/all recipient refusals, authentication failure, TLS failure, transient retry, permanent rejection, ambiguous send outcome, audit writing failure, and explicit no-send default.

### Phase 6 — Schedule, document, and operationalize

- Package and install the application in the selected supported Python environment. Lock or otherwise control dependency versions for deployment.
- Configure the approved scheduler for Monday at 09:00 in the authoritative timezone, with a stable working directory, restricted service identity, secure secret access, and overlap/missed-run behavior.
- Document setup, Jira read permissions and fields, metric definitions, timezone, secret provisioning/rotation, recipient review, dry run, live delivery, audit access/retention, troubleshooting, recovery, and how to disable the task.
- Add run-start/end and stage/result logging, a clear nonzero failure status, and the agreed operational alert/ownership process. Avoid issue descriptions, credentials, or unnecessary personal data in logs.

**Exit criteria:** A deployment-like scheduled invocation uses the intended timezone and scope; test or fixture failures alert/exit as documented; an operator can disable, rerun, and recover a failed run.

### Phase 7 — Acceptance and controlled rollout

- Run the automated test suite and a complete fixture-backed dry run without network access or email.
- Test live Jira retrieval and email delivery only in an approved non-production/test configuration with authorized credentials and recipients.
- Demonstrate support for 100 issues and pagination; measure report generation against the agreed sub-60-second test conditions.
- Verify sample/fixture data is fictional, secret scanning and repository checks are clean, no credentials occur in logs or output, and no Jira write request is possible.
- Conduct stakeholder review of the sample report, metric interpretations, recipient list, and delivery audit. Enable the production schedule only after sign-off.

**Release gate:** All acceptance checks pass, unresolved decision gates are closed, delivery/audit behavior is approved, and the explicit dry-run preview has been reviewed before the first production send.

## Test strategy

- **Unit tests:** Configuration validation; Jira normalization; issue classification; date/timezone boundaries; unique counts; risk and health formulas; Fix Version progress; recommendation generation; rendering and truncation.
- **Integration tests with mocks:** Jira authentication and TLS configuration, pagination and bounded retry, malformed/partial Jira responses, SMTP TLS/authentication, per-recipient outcomes, audit persistence, and process exit codes.
- **Fixture end-to-end test:** Exercise CLI → fixture normalization → metrics → health → rendering → preview output with no network calls and no mail delivery.
- **Deployment verification:** Validate the Windows scheduler command, working directory, service identity, secure configuration, Monday 09:00 schedule, timezone/DST behavior, and failure alert/exit behavior in a controlled environment.
- **Performance and security checks:** Measure the agreed 100-issue scenario against the 60-second target; verify secret redaction, HTTPS/TLS enforcement, report-content handling, read-only Jira scope, fixture sanitization, and audit access/retention.

## Dependencies and release constraints

- Jira project scope, field availability, timezone, read-only credentials, and API permissions.
- Approved business definitions and thresholds, especially the open decisions listed above.
- Authorized sender, mail endpoint, recipient list, TLS/authentication configuration, and audit storage.
- A supported Python runtime, timezone data, network access, and deployment scheduler/service identity.
- Stakeholder approval of report content and privacy handling before production recipients are enabled.
