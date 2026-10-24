# Implementation Tasks — Module 08 Weekly Stakeholder Status Reporting

This task breakdown follows [`plan.md`](./plan.md), with source requirements in [`specification.md`](./specification.md) and unresolved issues tracked in [`clarify.md`](./clarify.md). Tasks are ordered by dependency, not strictly by priority. Tasks involving business rules or production operations remain gated until their required decisions are recorded.

## Task T01 — Resolve business and deployment decision gates

**Description**  
Work with the project owner to resolve the contradictory or open decisions in `clarify.md`. Record the approved rules for required Jira fields and invalid records, at-risk definition, health thresholds and denominator, timezone source, partial-recipient success, audit contents/retention, issue-detail priority ordering, scheduler ownership and recovery, and the 60-second measurement conditions. Confirm single-project scope, canceled/duplicate exclusions, reporting period, and field mappings.

**Acceptance Criteria**

- `clarify.md` records an unambiguous, approved answer for every decision gate listed in `plan.md`.
- Required versus optional fields and behavior for missing, malformed, or excluded issues are specified per field.
- Metric formulas, date boundaries, health thresholds, denominator, empty-data behavior, and priority tie-breaker have testable examples.
- Timezone/DST, recipient partial-failure, audit storage/access/retention, scheduler, and performance measurement conditions are approved.
- No decision is silently inferred by implementation.

**Dependencies**

- None.

## Task T02 — Finalize secure application configuration

**Description**  
Review and refine the existing configuration loader and example to support the approved Jira project/JQL scope, fields, timezone, metric mappings and thresholds, 100-issue detail cap, mail transport, recipients, retry limits, and audit settings. Define secure secret injection and enforce approved HTTPS/TLS and recipient policies.

**Acceptance Criteria**

- Required settings are validated before network access; invalid values return actionable errors and a failing exit status.
- Jira URLs require HTTPS and SMTP uses the approved TLS configuration without insecure fallback.
- Credentials are loaded only from the approved environment/secret source and never logged or included in report output.
- The committed example contains placeholders only, and actual secret files are ignored by version control.
- Configuration tests cover missing/invalid settings, thresholds, timezone, recipients, and secret-safe errors.

**Dependencies**

- T01.

## Task T03 — Implement Jira search, pagination, and retries

**Description**  
Implement or refine the read-only Jira REST adapter. Query the configured project and reporting population with the agreed fields; paginate all results, apply bounded retries only to transient failures, and enforce timeouts and TLS certificate verification.

**Acceptance Criteria**

- Requests use the configured scope, approved fields, HTTPS, and read-only search operations only.
- All pages are retrieved; duplicate issue keys are handled according to the approved policy.
- Retry count and backoff are bounded and configurable; permanent errors are not retried as transient.
- Exhausted retries, malformed responses, and empty/incomplete pages fail visibly; no partial result is presented as complete.
- Tests cover pagination, request field/scope construction, transient and permanent failures, TLS configuration, and retry exhaustion.

**Dependencies**

- T02.

## Task T04 — Normalize and validate Jira issues

**Description**  
Normalize Jira responses into typed issue records using approved fields and timezone rules. Distinguish legitimate null/empty optional values from missing or malformed required data, de-duplicate by issue key, and exclude canceled/duplicate items as agreed.

**Acceptance Criteria**

- Each normalized record retains the approved required fields and optional values without silently inventing missing data.
- Missing/malformed fields follow the T01 policy and produce issue-context diagnostics without credentials or unnecessary sensitive details.
- Dates are parsed consistently in the approved timezone, including DST boundaries.
- Duplicate, canceled, and excluded issues follow the approved rules and do not inflate metrics.
- Tests cover complete records, null optional values, missing required fields, malformed dates/statuses, duplicates, exclusions, and timezone transitions.

**Dependencies**

- T01, T02.

## Task T05 — Integrate complete Jira data collection

**Description**  
Connect the Jira adapter to normalization and validation so the application either returns a complete, validated issue population or a visible failed result. Confirm the JQL/scope includes both current work and period completions.

**Acceptance Criteria**

- Live retrieval produces normalized unique issue records from every Jira result page.
- The configured population includes current open work and completed items needed for the reporting period.
- Any failed page or disallowed validation condition fails the collection stage rather than yielding success-shaped partial data.
- Integration tests cover adapter-to-normalizer behavior with mocked Jira responses and sanitized fixtures.
- No Jira write operation is made.

