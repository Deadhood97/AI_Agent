# Conversational Dataset Analyst

## 1. Project Overview

Conversational Dataset Analyst is Project 02 in the AI analytics learning track. It is a clean fork and evolution of Dashboard Studio, the earlier project located at:

```text
C:\Users\Lord Vader\Documents\AI dashboaring
```

Dashboard Studio focused on this workflow:

```text
Upload dataset -> generate dashboard automatically
```

This project changes the center of gravity:

```text
Upload dataset -> chat iteratively with an AI analyst
```

Instead of immediately producing a fixed dashboard, the system should behave like a data analyst who has studied the uploaded CSV and can hold an ongoing conversation about it. The user should be able to ask questions, request charts, refine filters, compare against previous answers, ask why a pattern exists, and inspect the calculations behind each answer.

The important learning goal is not only to make a useful app. The goal is to understand how conversational AI systems manage dataset context, memory, tools, generated code, artifacts, and trust over multiple turns.

## 2. Product Promise

Given a CSV dataset, the assistant should help answer:

- What is in this dataset?
- What do the important columns appear to represent?
- What questions can this data answer?
- What code or computation is needed for a user question?
- What did the system calculate?
- Which results are computed facts versus inferred interpretation?
- What previous result, chart, or filter is the user referring to?
- What assumptions or limitations should be visible?
- Can this analysis be reviewed or reused later?

The assistant should feel conversational, but it must stay grounded. It should not invent numbers. It should inspect metadata, call tools, run safe code, and answer from computed outputs.

## 3. Project Lineage And Reuse Strategy

Dashboard Studio already solved several hard backend problems that should not be rediscovered from scratch. Reuse the ideas and selected modules, but do not copy the old app wholesale.

Reusable patterns from Dashboard Studio:

- CSV ingestion and tolerant parsing.
- Kaggle dataset import, if still useful.
- Dataframe profiling and metadata generation.
- Compact dataframe context for agents.
- Pydantic contract validation at agent boundaries.
- Sandboxed pandas code execution.
- Generated-code sanitization and repair loops.
- Artifact storage with stable run identifiers.
- Run tracing for debugging partial failures.
- Role-specific model routing and model benchmarking.
- Notebook-style audit trail generation.

What should not be inherited directly:

- The monolithic "generate entire dashboard" flow as the primary user experience.
- UI assumptions from Streamlit, FastAPI, or Next.js.
- Dashboard-first contracts where every analysis must become a dashboard component.
- Whole-run repair behavior where one bad generated component can dominate the entire pipeline.

This project should begin as a clean project folder under:

```text
C:\Users\Lord Vader\Documents\AI analyst
```

Dashboard Studio remains the reference project and source of lessons. It should not be modified as part of building this overview or the initial fork unless that is explicitly requested later.

## 4. Core Learning Goals

### Conversational Memory

The assistant must remember enough prior context to handle follow-ups like:

- "Show that again."
- "Now only compare movies after 2015."
- "Use the same filter but group by country."
- "Compare this with the previous chart."

Memory should not mean blindly appending the entire chat history forever. The system needs explicit recent-turn context, summarized older context, and retrievable analytical artifacts.

### Context Management

The system must learn what to include in each prompt or tool call:

- Dataset metadata.
- Column summaries.
- Recent conversation turns.
- Relevant prior outputs.
- Prior charts.
- Current user intent.
- Known filters or entities from earlier turns.

It must also learn what to drop or summarize. The previous project showed that large, duplicated context can cause token-limit and rate-limit failures.

### Tool Calling

The assistant should use tools instead of answering from text alone. Initial tools should inspect the dataset, preview rows, describe columns, run safe dataframe queries, retrieve artifacts, and retrieve memory.

### Stateful Analytical Reasoning

The app is iterative. A question is not isolated if it refers to prior work. The system needs explicit turn state, artifact links, and reference resolution.

### Safe Code Execution

Generated pandas code should execute in a constrained environment. The code must not access the filesystem, network, interpreter internals, unsafe imports, infinite loops, or arbitrary builtins.

