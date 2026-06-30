# AI Analyst Learning Labs

This project is a hands-on lab for learning AI application frameworks. Codex can scaffold, review, debug, and quiz, but framework fluency comes from you running commands, inspecting platform output, and explaining what happened.

## Start Here

First active lab:

- `Lab 00: Project Map`

First files to inspect:

- `README.md`
- `ui/cli_app.py`
- `core/dataset_tools.py`
- `contracts/turn.py`
- `tests/test_foundation.py`

The goal is to understand the current project before adding more frameworks. LangSmith, LangChain, LangGraph, and MCP will make more sense once the existing deterministic analyst pipeline is clear.

## Lab Rhythm

Each lab should fit in 30-60 minutes:

1. Read the objective and concept notes.
2. Run or edit the assigned code yourself.
3. Verify with the command listed in the lab.
4. Answer the quiz in your own words.
5. Add a short `JOURNAL.md` entry with what you learned, what confused you, and what you verified.

## Quiz Workflow

Submit quiz answers directly in the chatbox, using this shape:

```text
Lab 00 quiz answers:

1. ...
2. ...
3. ...
```

Codex will review each answer as:

- `correct`
- `partially correct`
- `needs review`

Missed answers become small mini-exercises before moving to the next lab. After review, add the quiz result to `JOURNAL.md`.

Good answers do not need perfect vocabulary; they need the right mental model.

## Codex Handholding Rules

- Codex explains first, then asks you to run or edit.
- Your edits should be small: config values, one line, one function call, one test expectation, or one prompt sentence.
- Codex can scaffold larger code after explaining what it does.
- Codex reviews quiz answers and helps update `JOURNAL.md`.
- No new framework step should start until the previous concept is understood.
- If something breaks, debugging is part of the lab, not a failure.

## Lab 00: Project Map

Objective:

- Learn where the main parts of the project live and what each folder owns.

Concept Notes:

- `core/` owns deterministic backend behavior.
- `contracts/` owns Pydantic schemas for handoffs between parts of the app.
- `ui/` owns entry points users interact with, such as the CLI or future chat UI.
- `tests/` proves behavior stays stable.
- `artifacts/` stores generated datasets, metadata, sessions, turns, outputs, memory, and traces.
- `docs/` stores the learning path and project explanation.
- `evals/` stores evaluation scripts that test the app like a product.

Hands-On Task:

1. Open `README.md` and identify the project goal.
2. Open `ui/cli_app.py` and find where the CSV path and question enter the app.
3. Open `core/dataset_tools.py` and find `run_planned_turn`.
4. Open `contracts/turn.py` and find `ConversationTurn`.
5. Open `tests/test_foundation.py` and find one test that runs the analyst pipeline.

Verification:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Quiz:

1. Which folder owns deterministic backend behavior?
2. Which folder owns Pydantic handoff schemas?
3. Which file is the CLI entry point?
4. Which module runs the planned analysis turn?
5. Why do we keep UI separate from `core`?

Journal Prompt:

```text
### Lab 00: Project Map

Files inspected:

What I think happens when the CLI receives a CSV and a question:

Quiz answers:

Quiz review:

What confused me:
```

## Lab 00.5: Python Survival For This Project

Objective:

- Learn only the Python needed to read and safely edit this project.

Concept Notes:

- A function receives inputs, does work, and may return an output.
- A class groups data or behavior under a named object.
- A dictionary stores named values, like `{"status": "succeeded"}`.
- A list stores ordered values, like `["region", "revenue"]`.
- An import pulls code from another file or package.
- Type hints describe expected shapes; they are signposts for humans and tools.

Hands-On Task:

1. Open `ui/cli_app.py`.
2. Find `main`.
3. Identify three inputs it reads.
4. Identify what it prints.
5. Identify what integer it returns on success.

Verification:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Quiz:

1. What is a function argument?
2. What does `return 0` usually mean in a CLI app?
3. What does `from core import ArtifactStore, DatasetTools` do?
4. What is one dictionary you saw in the code or tests?
5. Why are type hints useful when you are reading unfamiliar code?

Journal Prompt:

```text
### Lab 00.5: Python Survival For This Project

Function inspected:

Inputs I found:

Outputs I found:

Quiz answers:

Quiz review:

What confused me:
```

## Lab 00.6: Tests, Contracts, And Artifacts

Objective:

