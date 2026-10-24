# Task Analysis — Module 08 Weekly Stakeholder Status Reporting

**Reviewed:** [`tasks.md`](./tasks.md) against [`plan.md`](./plan.md), [`specification.md`](./specification.md), and the latest approved decisions in [`clarify.md`](./clarify.md).

Complexity estimates reflect implementation effort assuming the final decisions in `clarify.md` are authoritative. Task-level dependencies below distinguish the dependencies currently listed from sequencing improvements where appropriate.

## Per-task assessment

| Task | Complexity | Risks | Dependencies |
|---|---|---|---|
| **T01 — Resolve business and deployment decision gates** | High | The clarification now has owner approval, boundary examples, field validation policy, metric definitions, timezone, delivery behavior, audit policy, priority order, volume policy, scheduler mechanism, and performance procedure. However, the constitution and plan have not been updated to reflect prototype validation exceptions and the Docker/Node scheduler. Approval labels also say “Module 17 Prototype Review” rather than a verifiable date. These can create conflicting implementation authority. | None. |
| **T02 — Finalize secure application configuration** | Medium | Broad configuration surface across Jira, mail, PostgreSQL, audit, thresholds, and scheduler integration. Required fields include Assignee and Due Date, so null values are excluded; this can bias metrics. Recipient values are configured in environment variables but an allowlist/change approval mechanism is not specified. | T01. |
| **T03 — Implement Jira search, pagination, and retries** | High | Must retrieve an unbounded result set despite the 100-issue performance target; API quotas, timeouts, retry/backoff values, and behavior under very large project scope need limits. JQL must include open and period-resolved work while excluding canceled/duplicate records. A failed page must not yield complete-looking results. | T02. |
| **T04 — Normalize and validate Jira issues** | High | Missing or malformed required records are excluded and warned while the prototype run continues, overriding the constitution. The warning/error sanitization, log retention and issue-level diagnostics need care. Jira Resolution Date and status transitions/reopenings must match the approved latest-resolution-date rules. | T01, T02. |
| **T05 — Integrate complete Jira data collection** | Medium | Incorrect JQL or status/resolution filtering can omit issues while appearing successful. “Disallowed validation condition” must respect the approved prototype exception: invalid issue records are excluded with warnings, whereas incomplete page/API retrieval fails. | T03, T04. |
| **T06 — Calculate deterministic issue metrics** | High | The latest clarification resolves at-risk (today through seven calendar days; overdue separate), active denominator, thresholds, status precedence, and reopened completion behavior. Risks remain around distinct issue counting after normalization, interpretation of a report period boundary at fractional seconds, and applying prototype exclusions consistently to all metric denominators. | Listed: T01, T04. **Recommended addition:** T05 for production/integrated metric verification. |
| **T07 — Calculate health classification and rationale** | Medium | Latest examples settle Green through 10%, Yellow >10% through 20%, Red >20%, with zero active issues Green. Ensure classification uses exact ratios rather than rounded display percentages and excludes Completed from denominator while including unmapped statuses as Active. | T01, T06. |
| **T08 — Aggregate Jira Fix Version milestones** | Medium | Released milestones are complete, but the handling of a released version whose issues remain incomplete, missing release dates, and milestone progress rounding is not specified in the latest decision record. The field is optional, so reports without milestones need explicit treatment. | Listed: T01, T04. **Recommended addition:** T05 for validation against the full collection. |
| **T09 — Generate actionable recommendations** | Medium | Recommendations can overstate what Jira supports. The decision record defines category precedence but not a full recommendation catalogue or whether to name owners; use deterministic rules and do not infer ownership. | T06, T07, T08. |
| **T10 — Render the bounded plain-text report** | Medium | The latest clarification resolves 100 as maximum detailed entries while processing all matching issues, and supplies deterministic priority tie-breakers. Risks include maintaining summary metrics over all issues while selecting 100 details, sanitizing untrusted Jira text and email headers, and defining a report subject week reference. | T06, T07, T08, T09. |
| **T11 — Implement per-recipient email delivery and audit** | High | Continue after recipient refusals and return Success With Warnings; audit stores recipient count (not addresses), 90-day retention, and error summary. Ambiguous SMTP outcomes could cause duplicate sends. “Application log storage” plus PostgreSQL audit metadata requires clear separation, permissions and retention enforcement; audit-write failure must fail the run. | T01, T02, T10. |
| **T12 — Complete CLI orchestration and run outcomes** | Medium | Must reconcile process exits for partial email delivery (warning-success) versus fatal retrieval/render/audit failures, and enforce no-send default. It is unclear whether the Node scheduler invokes the Python CLI as a subprocess or how shared environment, exit codes and timezones are passed. | T02, T05, T10, T11. |
| **T13 — Add fixture and automated acceptance coverage** | High | This task spans nearly every subsystem and duplicates test obligations in T03–T12, creating a late integration bottleneck. Fixtures must reflect all latest approved examples and avoid logging sensitive data. | T03, T04, T06, T07, T08, T09, T10, T11, T12. |
| **T14 — Document setup, operation, and recovery** | Medium | Documentation can drift if delayed until all implementation completes. It must explain Docker plus the Node cron scheduler and Python reporting process, PostgreSQL responsibilities, app-log audit retention, partial success, and prototype-only validation behavior. | Listed: T01, T02, T06, T07, T08, T10, T11, T12. Can be delivered incrementally after T02 and finalized after T15. |
| **T15 — Configure and verify scheduled deployment** | High | Latest clarification selects a Docker scheduled task using a Node.js cron job, while the plan still describes Windows Task Scheduler. The scheduler-to-Python integration, authoritative timezone retrieval, persistence/restart behavior, and single-run lock across container restarts require design. | Listed: T01, T02, T12, T14. |
| **T16 — Verify performance, security, and release readiness** | High | The latest test procedure specifies Docker, PostgreSQL, reachable Jira, stable unthrottled network, 100 issues and under 60 seconds including email and database operations. Results may not generalize to production latency. This task combines independent performance/security verification with stakeholder approval and production release. | Listed: T01, T05, T13, T14, T15. |

