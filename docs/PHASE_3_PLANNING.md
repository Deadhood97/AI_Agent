# Phase 3 Planning Layer

Phase 3 starts the agentic path without making the app depend on an LLM for normal use.

## What Exists Now
- `contracts.planning.AnalysisPlan` is the planner output contract.
- `contracts.planning.PlanningResult` records the selected plan and planner attempts.
- `core.planning.deterministic_plan()` wraps the existing deterministic planner in the new contract.
- `core.planning.plan_question()` tries deterministic planning first.
- `core.llm_planner.llm_plan_question()` is an optional OpenAI structured-output planner.
- `DatasetTools.run_planned_turn()` stores the selected plan on the turn and writes a plan artifact.

## LLM Fallback
LLM planning is opt-in:

```powershell
.\.venv\Scripts\python.exe -m ui.cli_app path\to\data.csv --question "Which region has the highest revenue?" --allow-llm-planner
```

The flow is:

```text
deterministic planner fails
-> LLM planner returns AnalysisPlan
-> generated code is validated
-> DatasetTools executes the code through the safe executor
-> answer and plan are saved/traced
```

Live LLM planning requires:

```text
OPENAI_API_KEY=...
OPENAI_CODE_MODEL=...
```

The `openai` package is listed in `requirements-agent-frameworks.txt`.

## Why This Helps
The developer-user can inspect a turn and answer:
- what question was asked
- which planner handled it
- which columns, metrics, grouping, and filters were selected
- what code was generated
- why that plan was chosen
- what assumptions and limitations applied
- what execution result followed

## Current Shortcomings
- LLM planning is opt-in and not part of the default CLI path.
- There is no repair loop yet if LLM code fails validation.
- The deterministic planner still supports only row count, sums, means, and simple group counts.
- The LLM prompt is intentionally small and will need hardening with examples, RAG context, and evals.
- Plans are saved as JSON artifacts, but there is not yet a frontend to inspect them comfortably.

## Later Fixes
- Add a validation/repair loop for failed generated code.
- Add RAG context before LLM planning so the planner can use analyst knowledge.
- Add eval datasets for planner quality.
- Add a UI panel that shows the plan beside each answer.
- Add MCP only after the internal tool and plan contracts stabilize.