- Learn how this project proves behavior, validates handoffs, and saves audit trails.

Concept Notes:

- A test checks that a behavior still works.
- A contract defines the shape of data passed between parts of the app.
- An artifact is saved evidence of what happened.
- In analyst terms: tests are QA checks, contracts are agreed templates, and artifacts are audit files.

Hands-On Task:

1. Run the test suite.
2. Open `contracts/turn.py` and inspect `ConversationTurn`.
3. Open `tests/test_foundation.py` and find a test that creates a turn.
4. Open `core/artifacts.py` and find how JSON artifacts are written.

Verification:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Quiz:

1. What is the difference between a test and a contract?
2. Why should every assistant answer become a turn artifact?
3. What does Pydantic validation protect us from?
4. Why are artifacts useful when an answer is wrong?
5. Which artifact would you inspect to debug a failed generated-code run?

Journal Prompt:

```text
### Lab 00.6: Tests, Contracts, And Artifacts

Test command result:

Contract inspected:

Artifact behavior inspected:

Quiz answers:

Quiz review:

What confused me:
```

## Lab 00.7: Deterministic Analyst Pipeline

Objective:

- Understand the current non-LLM analyst path before adding model intelligence.

Concept Notes:

- The current pipeline is deterministic for simple questions.
- The model should not invent calculations; calculations should come from code or trusted tools.
- The current flow is: CSV ingest -> metadata -> simple planner -> safe pandas execution -> formatted answer -> artifacts/traces.

Hands-On Task:

1. Create or choose a tiny CSV with `region` and `revenue` columns.
2. Run the CLI smoke command:

```powershell
.\.venv\Scripts\python.exe -m ui.cli_app path\to\data.csv --question "What is the total revenue?"
```

3. Trace the code path from `ui/cli_app.py` into `DatasetTools.run_planned_turn`.
4. Find where the final answer is printed.

Verification:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Quiz:

1. What are the steps in the deterministic pipeline?
2. Why should revenue totals come from pandas code instead of model text?
3. What does the simple planner produce?
4. What does safe execution protect against?
5. Where is the assistant answer formatted?

Journal Prompt:

```text
### Lab 00.7: Deterministic Analyst Pipeline

CLI command I ran:

CLI output:

Pipeline steps in my own words:

Quiz answers:

Quiz review:

What confused me:
```

## Lab 01: LangSmith Tracing Smoke

Objective:

- Learn how a local app run becomes a LangSmith trace with nested spans.

Concept Notes:

- A trace is the full recorded run.
- A span is one step inside that run, such as ingest, plan, execute, or answer.
- `LANGSMITH_TRACING=true` enables tracing.
- `LANGSMITH_PROJECT` controls where traces appear in the LangSmith UI.
- This project sends preview rows, metadata summaries, IDs, statuses, and output summaries, but not full datasets.

Hands-On Task:

1. Install tracing dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-tracing.txt
```

2. Copy `.env.example` values into `.env` and set:

```text
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_real_key
LANGSMITH_PROJECT=ai-analyst-dev
```

3. Run the CLI smoke command with a small CSV.
4. Open LangSmith and inspect the trace tree.

Verification:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Quiz:

1. What is the difference between a trace and a span?
2. Which environment variable chooses the LangSmith project?
3. Why do we keep full CSV contents out of LangSmith?
4. Which span tells you whether generated code execution succeeded?
5. What would you inspect first in LangSmith if the answer was wrong?

Journal Prompt:

```text
### Lab 01: LangSmith Tracing Smoke

What I ran:

What I saw in LangSmith:

Quiz answers:

What confused me:

What I want to inspect next:
```

## Lab 02: LangSmith Evaluation Smoke

Objective:

- Learn how LangSmith datasets, target functions, evaluators, and experiments fit together.

Concept Notes:

- A dataset stores test examples.
- A target function is the app behavior being tested.
- An evaluator scores the target output against expectations.
- An experiment is one evaluation run over a dataset.

Hands-On Task:

1. Run the evaluation script:

```powershell
.\.venv\Scripts\python.exe -m evals.langsmith_smoke
```

2. Follow the printed LangSmith experiment link.
3. Inspect each example row and evaluator score.

Verification:

- The `ai-analyst-smoke` dataset exists in LangSmith.
- The experiment has examples for row count, total revenue, average revenue, and count by region.

Quiz:

1. What is the difference between a dataset and an experiment?
2. What does the target function do in this project?
3. Why do we use deterministic evaluators before LLM-as-judge evaluators?
4. Which example would fail if the planner could not identify a numeric column?
5. What is one new test case you would add to the LangSmith dataset?

Journal Prompt:

```text
### Lab 02: LangSmith Evaluation Smoke

