# Implementation Plan — Checklist Gaps

**Scope:** Address the five approved implementation gaps in [`checklist.md`](./checklist.md). This is a plan only; no application code is changed here.

## Implementation sequence

Implement in dependency order:

1. Make issue-level validation tolerant and exclude invalid records.
2. Exclude canceled and duplicate issues from the report population.
3. Align status classification, metric formulas, and health with the final clarification.
4. Apply deterministic, capped detail selection without truncating metric counts.
5. Implement per-recipient delivery and report partial success accurately.
6. Run the full suite and update operator documentation after the behaviors are integrated.

Page-level Jira failures remain fatal and fail closed, as required by T03. Only malformed individual records are skipped under the approved prototype exception.

## Gap 1 — Exclude invalid issue records and continue

**Current gap:** Jira/fixture normalization currently raises on an invalid issue and aborts the run. The approved prototype rule is to exclude the issue, log a safe validation warning, and continue with valid issues.

**Files to modify**

- `status_reporter/jira.py` — validate required fields, including Issue Key, Summary, Status, Assignee, and Due Date; handle issue-level normalization failures while retaining page-level failure behavior.
- `status_reporter/cli.py` — apply the same tolerant issue validation in fixture mode so fixture and live behavior agree.
- `tests/test_status_reporter.py` — add live-page and fixture mixed-validity cases.
- `docs/weekly-status-report.md` — describe required fields, exclusions, warnings, and continued processing.

**Acceptance criteria affected**

- Specification F2 and F7; acceptance A2.
- Task T04: required/malformed field policy and issue-context diagnostics.
- Task T05: complete collection while distinguishing issue exclusions from failed pages.
- Task T12: safe warnings and correct run status.
- Task T13: prototype invalid-record test coverage.

**Tests to add/update**

- A page/fixture with one valid issue and one issue missing each required field: only the valid record is included; processing continues.
- Malformed required values (including date, assignee, and status structures) are excluded with a warning that identifies the issue safely and does not emit full Jira content or credentials.
- A page-level pagination or transport failure still fails the whole retrieval; previously collected records are not returned as successful partial output.
- Fixture CLI returns success when valid records remain and returns an explicit appropriate outcome when all records are excluded.

## Gap 2 — Exclude canceled and duplicate-resolution issues

**Current gap:** The current data model does not retain Jira resolution identity, and reporting does not exclude Cancelled statuses or Duplicate resolutions consistently.

**Files to modify**

- `status_reporter/jira.py` — request Jira's resolution field and normalize its name.
- `status_reporter/models.py` — retain optional resolution on `IssueRecord`.
- `status_reporter/reporting.py` — filter Cancelled and Duplicate issues before totals, metrics, milestones, and recommendations are calculated.
- `tests/fixtures/weekly_issues.json` — add sanitized canceled and duplicate-resolution examples.
- `tests/test_status_reporter.py` — assert exclusion across report outputs.
- `docs/weekly-status-report.md` — confirm the exclusion policy and required Jira field access.

**Acceptance criteria affected**

- Specification F2 and F3; acceptance A2.
- Task T04: exclusions do not inflate metrics.
- Task T06: unique issue metric counts.
- Task T08: excluded issues do not affect milestone totals.
- Task T13: canceled/duplicate acceptance coverage.

**Tests to add/update**

- Cancelled status is absent from total/open/completed counts, detail listings, milestone totals, and recommendations.
- Resolution `Duplicate` is excluded even if the issue's current status otherwise appears reportable.
- Null/missing resolution remains valid for non-duplicate issues.
- Case handling follows the agreed Jira value comparison behavior.

## Gap 3 — Align status, metric, and health rules with final decisions

**Current gap:** Reporting still applies legacy label/priority risk rules and count-based health thresholds. It does not fully apply approved status category precedence, the active denominator, reopened completion behavior, or the zero-active Green rule.

**Files to modify**

- `status_reporter/reporting.py` — derive each issue's category/state from the approved mappings and precedence; calculate due-based At Risk separately from Overdue; calculate completion from current Done status and latest resolution date; calculate the overdue ratio against the approved active denominator.
- `status_reporter/config.py` — use validated percentage thresholds as the health policy and remove or deprecate legacy count-threshold settings where they conflict.
- `status_reporter/models.py` — add report fields for category counts, denominator, overdue percentage, or other data required to explain classification accurately.
- `weekly-status.env.example` — ensure only effective approved metric settings are presented.
- `tests/test_status_reporter.py` — replace conflicting legacy assertions and add clarified boundary cases.
- `docs/weekly-status-report.md` — ensure metric and health descriptions match executable behavior.

**Acceptance criteria affected**

- Specification F3 and F4; acceptance A2.
- Task T06: deterministic metrics, date boundaries, reopened issues, and empty scope.
- Task T07: denominator, inclusive thresholds, zero denominator, and rationale.
- Task T09: recommendations based on the resulting findings.
- Task T13: decision-example regression coverage.