### MCP Learning

Model Context Protocol is a learning objective, but it should not drive the first implementation. Build direct local dataset tools first. Once those tools are stable, wrap them in a local Dataset MCP server and compare direct tool calls with MCP tool calls.

### Explainability

The assistant should briefly explain what it did:

```text
I filtered the dataset to movies released after 2015, grouped by country, counted titles, and sorted the result descending before plotting the top countries.
```

Explanations should be useful for trust and debugging, not performative. They should distinguish computation from interpretation.

## 5. Recommended Starting Stack

Start with a lightweight chat-first UI, most likely Chainlit or a similar Python-native conversational app framework. The UI should be treated as disposable.

The durable architecture should live below the UI:

- `core/`
- `agents/`
- `contracts/`
- `mcp/`
- `tests/`

The first UI can change later, just like the previous project evolved beyond its first Streamlit version. Possible later interfaces include:

- Next.js product workspace.
- NiceGUI or Gradio prototype.
- Tauri or Electron desktop shell.
- Browser-native analytical workspace using DuckDB-WASM or Pyodide.

The key rule:

```text
The analyst engine must not depend on the UI framework.
```

## 6. Target Project Structure

```text
AI analyst/
|-- project-overview-plan.md
|-- README.md
|-- requirements.txt
|-- .env.example
|-- core/
|   |-- csv_io.py
|   |-- dataset_metadata.py
|   |-- dataframe_context.py
|   |-- artifacts.py
|   |-- sessions.py
|   |-- memory.py
|   |-- execution.py
|   |-- tracing.py
|   |-- model_config.py
|-- agents/
|   |-- dataset_understanding.py
|   |-- question_planner.py
|   |-- code_generator.py
|   |-- code_repair.py
|   |-- answer_synthesizer.py
|   |-- chart_suggester.py
|   |-- memory_summarizer.py
|-- contracts/
|   |-- base.py
|   |-- dataset.py
|   |-- session.py
|   |-- turn.py
|   |-- tools.py
|   |-- analysis.py
|   |-- charts.py
|   |-- memory.py
|-- ui/
|   |-- chainlit_app.py
|-- mcp/
|   |-- dataset_server.py
|-- artifacts/
|   |-- datasets/
|   |-- metadata/
|   |-- sessions/
|   |-- turns/
|   |-- analysis_outputs/
|   |-- charts/
|   |-- memory/
|   |-- traces/
|   |-- notebooks/
|   |-- logs/
|-- tests/
```

The exact file names may change during implementation, but the boundaries should remain stable.

## 7. Durable Architecture

### `core/`

Owns deterministic backend behavior:

- CSV ingestion.
- Dataset profiling.
- Dataframe context compaction.
- Artifact storage.
- Session state.
- Memory storage and retrieval.
- Safe pandas execution.
- Run and turn tracing.
- Model configuration.

`core/` must not import the UI.

### `agents/`

Owns LLM-assisted reasoning:

- Dataset understanding.
- User intent and question planning.
- Follow-up/reference resolution.
- Pandas code generation.
- Code repair after execution failure.
- Result interpretation.
- Chart suggestion.
- Memory summarization.

Agents should communicate through validated Pydantic contracts.

### `contracts/`

Owns shared schemas:

- Dataset metadata.
- Dataset sessions.
- Conversation turns.
- Tool calls.
- Analysis outputs.
- Chart payloads.
- Memory records.
- Trace events.

Every boundary that crosses from one subsystem to another should validate payloads through these contracts.

### `ui/`

Owns the first user-facing chat interface. It should:

- Upload a CSV.
- Show dataset load status.
- Display chat messages.
- Render tables/charts returned by the analyst engine.
- Expose trace or artifact links in a developer-friendly way.

The UI must not own analysis logic.

### `mcp/`

Owns the later MCP learning track. It should wrap stable local dataset tools after the direct tool layer is working.

## 8. First User Flow

