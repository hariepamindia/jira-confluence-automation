# Project Constitution

## Principles

1. **Requirements lead implementation.** Preserve the user-visible outcomes and acceptance criteria in `project_spec.md`; record any operational assumptions in project documentation.
2. **Protect credentials and stakeholder data.** Read secrets from the environment or an approved secret store. Never commit credentials or write them to logs, previews, or generated reports.
3. **Fail visibly and safely.** Invalid configuration, incomplete required Jira data, integration failures, and rejected email delivery must produce actionable errors and a failing process exit; never report a failed run as successful.
4. **Make the report explainable.** Derive metrics from normalized issue data, define classification rules, identify missing milestone data, and include concise reasons for health assessments.
5. **Keep integrations replaceable and testable.** Separate configuration, Jira access, aggregation, rendering, delivery, and command orchestration. Test behavior without live Jira or email credentials.
6. **Default to non-destructive operations.** A normal run may retrieve and render a report but must not send email unless the operator explicitly opts in.

## Quality Gates

- Automated tests cover normalization, reporting rules, rendering, and failure behavior.
- A dry run using fixture data exercises the complete report path without network access or email delivery.
- Documentation explains configuration, metric assumptions, manual execution, scheduling, and recovery.