**Dependencies**

- T03, T04.

## Task T06 — Calculate deterministic issue metrics

**Description**  
Implement issue counts for total, open/current, completed in period, active/in-progress, planned, blocked, at-risk, overdue, and due soon. Use unique issue keys, approved statuses, completion date semantics, reporting boundaries, and the agreed treatment of reopened issues.

**Acceptance Criteria**

- Each metric matches its approved definition and counts unique issues only.
- Completed-period membership and due/overdue boundaries use the approved dates and timezone.
- At-risk and overdue are distinct or combined exactly as approved in T01.
- Empty datasets and missing optional dates have explicit, tested behavior.
- Tests cover every status/category, exact start/end and due-date boundaries, reopened items, duplicates, and empty scope.

**Dependencies**

- T01, T04.

## Task T07 — Calculate health classification and rationale

**Description**  
Calculate overdue percentage using the approved denominator and classify the project Green, Yellow, or Red with configured thresholds and precedence. Retain an explanation that makes the result auditable.

**Acceptance Criteria**

- Health uses the approved denominator, threshold inclusivity, empty-denominator rule, and precedence.
- Classification explains the relevant counts, percentage, and threshold without exposing secrets.
- Missing or contradictory signals follow the agreed policy and are not reported as Green without evidence.
- Tests cover values below, at, and above each threshold, including exactly 10%, 20%, and an empty denominator if applicable.

**Dependencies**

- T01, T06.

## Task T08 — Aggregate Jira Fix Version milestones

**Description**  
Aggregate milestone status and progress from Jira Fix Versions. Count an issue once within each assigned version, apply the approved completion mapping, preserve target dates, and mark released milestones complete.

**Acceptance Criteria**

- Progress percentage equals completed assigned issues divided by total assigned issues using the approved rounding rule.
- Issues linked to multiple Fix Versions contribute once to each corresponding milestone.
- Released milestones are shown as complete; missing target dates or milestone data are explicitly identified.
- Tests cover multiple versions, zero/empty cases, date boundaries, released versions, and absent Fix Version data.

**Dependencies**

- T01, T04.

## Task T09 — Generate actionable recommendations

**Description**  
Generate concise next steps based on actual blockers, risks, overdue work, and milestone state. Avoid unsupported recommendations where the data is unavailable.

**Acceptance Criteria**

- Recommendations are derived from report findings and match the approved rule set.
- Blockers, overdue work, at-risk items, and milestone concerns produce relevant actions.
- No-data cases are clearly stated; recommendations do not assert facts absent from Jira.
- Tests cover each trigger, combinations, and the no-risk/default case.

**Dependencies**

- T06, T07, T08.

## Task T10 — Render the bounded plain-text report

**Description**  
Render the project/week subject and stakeholder report sections: health and rationale, summary metrics, completed highlights, risks/blockers, milestone status, upcoming actions, and recommended next steps. Limit detailed issue listings to 100 and apply the approved priority ordering above that limit.

**Acceptance Criteria**

- Output is plain text and includes every required section, project name, and reporting period.
- Summary statistics remain complete when issue details are truncated; the report states how many details were omitted.
- The selected issue details follow the approved priority ordering and deterministic tie-breaker.
- Empty sections and optional fields render consistently without fabricated values.
- Jira-provided text is sanitized against control characters and cannot corrupt report layout or subject/header values.
- Rendering tests assert exact subject shape, required sections, metrics, truncation, and safe handling of Jira text.

**Dependencies**

- T06, T07, T08, T09.

## Task T11 — Implement per-recipient email delivery and audit

**Description**  
Deliver the rendered report through the approved mail transport only when explicitly requested. Validate sender/recipients, enforce TLS and authentication policy, continue after recipient-specific rejection when required, and persist an approved secret-minimized audit record for each delivery.

**Acceptance Criteria**

- No email is sent in preview/default mode; explicit send opt-in is required.
- TLS, sender, and recipient validation follow the approved policy.
- A recipient-specific failure does not prevent attempts to remaining recipients; the final run result follows the approved partial-delivery rule.
- Audit records contain required delivery outcomes and timestamps, omit credentials, minimize personal data, and follow approved access/retention settings.
- Transient retries are bounded; permanent and ambiguous outcomes are not blindly retried.
- Tests cover full success, partial/all rejection, authentication/TLS failures, transient/permanent errors, ambiguous outcomes, and audit failure.