## Dependency and sequencing review

- **T06 and T08 lack T05 as a listed dependency.** Their unit logic can be developed from T04 normalized records, but production acceptance over the complete paginated population should depend on T05.
- **Testing is duplicated and sequenced late.** T03–T12 already require component tests, while T13 depends on nearly all implementation. Keep unit/integration tests within their implementation tasks and narrow T13 to end-to-end fixture, cross-component regression and acceptance coverage.
- **T14 is over-dependent for initial documentation.** Setup/configuration documentation can start after T02; later sections should be updated alongside metrics, mail/audit, and scheduler work. Reserve final review for after integration.
- **T16 combines separate work.** Performance/security test evidence can be gathered before scheduler deployment; production activation and stakeholder authorization should remain a separate release gate.
- **T12 and T15 have an implicit runtime dependency.** Clarify whether the Node cron process launches the Python report command, whether both share a container or communicate over an interface, and how failures/locks/timezone values propagate.
- **T01 decision resolution is approved in the clarification, but task artifacts are stale.** The plan still describes unresolved gates and Windows Task Scheduler, and the task descriptions include conditional language (“as agreed”) despite final decisions. Update them before using the task list as the sole implementation authority.

## Gaps

- **JQL contract/artifact:** T03/T05 mention query scope but do not define the exact query or provide a reviewed query artifact that includes current unresolved work and issues resolved in the reporting period while excluding Cancelled and Duplicate.
- **Project timezone interface:** Timezone is decided, but no artifact identifies how the Jira Project Timezone is retrieved/configured and what happens if it is unavailable or changes.
- **Reporting period precision:** The approved interval ends Sunday at 23:59:59. Jira timestamps may have fractional seconds after that instant. Specify whether the implementation uses an exclusive next-Monday boundary to include all Sunday events.
- **Fix Version edge cases:** Resolve release-versus-issue completion precedence, missing target dates, and progress rounding; the original spec calls for milestone status as well as percentage.
- **Audit implementation details:** PostgreSQL stores audit metadata, while audit logs remain in application logs. Define which store is authoritative, how the 90-day deletion is enforced in both, how Project Administrator-only access is enforced, and whether error summaries are redacted.
- **Node/Python deployment contract:** A Node.js cron scheduler is selected while the implementation is Python. No task owns the execution interface, packaging topology, health checks, or restart/lock semantics across both processes.
- **Unmapped Jira statuses:** They are treated as Active and logged, but no limit/alert behavior is defined if a large share of the project is unmapped.
- **Recipient control:** Environment-variable recipients are specified, but approval/allowlisting and change control to prevent accidental external delivery are not assigned to a task.
- **Operational alerting:** The Project Administrator is named as owner, but the actual notification channel and escalation procedure for missed/failed reports are not specified.
- **Reproducible dependency/build artifact:** The plan mentions dependency control, but tasks do not explicitly require pinned Python/Node dependencies, lockfiles, image provenance, or repeatable Docker builds.
- **Report artifact:** Stakeholder preview is required, but there is no named golden/sample report artifact with expected output for sign-off.