1. User uploads a CSV.
2. System parses the file and saves the dataset artifact.
3. System profiles the dataframe and saves metadata.
4. System creates a dataset session.
5. Dataset understanding agent creates a semantic summary.
6. User asks an analytical question.
7. Question planner determines whether the answer needs:
   - metadata lookup,
   - dataframe preview,
   - generated pandas code,
   - chart output,
   - previous artifact retrieval,
   - clarification.
8. Code generator writes constrained pandas code if computation is needed.
9. Sandbox executes the code against a dataframe copy.
10. Result is serialized into an analysis output artifact.
11. Chart suggester creates a chart payload if useful.
12. Answer synthesizer produces a grounded response.
13. System saves the turn artifact.
14. Memory layer updates recent conversational memory and analytical memory.
15. UI displays the answer, table/chart, assumptions, limitations, and trace summary.

## 9. Memory Model

Use three layers of memory.

### Dataset Memory

Persistent per uploaded dataset.

Stores:

- Dataset ID.
- Source filename and file hash.
- Row and column counts.
- Column metadata.
- Data integrity summary.
- Semantic summary.
- Inferred entities, dimensions, metrics, and temporal fields.
- Suggested starter questions.

Created once after upload and refreshed only when the dataset changes.

### Conversational Memory

Session-scoped.

Stores:

- Recent user messages.
- Recent assistant answers.
- Resolved filters and entities.
- Clarifications.
- Summaries of older turns.

Used for references like:

- "that"
- "same as before"
- "compare those"
- "filter the earlier result"

### Analytical Memory

Session-scoped, artifact-backed.

Stores:

- Generated code.
- Execution outputs.
- Tables.
- Chart payloads.
- Insight summaries.
- Turn-to-turn references.

Used when a user asks to reuse or compare previous work.

## 10. Public Interfaces And Contracts

### `DatasetSession`

Fields:

- `session_id`
- `dataset_id`
- `metadata`
- `semantic_summary`
- `memory_summary`
- `turn_ids`
- `created_at`
- `updated_at`

Purpose:

Represents one ongoing analysis conversation over one uploaded dataset.

### `ConversationTurn`

Fields:

- `turn_id`
- `session_id`
- `user_message`
- `resolved_intent`
- `referenced_turn_ids`
- `generated_code`
- `execution_result`
- `chart_payload`
- `assistant_answer`
- `assumptions`
- `limitations`
- `trace`
- `created_at`

Purpose:

Represents one user message and everything the system did to answer it.

### `ResolvedIntent`

Fields:

- `question_type`
- `requires_code`
- `requires_chart`
- `filters`
- `grouping`
- `metrics`
- `referenced_entities`
- `referenced_turn_ids`
- `needs_clarification`
- `clarification_question`

Purpose:

Makes follow-up resolution explicit before code generation.

### `AnalysisExecutionResult`

Fields:

- `status`
- `output_key`
- `serialized_output`
- `row_count`
- `columns`
- `error_type`
- `error_message`
- `repair_attempts`

Purpose:

Captures deterministic execution results without requiring the UI to understand raw pandas objects.

### `ChartPayload`

Fields:

- `chart_id`
- `chart_type`
- `source_output_key`
- `title`
- `x`
- `y`
- `color`
- `top_n`
- `rationale`
- `warnings`

Purpose:

Provides a UI-independent chart contract that can later be rendered by Chainlit, Next.js, or another interface.

### Tool Contracts

Initial direct tools:

- `describe_dataset()`
- `describe_column(column_name)`
- `preview_rows(limit)`
- `run_dataframe_query(code)`
- `lookup_artifact(artifact_id)`
- `retrieve_memory(query)`
- `save_turn_artifact(turn_payload)`

Later MCP tools should expose a small subset first:

- `describe_dataset`
- `describe_column`
- `preview_rows`
- `run_dataframe_query`

## 11. Agent Workflow

### Dataset Understanding Agent

Input:

- Dataset metadata.
- Compact dataframe context.
- Optional user description.

Output:

- Semantic summary.
- Main entities.
- Important dimensions.
- Important metrics.
- Time fields.
- Suggested starter questions.
- Assumptions and limitations.

