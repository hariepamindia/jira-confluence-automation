# Implementation Plan

## Design

Use a dependency-free Python package and standard-library integrations. Keep configuration, Jira REST access, issue/report models, aggregation, rendering, SMTP delivery, and CLI orchestration in separate modules. Use environment variables for all deployment-specific settings and credentials. The report period defaults to the previous Monday through the current Monday in the configured timezone.

The Jira client uses configured JQL as the project/team scope, requests all report fields, and follows Jira pagination. The reporting layer derives period completions from resolution dates while retaining current open work and due items from the configured scope. Jira fix versions provide milestone progress when present; absent version data is called out rather than inferred.

The command supports fixture input for offline validation. By default, it prints the report and never sends mail. `--send` is required for SMTP delivery. Jira and SMTP failures are visible and cause a nonzero exit.

## Components

1. `status_reporter.config`: typed environment settings and validation.
2. `status_reporter.models`: normalized issue, milestone, and report records.
3. `status_reporter.jira`: Jira REST search, pagination, and bounded transient retries.
4. `status_reporter.reporting`: aggregation, risk rules, health classification, and recommendations.
5. `status_reporter.rendering`: plain-text stakeholder email and subject generation.
6. `status_reporter.email_delivery`: explicit SMTP delivery.
7. `status_reporter.cli`: date-window selection, fixture/live input, logging, dry-run, and send orchestration.

## Verification

- Run standard-library `unittest` tests for each component and failure path.
- Run the CLI end-to-end against a checked-in fictional fixture and inspect the rendered report.
- Confirm missing settings and failed delivery exit with errors, and that the default command cannot send email.
- No live integration run is performed without deployment credentials and an explicitly configured recipient list.
