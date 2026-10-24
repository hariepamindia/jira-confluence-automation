# Python Calculator Project

This project contains a simple calculator implemented in Python.

## Files

- `calculator.py` contains the `add()` and `subtract()` functions.
- `main.py` uses these functions to perform calculations based on user input.

## How to run

```bash
python main.py
```

You will be prompted to enter two numbers, and the program will display their sum and difference.

## MCP server

The `.vscode/mcp.json` configuration starts `mcp-echo-server.ps1`, which forwards to `mcp-echo.ps1`. The server exposes three tools over stdio:

- `echo` returns a supplied message.
- `get_time` returns the current UTC time in ISO 8601 format.
- `calculate` supports `add`, `subtract`, `multiply`, and `divide` operations with numeric `a` and `b` arguments.

## Weekly Jira status report

The `status_reporter` Python package generates a leadership-ready weekly report from Jira. See [the setup and operations guide](docs/weekly-status-report.md) for configuration, metric definitions, scheduling, and troubleshooting.

```powershell
Copy-Item weekly-status.env.example weekly-status.env
# Edit weekly-status.env and supply secrets through environment variables.
python -m status_reporter --fixture tests/fixtures/weekly_issues.json --env-file weekly-status.env
python -m unittest discover -s tests -v
```

The default is a preview-only dry run. Use `--send` only when SMTP settings and recipients are configured and the report is ready to deliver.