### Question Planner Agent

Input:

- Current user message.
- Dataset memory.
- Recent conversation memory.
- Relevant analytical memory.

Output:

- Resolved intent.
- Required tools.
- Referenced prior turns.
- Clarification request if necessary.

### Code Generation Agent

Input:

- Resolved intent.
- Dataset metadata.
- Compact dataframe context.
- Tool constraints.

Output:

- Safe pandas code.
- Expected output key.
- Expected output shape.
- Assumptions.

The code must assume a dataframe named `df` already exists and must write results into `analysis_outputs`.

### Code Repair Agent

Input:

- Failed code.
- Error type and message.
- Resolved intent.
- Dataset context.

Output:

- Repaired pandas code.
- Explanation of the change.

Repair should be limited. Repeated failure should produce an honest assistant response instead of hiding the error.

### Answer Synthesizer Agent

Input:

- User question.
- Resolved intent.
- Execution output.
- Chart payload.
- Relevant prior memory.

Output:

- Direct answer.
- Supporting evidence.
- Brief explanation of computation.
- Assumptions.
- Limitations.
- Suggested follow-up questions.

### Memory Summarizer Agent

Input:

- Older turns.
- Saved analytical artifacts.

Output:

- Compact memory summary.
- Important reusable references.
- Deprecated or low-value details to drop.

## 12. Implementation Phases

### Phase 1: Foundation

Goals:

- Create clean project structure.
- Port/adapt only backend-neutral pieces from Dashboard Studio.
- Add tests before UI complexity.

Build:

- CSV ingestion.
- Dataset metadata.
- Artifact paths.
- Safe execution.
- Base contracts.
- Model config.
- Basic tracing.

Exit criteria:

- A sample CSV can be loaded and profiled.
- Metadata artifact is saved.
- Safe pandas code can be executed against a dataframe.
- Unsafe generated code is rejected.
- Unit tests pass.

### Phase 2: Chat MVP

Goals:

- Build a simple chat-first experience.
- Answer first-order natural-language questions from computed outputs.

Build:

- Chainlit or equivalent lightweight UI.
- Dataset upload.
- Dataset summary response.
- Planner -> code generation -> execution -> answer loop.
- Turn artifact persistence.

Exit criteria:

- User can upload a CSV.
- User can ask a simple analytical question.
- Assistant executes code and answers from the result.
- Assistant can return a table or chart payload.
- Turn artifacts are saved.

### Phase 3: Conversational Memory

Goals:

- Support follow-ups and references.
- Avoid unbounded prompt growth.

Build:

- Recent-message memory.
- Turn summaries.
- Reference resolution.
- Memory retrieval by turn ID and semantic labels.

Exit criteria:

- "Show that again" retrieves the previous result.
- "Use the same filter" resolves prior filter context.
- Older history is summarized instead of sent in full.

### Phase 4: Analytical Memory

Goals:

- Treat prior outputs as reusable analytical objects.

Build:

- First-class storage for outputs and charts.
- Artifact lookup tools.
- Comparison support between prior turns.

Exit criteria:

- User can compare current results with a previous chart/table.
- Assistant can reuse a prior artifact when recomputation is unnecessary.
- Artifacts remain linked to sessions and turns.

### Phase 5: MCP Learning Track

Goals:

- Learn MCP with a small local server over stable dataset tools.

Build:

- Local Dataset MCP server.
- Tool discovery.
- Tool calls for dataset description, column description, row preview, and safe query execution.
- Tests comparing direct tools and MCP tools.

Exit criteria:

- MCP client can discover dataset tools.
- MCP tool outputs match direct tool outputs.
- Unsafe query behavior remains blocked.

### Phase 6: Future UI Migration

Goals:

- Decide whether the initial UI is enough.
- Move to a richer product shell only after the analyst engine works.

Possible migrations:

- Next.js app with Python worker.
- Desktop shell with Python sidecar.
- Browser-native analytics layer with DuckDB-WASM or Pyodide.

Exit criteria:

