- Accept a JSON input containing `project`, `reporting_period`, and verified project data.
  + `project` contains `name` and optional `team`, `prepared_by`, and `stakeholders`.
  + `reporting_period` contains ISO 8601 `start` and `end` dates, optional `timezone`, and `report_date`.
  + `data` contains available Jira issues, milestones, risks, decisions, and team-defined status mappings or health thresholds. Jira issues may use the output schema from `./instructions/fetch-jira-data.agent.md`.
  + Example: `{"project":{"name":"Operations","team":"Platform","prepared_by":"Team"},"reporting_period":{"start":"2026-10-05","end":"2026-10-11","timezone":"UTC","report_date":"2026-10-12"},"data":{"issues":[],"milestones":[],"risks":[],"decisions":[]}}`
- Validate that project identity, reporting dates, and source data are present; flag missing or inconsistent information explicitly instead of filling gaps with assumptions.
- Review and reconcile the supplied data before drafting.
  + Count each issue once per metric and use the team's status mappings when provided.
  + Count work as completed during the period only when completion evidence or a resolution date supports it; a recent update alone is not proof of completion.
  + Include relevant current open work, blockers, risks, overdue or due-soon work, and active milestones.
- Assess project health as Green, Yellow, or Red using team-defined thresholds when available; otherwise use the guidance in `./reports/instructions.md` and explain the evidence briefly.
- Summarize outcomes and stakeholder impact rather than listing routine activity or dumping raw Jira tickets.
- Produce a stakeholder-ready Markdown report in this order: project/reporting metadata, Project Health, Summary, Highlights, Risks and Blockers, Milestones, Next Period: Planned Actions, and Decisions or Support Needed.
  + Use concise bullets for narrative sections and Markdown tables for risks/blockers, milestones, and planned actions, following `./reports/template.md`.
  + Include counts and concise context for completed, in-progress, blocked, at-risk, and due-soon or overdue work when supported by the input.
  + For each material risk or blocker, include impact, owner when known, mitigation or next step, and target date when known.
  + For actions, include a specific verifiable next step, owner when known, and due date when known.
- If no risks, blockers, milestones, actions, or decisions exist, state `None` only when the provided data confirms that; otherwise identify the information as unavailable or not provided.
- Use only supplied facts; do not invent issue details, owners, dates, decisions, milestones, impact, status mappings, or health evidence.
- Do not expose credentials, confidential personal information, or details the intended stakeholders are not authorized to receive.
- Keep wording professional, factual, concise, and free of filler; remove unresolved template placeholders before returning the report.
