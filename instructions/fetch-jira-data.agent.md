- Accept a JSON request with a Jira base URL, exactly one scope (`project_key`, `saved_filter_id`, or `jql`), reporting period (`start`, `end`, `timezone`), and an authentication environment-variable name.
  + Use ISO 8601 dates; define `start` as inclusive and `end` as exclusive.
  + Accept optional `fields`. If omitted, request `key`, `summary`, `issuetype`, `status`, `assignee`, `created`, `updated`, `resolutiondate`, `duedate`, `priority`, `labels`, and `components`.
  + Example: `{"jira_base_url":"https://jira.example.com","project_key":"OPS","start":"2026-10-05","end":"2026-10-12","timezone":"America/New_York","auth_env_var":"JIRA_TOKEN"}`
- Validate required values, URL format, scope exclusivity, date order, timezone, requested fields, and that the referenced authentication variable is configured before making requests.
- Use the Jira issue-search REST API supported by the configured Jira deployment; preserve supplied JQL and do not broaden or silently rewrite the requested scope.
- Apply the reporting-period boundaries in the configured timezone when constructing a query; include work completed during the period and relevant current work when the scope allows it.
- Request only the selected fields, use bounded request timeouts, and fetch every page until Jira indicates there are no more results.
- Normalize each issue without inferring missing values; deduplicate by issue key and retain the Jira-provided values.
- Return one JSON object with `source`, `issues`, and `pagination` properties.
  + `source` contains the resolved scope, effective JQL, reporting-period boundaries, timezone, and requested fields.
  + Each `issues` entry contains `key`, `url`, `summary`, `issue_type`, `status`, `status_category`, `assignee`, `created`, `updated`, `resolution_date`, `due_date`, `priority`, `labels`, and `components`.
  + Use `null` for unavailable scalar values and `[]` for unavailable or empty list values; retain Jira date-only due dates as dates and normalize timestamps to ISO 8601 with timezone information.
  + `pagination` contains `pages_fetched` and `issues_returned`.
- On request, authentication, rate-limit, pagination, or response-validation failure, stop and return `{"error":{"stage":"...","message":"..."}}` with safe Jira error details; never return partial data as a successful result.
- Never request credentials in chat, include credential values in the request or output, or log tokens, authorization headers, or other secrets.
- Do not fabricate issues, fields, owners, dates, or status mappings; preserve Jira values and report unavailable data as `null` or `[]`.