- UI migration does not require rewriting `core/`, `agents/`, or `contracts/`.

## 13. Pitfalls And Guardrails

### Monolithic Generation

Pitfall:

One giant analysis plan can fail because one generated metric or chart is bad.

Guardrail:

Use per-question execution. Keep each turn small. Let partial success survive.

### Context Bloat

Pitfall:

Sending full metadata, full chat history, all outputs, and full artifacts on every turn can hit token limits and rate limits.

Guardrail:

Use compact metadata, recent chat windows, memory summaries, and targeted artifact retrieval.

### Unsafe Code Generation

Pitfall:

Generated pandas code can try unsafe imports, filesystem access, network access, interpreter internals, long loops, or unsupported libraries.

Guardrail:

Use AST validation, restricted builtins, dataframe copies, blocked imports, timeout policy, and explicit output contracts.

### Hallucinated Numbers

Pitfall:

The assistant may produce plausible numerical answers without computing them.

Guardrail:

The answer synthesizer must use execution outputs for numbers. If no computation exists, it should say so or ask to run one.

### Weak Follow-Up Handling

Pitfall:

Questions like "that" and "same as before" are ambiguous unless resolved explicitly.

Guardrail:

Create a `ResolvedIntent` before code generation. Store referenced turn IDs and filters.

### Artifact Drift

Pitfall:

Saved code, outputs, charts, and answers can become disconnected.

Guardrail:

Every artifact should include `session_id`, `turn_id`, `dataset_id`, and source output keys.

### UI Lock-In

Pitfall:

The first UI framework can shape backend architecture in ways that make migration painful.

Guardrail:

No analysis logic in UI files. UI calls the analyst engine through stable contracts.

### MCP Too Early

Pitfall:

Starting with MCP before direct tools are stable adds protocol complexity before the app behavior is understood.

Guardrail:

Build direct tools first. Add MCP in Phase 5 as a wrapper and learning track.

### Model Overkill

Pitfall:

The previous project showed that stronger models can overbuild and fail sandbox constraints.

Guardrail:

Use role-specific model routing. Benchmark model changes on actual pipeline stages before upgrading broadly.

### Optional Repair Becoming Fatal

Pitfall:

Repair loops can become required paths and discard usable outputs when repair fails.

Guardrail:

Treat repair as resilience. If optional repair fails, save the original output, warning, trace, and limitations.

### Poor Observability

Pitfall:

Without trace artifacts, debugging depends on reproducing failures manually.

Guardrail:

Every turn should write trace events for planning, code generation, execution, repair, answer synthesis, and artifact save.

### Oversized Analytical Artifacts

Pitfall:

Large tables or verbose generated outputs can overwhelm prompts and UI rendering.

Guardrail:

Serialize compact previews, row counts, column names, truncation flags, and artifact references.

### Confusing Computation And Interpretation

Pitfall:

The assistant may blend measured facts and speculative explanations.

Guardrail:

Answer format should separate computed findings, interpretation, assumptions, and limitations.

### Dataset Quality Problems

Pitfall:

Malformed CSVs, missing values, mixed types, tiny sample groups, duplicated rows, and weird encodings can derail analysis.

Guardrail:

Keep tolerant ingestion, data integrity summaries, visible warnings, and conservative analysis behavior.

## 14. Test Plan

### Unit Tests

Cover:

- CSV parsing.
- Metadata profiling.
- Dataframe context compaction.
- Artifact path stability.
- Safe code execution.
- Unsafe code rejection.
- Contract validation.
- Memory summarization.
- Tool outputs.

### Agent Contract Tests

Cover:

- Dataset understanding output shape.
- Question planner output shape.
- Code generator output shape.
- Code repair output shape.
- Answer synthesizer output shape.
- Memory resolver output shape.

### Conversation Tests

Scenarios:

- First analytical question over a dataset.
- Follow-up filter using prior context.
- "Show that again."
- Chart request from computed output.
- Failed code repair.
- Reuse of prior output.
- Clarification when the user question is under-specified.

### Regression Tests From Dashboard Studio Lessons

