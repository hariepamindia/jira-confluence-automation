# Implementation Checklist — Specification Comparison

**Source:** [`specification.md`](./specification.md)  
**Implementation reviewed:** current `status_reporter` package, environment example, tests, and operations guide.  
**Latest verification:** 2026-10-24 — `python -m unittest discover -s tests -v` — **55 tests passed**; `python -m compileall -q status_reporter tests` and `git diff --check` also passed.

## Status meanings

- **Implemented and tested** — implementation exists and relevant offline tests pass.
- **Partially implemented** — behavior exists but is incomplete or not verified against a live service.
- **Out of scope / superseded** — external to the application or superseded by a later approved clarification.

Tests rely on fixtures and mocks. They do not demonstrate live Jira, SMTP, PostgreSQL, or scheduler operation.

## Functional requirements

| ID | Requirement | Status | Assessment |
|---|---|---|---|
| F1 | Read Jira scope and credentials, report timezone, status/risk rules, and mail settings from environment configuration. | **Implemented and tested** | `Settings.from_env` reads and validates configuration in [`config.py`](../status_reporter/config.py). The example configuration contains placeholders. Tests cover required settings, invalid values, timezone, recipients, TLS, and secret-safe errors. Runtime use with real credentials is not verified. |
| F2 | Retrieve configured Jira issues with required fields and pagination; normalize optional and missing values without dropping otherwise valid issues. | **Implemented and tested** | [`fetch_issues`](../status_reporter/jira.py) preserves JQL, requests report fields, validates pagination, fetches every page, and deduplicates. [`normalize_issues`](../status_reporter/jira.py) excludes malformed individual records with sanitized warnings and continues processing valid records. Missing required assignee/due date is excluded; optional timestamps may be absent. Page-level failures remain fail-closed. Live Jira behavior is unverified. |
| F3 | Calculate open, completed-in-period, in-progress, blocked, at-risk, overdue, and due-soon metrics, plus milestone progress where Jira supplies fix-version data. | **Implemented and tested** | [`build_report`](../status_reporter/reporting.py) excludes canceled and duplicate-resolution issues, deduplicates keys, applies the approved status mapping/precedence, uses Jira resolution dates for completions, treats reopened issues as active, derives date-based risk, calculates overdue and milestone metrics, and orders/caps details. Boundary and exclusion behavior is covered by offline tests. |
| F4 | Classify health as Green, Yellow, or Red using configurable thresholds and include reasons. | **Implemented and tested** | Health uses the overdue percentage over the active denominator, excluding completed issues; zero active issues is Green. Configured threshold boundaries and reason text are covered by offline tests. |
| F5 | Render concise email with health, period, highlights, risks/blockers, milestones, upcoming actions, recommendations, and project/week subject. | **Implemented and tested** | [`render_report`](../status_reporter/rendering.py) renders the required sections. Detail selection is deterministic and capped at the configured maximum of 100 across the report, with no duplicate issue lines and an omitted-count notice. Jira-derived text is sanitized. Rendering is tested offline. |
| F6 | Support fixture input and non-sending dry run; send only after explicit operator opt-in. | **Implemented and tested** | [`cli.py`](../status_reporter/cli.py) supports `--fixture`; sending requires `--send`. Fixture dry-run tests pass without network access. |
| F7 | Return a failing status and clear error on invalid required configuration or failed Jira/email operations. | **Implemented and tested** | The CLI returns a failure for invalid configuration, Jira page/fetch failures, ambiguous transport failures, and total recipient rejection. Per-recipient refusals continue to other recipients; partial acceptance returns “Success With Warnings” and exits successfully. Mocked/offline tests cover these paths; live delivery is unverified. |

## Safety and operational constraints

| ID | Constraint | Status | Assessment |
|---|---|---|---|
| S1 | No credentials in source, committed examples, report output, or logs. | **Implemented and tested** | The example uses placeholders; configuration tests verify secrets are not echoed. Recipient addresses are not included in delivery outcome logs. No live log review was performed. |
| S2 | No Jira writes; only issue search requests are permitted. | **Implemented and tested** | The adapter makes Jira search requests only. Tests inspect the request path and headers. |
| S3 | Jira retries are bounded and limited to transient failures. | **Implemented and tested** | Retry attempts and delays are capped/configurable. Tests cover transient network/rate-limit retries, permanent HTTP failures, TLS failures, and retry exhaustion. |
| S4 | Scheduler deployment is external; document a Windows Task Scheduler example and configured timezone. | **Out of scope / superseded** | Later approved clarification selects Docker with a Node.js cron job, Monday 09:00 in Jira Project Timezone, missed-run recovery, and overlap protection. The operations guide documents that target; scheduler implementation remains external and deferred. |

## Acceptance checks

| ID | Acceptance check | Status | Assessment |
|---|---|---|---|
| A1 | Fixture-backed command creates a readable report without network access. | **Implemented and tested** | CLI fixture dry-run test passes; sample data is in [`weekly_issues.json`](../tests/fixtures/weekly_issues.json). |
| A2 | Tests verify normalization, metrics/thresholds, milestones, report sections, config, pagination/retries, and delivery failure. | **Implemented and tested** | The latest 55-test offline suite covers the approved validation/exclusion rules, status and health boundaries, detail order/cap, rendering, pagination/retries, and per-recipient partial delivery, including retry and continuation after `SMTPRecipientsRefused`. |
| A3 | Live Jira/SMTP are available only when configured; email requires explicit send option. | **Partially implemented** | Required live settings and `--send` gating are implemented and tested. Actual Jira/SMTP service operation remains unverified because no live integration test was run. |

## Verified test run

```text
Command: python -m unittest discover -s tests -v
Run:     2026-10-24
Result:  Ran 55 tests
Status:  OK

Command: python -m compileall -q status_reporter tests
Status:  OK

Command: git diff --check
Status:  OK
```

These checks verify the offline tests and code compilation, not live service connectivity or production deployment readiness.

## Remaining gaps and verification limits

- Live Jira and SMTP connectivity, credentials, and production permissions have not been exercised.
- PostgreSQL persistence and the approved Docker/Node.js scheduler are deferred to their respective tasks.

The five in-scope remediation gaps identified in the earlier checklist have been implemented and covered by offline tests.