Dataset inspected:

Experiment inspected:

Quiz answers:

One failure mode I noticed:

One new eval example I would add:
```

## Lab 03: LangChain Structured-Output Planner

Objective:

- Learn how a natural-language question can become a validated planning object.

Concept Notes:

- Structured outputs turn model text into a schema-validated object.
- The app should still validate the planner result before trusting it.
- This lab should preserve the current deterministic planner as a fallback.

Hands-On Task:

1. Install agent framework dependencies when this lab starts:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-agent-frameworks.txt
```

2. Add a LangChain planner that returns a `ResolvedIntent`.
3. Compare its output against the deterministic planner for simple questions.

Verification:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Quiz:

1. Why is structured output safer than parsing free-form model text?
2. What should happen if the model returns an invalid `ResolvedIntent`?
3. Why keep the deterministic planner as a fallback?
4. Which fields in `ResolvedIntent` matter most for follow-up questions?
5. What would you trace in LangSmith for a planner span?

## Lab 04: LangChain Dataset Tools

Objective:

- Learn how app functions become model-callable tools.

Concept Notes:

- A tool has a name, description, input schema, and implementation.
- Good tool descriptions help the model choose the right tool.
- Tool output should be compact and structured.

Hands-On Task:

1. Wrap dataset preview, metadata lookup, and safe execution as LangChain tools.
2. Run a small tool-calling example against the current sample CSV.
3. Inspect tool call inputs and outputs in LangSmith.

Verification:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Quiz:

1. What makes a good tool description?
2. Why should tool outputs be compact?
3. What is the difference between a tool schema and a tool implementation?
4. Which dataset tool is riskiest, and why?
5. What should the model never be allowed to decide about safe execution?

## Lab 05: LangGraph Turn Graph

Objective:

- Learn how a turn can be represented as explicit graph state.

Concept Notes:

- LangGraph represents workflows as nodes and edges over shared state.
- A node does one job, such as plan, execute, or answer.
- State makes debugging easier because each step has a clear input/output.

Hands-On Task:

1. Build a graph with `plan -> execute -> answer`.
2. Run one successful analytical question through the graph.
3. Compare the LangSmith trace tree with the direct `DatasetTools` trace tree.

Verification:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Quiz:

1. What is graph state?
2. What is the difference between a node and an edge?
3. Why is a graph easier to debug than one large function?
4. Which node should own generated-code validation?
5. What would need to change to support follow-up questions?

## Lab 06: LangGraph Repair Branch

Objective:

- Learn how graph branching handles failed execution.

Concept Notes:

- A conditional edge chooses the next node based on state.
- Repair should be bounded; it is resilience, not an infinite retry loop.
- Failed turns should still produce useful artifacts and traces.

Hands-On Task:

1. Add an execution-failed branch.
2. Add one repair attempt.
3. Record both the original failure and repaired outcome in artifacts and LangSmith.

Verification:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Quiz:

1. What condition should trigger the repair branch?
2. Why should repair attempts be limited?
3. What information should the repair node receive?
4. What should happen if repair also fails?
5. How would you identify repair behavior in LangSmith?

## Lab 07: Trace Comparison

Objective:

- Learn to compare direct, LangChain, and LangGraph implementations in LangSmith.

Concept Notes:

- Traces are not just logs; they are debugging and evaluation artifacts.
- A good trace helps answer what happened, where time went, and where wrong data entered.
- Comparable traces make framework tradeoffs visible.

Hands-On Task:

1. Run the same question through direct `DatasetTools`.
2. Run it through the LangChain pipeline.
3. Run it through the LangGraph pipeline.
4. Compare trace depth, readability, payloads, and failure visibility.

Verification:

- Three traces exist in the same LangSmith project for the same question.
- Your journal explains which implementation was easiest to debug and why.

Quiz:

1. Which trace was easiest to understand?
2. Which trace exposed the most useful intermediate state?
3. Which implementation had the most moving parts?
4. What payload would you remove for privacy?
5. What payload would you add for debugging?