Scenarios:

- Malformed generated code.
- Oversized context.
- Invalid contract payloads.
- Optional repair failure.
- Missing artifacts after partial failure.
- Unsupported chart payload.
- Model-generated code that tries blocked operations.

### MCP Tests

Add after Phase 5:

- Server starts locally.
- Tool discovery works.
- Each dataset tool can be called.
- Unsafe query code is rejected.
- MCP outputs match direct local tool outputs.

## 15. Success Criteria

The project is successful when a user can:

- Upload a CSV.
- See a clear dataset summary.
- Ask natural-language analytical questions.
- Receive answers grounded in computed outputs.
- Request charts.
- Ask follow-up questions using prior context.
- Reuse or compare previous results.
- Inspect what code was run.
- Understand assumptions and limitations.
- Review saved artifacts for each turn.
- Learn how memory, context, tool calling, MCP, and explainability work in practice.

## 16. Early Milestones

### Milestone 1: Dataset Session Created

The system can ingest a CSV, profile it, save metadata, and create a `DatasetSession`.

### Milestone 2: First Question Answered

The user can ask one analytical question and receive an answer from executed pandas code.

### Milestone 3: First Follow-Up Resolved

The user can ask a follow-up that depends on prior context.

### Milestone 4: Analytical Artifact Reused

The user can ask to show, filter, or compare a previous result.

### Milestone 5: Dataset MCP Server

The stable direct dataset tools are exposed through a local MCP server.

## 17. Assumptions And Defaults

- The project starts as a clean folder/repo under `AI analyst`.
- The first UI can change later.
- The durable goal is the analyst engine, not the first UI framework.
- Chainlit or a similar lightweight chat UI is the recommended MVP path.
- Dashboard Studio remains a reference project and source of reusable backend patterns.
- The new app should preserve the learning-oriented spirit of `new project.md` while being more implementation-ready.
- Agent outputs should be structured, validated, and saved.
- The assistant should prefer honest uncertainty over unsupported claims.

## 18. Priority Roadmap

### High Priority

These items create the durable foundation. Do these before building a rich UI.

- Create the clean project structure under `AI analyst`.
- Create `.gitignore`, `.env.example`, `requirements.txt`, and a starter `README.md`.
- Create package folders: `core/`, `agents/`, `contracts/`, `ui/`, `mcp/`, and `tests/`.
- Define initial Pydantic contracts for `DatasetSession`, `ConversationTurn`, tool calls, analysis outputs, chart payloads, and trace events.
- Port/adapt CSV ingestion and dataset metadata from Dashboard Studio.
- Port/adapt safe execution and generated-code sanitizer.
- Add artifact path helpers for datasets, metadata, sessions, turns, analysis outputs, charts, memory, traces, and logs.
- Add tests for ingestion, metadata, execution, contracts, and artifact paths.
- Build the first minimal chat loop only after the deterministic foundation is testable.

### Medium Priority

These items turn the foundation into a useful conversational analyst.

- Add the dataset understanding agent.
- Add the question planner agent with explicit `ResolvedIntent`.
- Add the code generation and limited code repair agents.
- Add the answer synthesizer agent that answers only from computed outputs.
- Add recent conversational memory and basic follow-up resolution.
- Save every user question and assistant response as a turn artifact.
- Add table and chart payload rendering in the first chat UI.
- Add turn-level tracing for planning, code generation, execution, repair, answer synthesis, and artifact save.
- Add conversation tests for first questions, follow-up filters, chart requests, failed code repair, and "show that again."

### Low Priority

These items are valuable, but they should wait until the analyst loop works reliably.

- Add analytical memory search across older outputs, charts, and insights.
- Add notebook-style export from the conversation history.
- Add the local Dataset MCP server.
- Compare direct local tools with MCP tool calls.
- Add role-specific model benchmarking for the new per-turn pipeline.
- Evaluate migration from the first chat UI to Next.js, desktop, or a richer product workspace.
- Add multi-dataset comparison, branching conversations, shareable sessions, and polished reporting/export features.
