# Codex Project Memory

This is the memory file for Codex to quickly understand the project.

## Project
Conversational Dataset Analyst is a Python learning project. The current goal is a deterministic backend for:

```text
Upload CSV dataset -> ask simple analytical questions -> get computed answers
```

The backend foundation comes before heavier UI, LLM, agent, RAG, or MCP work.

## Structure
- `core/` contains durable backend behavior.
- `contracts/` contains Pydantic v2 models that define persisted and internal shapes.
- `ui/cli_app.py` is a replaceable smoke interface.
- `ui/web_app.py` and `ui/web/` contain the Phase 4 desktop-first web UI.
- `evals/langsmith_smoke.py` is an optional LangSmith evaluation harness.
- `tests/test_foundation.py` is the main behavioral test suite.
- `artifacts/` is runtime output/local data, not source.
- `agents/` and `mcp/` are placeholders for later phases.

## Main Flow
1. `DatasetTools.ingest_csv_bytes` receives CSV bytes and delegates to `DatasetIngestionService`.
2. `core.csv_io.read_csv_bytes` parses CSV with pandas fallbacks.
3. `core.dataset_metadata.build_dataset_metadata` profiles columns and data quality.
4. `ArtifactStore` persists raw CSV, metadata, sessions, turns, traces, and outputs.
5. `core.question_suggestions.suggest_questions` creates the starter top-3 questions from dataset metadata.
6. Sessions store `suggested_questions` so the upload state can power the starter app experience.
7. `DatasetSessionService` reloads datasets for preview and question suggestions.
8. `SimplePlanner` can plan row count, sum, mean, and simple group-count questions.
9. `core.planning.plan_question` wraps planner output in an inspectable `AnalysisPlan` contract.
10. `AnalysisTurnService` stores plans, executes turns, persists outputs, and attaches turns to sessions.
11. `core.execution.execute_dataframe_code` safely validates and executes generated pandas code.
12. `core.serialization` normalizes outputs.
13. `core.answers` formats deterministic answers.

## Observability
- Phase 2 adds LangSmith-first observability while preserving local JSON trace artifacts.
- `core.langsmith_tracing.langsmith_span` is the wrapper for all LangSmith spans and must no-op when tracing is disabled or LangSmith is unavailable.
- Keep LangSmith payloads compact: send metadata summaries, suggestion summaries, code summaries, output summaries, and trace event summaries instead of full datasets or large table rows.
- The CLI creates a top-level `CLI dataset analyst workflow` span so LangSmith shows the whole starter flow from upload to suggestions to optional answer.
- Backend spans should remain nested around ingestion, suggestion retrieval, planning, dataframe execution, and answer formatting.
- User-facing LangSmith setup and viewing notes live in `docs/LANGSMITH_OBSERVABILITY.md`.
- Phase 3 planner notes live in `docs/PHASE_3_PLANNING.md`.
- Phase 4 frontend design direction lives in `docs/PHASE_4_FRONTEND_DESIGN.md`.

## Key Modules
- `core.dataset_tools.DatasetTools`: compatibility facade for ingestion, preview, analysis turns, and planned turns. Keep this small and delegate implementation to services.
- `core.ingestion.DatasetIngestionService`: CSV/Kaggle ingestion, metadata creation, session creation, initial suggestions, and ingestion traces.
- `core.dataset_sessions.DatasetSessionService`: dataframe reload, preview payloads, and session question suggestions.
- `core.analysis_turns.AnalysisTurnService`: planned turns, direct analysis turns, code execution, output persistence, plan persistence, and turn traces.
- `core.question_suggestions`: deterministic top-3 starter questions based on metadata; later this is the natural replacement point for RAG/LLM-backed suggestions.
- `core.kaggle_import`: Kaggle dataset importer ported from AI dashboaring. It normalizes dataset refs, lists files, selects CSV/CSV.zip files, safely extracts zips, and returns CSV bytes for ingestion.
- `core.planning`: planner orchestration and deterministic adapter that emits `AnalysisPlan` contracts.
- `core.llm_planner`: optional OpenAI structured-output planner scaffold. It is opt-in and should fail clearly if dependencies or credentials are missing.
- `core.execution`: generated-code sandbox. Code must create `analysis_outputs` as a dict.
- `core.simple_planner`: deterministic planner with intentionally limited scope.
- `core.sessions`: session/turn persistence.
- `core.memory`: lightweight session memory records.
- `core.langsmith_tracing`: optional tracing helpers and compact payload summaries for LangSmith.
- `ui.web_app`: dependency-light HTTP server for the Phase 4 web UI. It serves `ui/web/` and exposes `/api/upload` plus `/api/ask`.
- `ui/web/`: chat-first desktop analyst workspace. It now uses a dark app shell with left rail, top bar, composer-centered CSV attach/question input, starter prompt chips, and right inspector tabs for Data/Plan/Trace.

## Commands
```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -m ui.cli_app path\to\data.csv
.\.venv\Scripts\python.exe -m ui.cli_app --kaggle owner/dataset-slug --kaggle-file train.csv
.\.venv\Scripts\python.exe -m ui.cli_app path\to\data.csv --question "What is the total revenue?"
.\.venv\Scripts\python.exe -m ui.cli_app path\to\data.csv --question "Which region has the highest revenue?" --allow-llm-planner
.\.venv\Scripts\python.exe -m ui.web_app --host 127.0.0.1 --port 8765
.\.venv\Scripts\python.exe -m evals.langsmith_smoke
```

## Rules For Future Work
- Keep durable app logic in `core/` and schema boundaries in `contracts/`.
- Keep UI replaceable.
- Phase 4 UI is chat-first and desktop-first. The primary use case is asking analytical questions in a conversation, with dataset context visible beside it.
- Before changing the Phase 4 frontend, read `docs/PHASE_4_FRONTEND_DESIGN.md` and keep changes aligned with that design target.
- For frontend work, verify the desktop screenshot first and keep colors high-contrast. Avoid oversized marketing/hero treatment or dashboard-first composition unless the chat remains the main workflow.
- Keep `DatasetTools` as a stable facade for callers; put new ingestion/session/execution behavior in focused service modules.
- Treat deterministic suggestions as the Phase 1 product skeleton: upload first, suggest top 3 questions, then let the user choose or type a question.
- For Phase 2 observability, every new user-visible workflow should have a top-level LangSmith span and compact child outputs.
- Kaggle imports should flow through `DatasetTools.ingest_kaggle_dataset`, then reuse the same ingestion, suggestions, sessions, traces, and analysis path as local CSV uploads.
- Phase 3 plans are developer-facing explanation artifacts. Keep them compact, inspectable, and persisted on turns plus `artifacts/plans`.
- LLM planning is optional and incremental. Do not let LLM output bypass `AnalysisPlan` validation or `execute_dataframe_code`.
- LLM fallback should show deterministic failure and LLM attempt details in LangSmith. Live LLM use requires `OPENAI_API_KEY` and `openai`.
- Treat generated dataframe code as untrusted and always run it through `execute_dataframe_code`.
- Add focused tests to `tests/test_foundation.py`.
- Use temporary directories in tests that write artifacts.
- Do not commit `.env` or private data in `artifacts/`.
