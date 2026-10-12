# How to Complete the Weekly Status Report

Use [template.md](template.md) once per project each week. Base the report on the same reporting period and agreed Jira project, board, or saved filter every time. Follow any team-specific definitions for health status and risk; if none exist, use the guidance below and state the reason for your assessment.

## 1. Set the reporting period

- Enter the start and end dates covered by the update, and the date the report is prepared.
- Use the same weekly boundary each time. Include the time zone if dates or deadlines could be ambiguous.
- Include work completed during the period and current open work as of the report date. Do not treat an issue's recent update alone as evidence that it was completed.

## 2. Gather and verify Jira data

- Use the project, board, or JQL filter agreed by the team. Check that it covers current work, recently completed work, active milestones, and important open risks.
- Verify issue keys, statuses, owners, due dates, and milestone dates against Jira before reporting them.
- Count each issue once in a metric. Use the team's Jira workflow to decide which statuses count as complete, in progress, or blocked.
- If a field is missing or the Jira data is unclear, say so instead of guessing. Identify the source or assumption when it affects the report.

## 3. Assess project health

Choose one status and explain it briefly:

- **Green:** expected outcomes and milestones are on track, with no material unresolved blockers.
- **Yellow:** a meaningful risk, dependency, or schedule variance needs attention, but recovery is plausible with identified actions.
- **Red:** a critical blocker or significant delivery impact makes a key outcome or milestone unlikely without intervention.

Use the team's configured thresholds when available. Health is a project-level assessment, not an average of issue statuses. Do not mark a project Green solely because issues are moving or no blocker label is present.

## 4. Fill in each section

- **Summary:** Give concise counts and important context. Make clear what “completed,” “blocked,” and “at risk” mean if those categories might be interpreted differently.
- **Highlights:** Report outcomes achieved in the period and their stakeholder impact. Link or name Jira issues where useful; avoid a raw ticket dump.
- **Risks and Blockers:** Describe the impact, accountable owner, concrete mitigation or next step, and target date. Include material dependencies and overdue work. Write “None” only after checking.
- **Milestones:** Use the latest target date and explain any change. Choose a status that reflects forecast and evidence, not just percentage complete.
- **Planned Actions:** List specific actions for the next reporting period, with an owner and due date. Prefer actions that address the stated risks.
- **Decisions or Support Needed:** State the requested decision or help, the person or group needed, and the date by which it is needed. Write “None” when no support is required.

## 5. Review before sending

- Check that dates, counts, owners, and status descriptions agree with Jira and with one another.
- Ensure every Yellow or Red assessment has an explanation and next step.
- Keep the update concise and readable for leadership; surface exceptions and requests rather than listing routine activity.
- Remove unresolved placeholders and confirm that the recipient list and project scope are correct.
- Do not include credentials, confidential personal information, or details the recipients are not authorized to receive.