**Dependencies**

- T01, T02, T10.

## Task T12 — Complete CLI orchestration and run outcomes

**Description**  
Wire configuration, fixture/live Jira input, reporting, rendering, optional output preview, and explicit sending through the command-line entry point. Report stage outcomes, log safely, and return an accurate process exit status.

**Acceptance Criteria**

- Fixture mode runs without network access; live mode retrieves Jira; both produce a preview by default.
- Only an explicit send option invokes email delivery.
- Invalid configuration, incomplete Jira retrieval, rendering failure, and required delivery/audit failures produce visible errors and nonzero exit status.
- A successful status is returned only for stages defined as successful by the approved partial-delivery policy.
- Logs include run/period/stage outcomes without secrets or unnecessary Jira content.
- CLI tests cover preview, send opt-in, failures, and exit codes.

**Dependencies**

- T02, T05, T10, T11.

## Task T13 — Add fixture and automated acceptance coverage

**Description**  
Create or update fictional sanitized Jira fixtures and automated unit/integration tests for normalization, metrics, health boundaries, milestones, rendering, pagination/retries, delivery/audit, and CLI orchestration.

**Acceptance Criteria**

- Fixture data contains no real credentials, personal data, or proprietary issue content.
- Test coverage includes all acceptance edge cases in T03–T12 and the approved T01 decision examples.
- The full fixture-backed CLI path runs without network access or SMTP delivery.
- Test failures do not expose secrets or unnecessarily repeat issue content.

**Dependencies**

- T03, T04, T06, T07, T08, T09, T10, T11, T12.

## Task T14 — Document setup, operation, and recovery

**Description**  
Document Python setup, Jira permissions and fields, configuration and secret provisioning, metric definitions, timezone, preview/send workflow, audit policy, scheduler setup, troubleshooting, recovery, and disabling delivery.

**Acceptance Criteria**

- Documentation matches the implemented configuration and approved business rules.
- Jira read-only permissions, required fields, project scope/JQL, date boundaries, thresholds, and milestone semantics are documented.
- Secret storage/rotation, recipient approval, report sensitivity, preview retention, and audit access/retention are documented.
- Operators can perform a dry run, enable/disable delivery, diagnose failures, and recover a missed/failed run.
- No documentation example contains actual secrets or live sensitive data.

**Dependencies**

- T01, T02, T06, T07, T08, T10, T11, T12.

## Task T15 — Configure and verify scheduled deployment

**Description**  
Package the application and configure the approved scheduler to run each Monday at 09:00 in the authoritative Jira project timezone. Set the service identity, working directory, secret access, overlap/missed-run behavior, and failure alert/ownership.

**Acceptance Criteria**

- Scheduler invokes the documented application command at the approved local time, including across DST transitions.
- Task uses a restricted service identity and approved secure secret injection.
- Working directory, Python environment, overlap prevention, missed-run behavior, failure logging/alerting, and operator ownership are configured and documented.
- An isolated deployment-like run verifies schedule/timezone and expected exit/failure behavior.
- Production recipients are not enabled before stakeholder sign-off.

**Dependencies**

- T01, T02, T12, T14.

## Task T16 — Verify performance, security, and release readiness

**Description**  
Execute the complete acceptance and rollout checks: 100-issue pagination, the agreed sub-60-second measurement, secret and transport checks, read-only Jira verification, report review, and controlled non-production integration tests.

**Acceptance Criteria**

- Processing 100 issues and all required pages completes within the T01-approved under-60-second measurement conditions.
- Automated tests and fixture end-to-end dry run pass.
- HTTPS/TLS enforcement, least-privilege read-only access, secret redaction, recipient policy, report sanitization, and audit controls are verified.
- Live integration tests use approved non-production Jira/mail configuration and authorized recipients only.
- Stakeholders approve the report, metrics, recipient list, audit handling, and first-run preview.
- No production schedule or email delivery is enabled while any release gate in `plan.md` remains open.

**Dependencies**

- T01, T05, T13, T14, T15.