## Contradictions and inconsistencies

1. **Constitution versus approved prototype exception:** `clarify.md` explicitly overrides the constitution's fail-on-incomplete-data behavior for the prototype. The constitution file itself has not been amended or given an exception, leaving two active sources of authority. T04/T05/T12 must follow one documented rule.
2. **Plan versus approved deployment scheduler:** `plan.md` specifies an external scheduler and Windows Task Scheduler example; the final clarification specifies a Node.js cron scheduled job in Docker. Align the plan and T15 before implementation.
3. **Plan architecture versus actual stack:** The plan describes a Python package, while scheduling is Node.js and PostgreSQL is required for execution metadata. The boundary and launch interface are absent.
4. **Audit storage wording:** Earlier decisions say audit storage is application logs; later decisions add PostgreSQL audit metadata and retain audit logs in application logs. This can be consistent, but the division of responsibilities and authoritative audit record is not stated.
5. **Unbounded retrieval versus performance scope:** Clarification requires processing all matching issues and pagination, but the performance acceptance covers only 100 issues. There is no upper bound or behavior for workloads above that.
6. **Prototype continuation versus successful run definition:** Invalid issue records are excluded with warnings and processing continues; successful-run conditions require Jira retrieval/report/email success. State explicitly whether validation warnings yield normal success or Success With Warnings.

## Missing artifacts

- Updated `plan.md` aligned to approved business rules, Docker/Node cron deployment, PostgreSQL metadata and Python execution.
- Updated `constitution.md` or a clearly scoped, approved prototype exception that reconciles its incomplete-data failure principle.
- Jira project/JQL and field/status mapping artifact, including timezone discovery/configuration and canceled/duplicate filters.
- Node scheduler-to-Python execution contract and Docker deployment topology/lock mechanism.
- PostgreSQL schema/migration for execution/report/audit metadata and an application-log retention/access configuration for 90-day audit events.
- Sanitized fixture matrix and golden plain-text report covering boundary examples, partial recipient delivery, unmapped statuses, and >100 issues.
- Python and Node dependency lockfiles plus reproducible Docker build instructions.
- Operations runbook covering notification channel, missed/failed runs, overlap, credential rotation, audit access/retention, and recovery.

## Risk flags

- **HIGH — Conflicting source of truth:** Prototype validation exception is approved in `clarify.md` but not reflected in the constitution or plan.
- **HIGH — Runtime integration:** Python report application plus Node cron scheduler in Docker lacks an explicit process boundary and failure/lock contract.
- **HIGH — Report completeness:** Unlimited retrieval is required but performance is only measured at 100 issues; large projects can exceed the service window.
- **HIGH — Data quality bias:** Requiring Assignee and Due Date excludes valid unassigned/undated Jira issues, potentially skewing total/open/milestone metrics. The exclusion is approved, but its impact should be visible in report diagnostics.
- **HIGH — Audit/privacy:** Recipient count is stored instead of addresses, reducing exposure, but log error summaries and app-log access/retention controls still need implementation evidence.
- **HIGH — Delivery semantics:** Partial delivery is Success With Warnings; ambiguous SMTP outcomes and retries can still duplicate stakeholder reports.
- **MEDIUM — Time boundaries:** End-at-23:59:59 may omit fractional-second Jira updates on Sunday.
- **MEDIUM — Unknown workflow statuses:** Mapping them to Active prevents exclusion but can conceal workflow drift without an alert threshold.
- **MEDIUM — Operational recovery:** “Run on next startup” depends on the Docker scheduler actually starting and persisting run state; restart and outage cases need tests.
- **MEDIUM — Audit failure:** PostgreSQL and application logs can diverge; partial writes may leave an incomplete audit trail unless transaction/consistency behavior is designed.

## Recommended adjustments

1. Reconcile the prototype exception in the constitution and update `plan.md` and T04/T05/T12 to use the same rule.
2. Add T05 as a production integration dependency for T06 and T08.
3. Add an explicit task or subtask for the Node scheduler/Python CLI execution contract, Docker topology, and cross-restart overlap/missed-run behavior.
4. Add concrete deliverables for JQL/field/timezone mapping, PostgreSQL schema, log retention/access, pinned dependencies, and a golden report fixture.
5. Clarify Sunday timestamp inclusivity, issue validation warning run status, and how processing beyond 100 issues meets the stated performance target.
6. Move component tests into their implementation tasks; narrow T13 and separate technical verification from production activation in T16.