**Tests to add/update**

- Verify To Do → Planned, In Progress → Active, Blocked → Blocked, Done → Completed; unmapped statuses behave as Active and produce a safe warning.
- Verify precedence for Blocked, At Risk, Active, Planned, and Completed.
- Verify At Risk is non-Done and due today through seven calendar days; overdue is earlier than today and is not also At Risk.
- Verify reopened issues do not count as completed while unresolved; a re-completed issue uses its latest Jira Resolution Date.
- Verify the active denominator includes Planned, Active, Blocked, and unmapped statuses, and excludes Completed.
- Verify health at and around 10%, 20%, and above 20%, including 10/100 Green, 11/100 Yellow, 20/100 Yellow, and 21/100 Red; use exact ratios, not rounded display values.
- Verify zero active issues is Green and reasons report the relevant numerator, denominator, ratio, and threshold.

## Gap 4 — Apply global detail ordering and the configured 100-item cap

**Current gap:** Report sections use independent hard-coded slice limits and do not apply the configured maximum-100 deterministic priority ordering.

**Files to modify**

- `status_reporter/reporting.py` — select detailed issues using priority, earliest due date, oldest creation date, and lowest Jira key, while calculating all metrics from the full eligible issue set.
- `status_reporter/models.py` — retain selected detail records and omitted-detail count separately from full metric values, if needed for rendering.
- `status_reporter/rendering.py` — render no more than the selected limit overall, avoid duplicate issue details across sections, and disclose omitted detail count.
- `status_reporter/cli.py` and `status_reporter/email_delivery.py` — pass or consume the configured limit through a consistent report/rendering API.
- `tests/test_status_reporter.py` — add ordering, ties, global cap, and complete-metric assertions.
- `docs/weekly-status-report.md` — document the actual selection and truncation behavior.

**Acceptance criteria affected**

- Specification F5; acceptance A2.
- Task T10: priority ordering, detail limit, omitted count, and complete summary statistics.
- Task T13: bounded-listing and tie-break test coverage.

**Tests to add/update**

- Verify priority order Highest → High → Medium → Low, followed by earliest due date, oldest creation date, then lowest Jira key.
- Verify null due dates and equal sort keys have deterministic placement consistent with the approved policy.
- Use more than 100 eligible issues and assert no more than 100 distinct detailed issue listings appear.
- Assert all summary counts use all eligible issues, and the report states how many details were omitted.
- Verify the configured limit below 100 is honored and the validated maximum remains 100.

## Gap 5 — Support recipient-level partial email success

**Current gap:** The current sender treats SMTP refusal of any configured recipient as a delivery failure. The approved rule is to continue with remaining recipients and return “Success With Warnings” when some recipients fail.

**Files to modify**

- `status_reporter/email_delivery.py` — deliver/track recipient outcomes individually or otherwise ensure one refusal does not prevent attempts to remaining recipients.
- `status_reporter/models.py` — represent delivery outcome and accepted/failed recipient counts without storing addresses in audit metadata.
- `status_reporter/cli.py` — report `Success With Warnings` for partial delivery and preserve a failing exit for total delivery failure.
- `tests/test_status_reporter.py` — cover full, partial, and total rejection plus remaining-recipient attempts.
- `docs/weekly-status-report.md` — describe the success-with-warnings outcome and privacy-safe reporting.

**Acceptance criteria affected**

- Specification F7; acceptance A2 and A3.
- Task T11: per-recipient attempts and approved partial-delivery outcome.
- Task T12: accurate CLI status and exit code.
- Task T13: delivery decision test coverage.

**Tests to add/update**

- Full recipient success returns normal success.
- A mixed accepted/refused recipient result attempts all configured recipients and reports Success With Warnings without failing the run.
- Total rejection fails visibly with nonzero CLI exit.
- Error/log output follows the approved privacy decision: do not store recipient addresses in audit metadata; include counts and safe outcome information.
- Ensure retries do not resend to recipients whose acceptance is already known, avoiding duplicate delivery.

## Deferred work (not part of the five current real gaps)

The checklist classifies PostgreSQL persistence and the approved Docker/Node.js scheduler as deferred to later tasks. They should be planned and implemented under T11/T14/T15 rather than folded into this remediation scope:

- PostgreSQL execution/report/audit metadata persistence, access policy, 90-day retention, and failure behavior.
- Docker deployment and Node.js cron scheduling for Monday 09:00 Jira Project Timezone, missed-run recovery, and overlap prevention.
- Deployment-like tests for persistence, scheduler timezone/DST behavior, recovery, and concurrency.

## Completion gate

After the five gaps are implemented, run the focused tests for each area, then the complete test suite and fixture-backed dry run. Update `spec/checklist.md` only after confirming each claimed behavior against the implementation and tests. Keep live Jira, SMTP, database, and scheduler checks explicitly separate from offline test results.
