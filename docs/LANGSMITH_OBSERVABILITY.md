# LangSmith Observability

Phase 2 traces the starter analyst workflow from CSV upload through suggested questions and optional answer execution.

## Setup
Install the optional dependency:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-tracing.txt
```

Copy `.env.example` to `.env` if needed, then set:

```text
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_key_here
LANGSMITH_PROJECT=ai-analyst-dev
```

Leave `LANGSMITH_ENDPOINT` empty unless your LangSmith workspace uses a regional or self-hosted endpoint.

## Run A Trace
Suggestions-only workflow:

```powershell
.\.venv\Scripts\python.exe -m ui.cli_app path\to\data.csv
```

Suggestions plus a user question:

```powershell
.\.venv\Scripts\python.exe -m ui.cli_app path\to\data.csv --question "What is the total revenue?"
```

## What To View In LangSmith
Open LangSmith, select the project named by `LANGSMITH_PROJECT`, then inspect the latest run named:

```text
CLI dataset analyst workflow
```

Useful child runs:
- `DatasetTools.ingest_csv_bytes` - CSV parser, dataset id, compact metadata, initial suggestions, local trace events.
- `DatasetTools.suggest_questions_for_session` - the top suggested questions shown to the user.
- `DatasetTools.run_planned_turn` - the user question and deterministic planner output.
- `plan_simple_question` - resolved intent, rationale, and generated code summary.
- `execute_dataframe_code` - code summary, selected output key, and compact output summary.
- `format_analysis_answer` - final answer text.

## Payload Policy
Traces should show enough to debug behavior without leaking or bloating data:
- include compact metadata, not full datasets
- include suggested questions and rationales
- include code summaries, not full code by default
- include output summaries, not full table rows
- include local trace event summaries without internal trace ids
