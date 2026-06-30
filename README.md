# Conversational Dataset Analyst

Project 02 in the AI analytics learning track.

This project is a clean fork/evolution of Dashboard Studio. The goal is to move from:

```text
Upload dataset -> generate dashboard
```

to:

```text
Upload dataset -> chat with an AI analyst
```

The durable app logic lives in `core/`, `contracts/`, and `agents/`. The first UI should stay replaceable.

## Setup

```powershell
cd "C:\Users\Lord Vader\Documents\AI analyst"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` if needed, then add local secrets. Do not commit `.env`.

The Phase 4 web UI uses Python's standard library, so it does not need a frontend framework yet.

Optional LangSmith tracing/evaluation dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-tracing.txt
```

See [docs/LEARNING_LABS.md](docs/LEARNING_LABS.md) for the hands-on lab rhythm, quiz prompts, and journal prompts.

Optional LangChain/LangGraph learning dependencies, for later labs:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-agent-frameworks.txt
```

Optional OpenAI-assisted dataset briefings:

```powershell
# in .env
OPENAI_API_KEY=...
OPENAI_BRIEFING_ENABLED=true
OPENAI_BRIEFING_MODEL=gpt-4.1-mini
```

When disabled or unavailable, imports fall back to deterministic briefing and suggestions.

## Test

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

## CLI Smoke Run

```powershell
.\.venv\Scripts\python.exe -m ui.cli_app path\to\data.csv --question "What is the total revenue?"
```

With `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY` set, the CLI smoke run also creates LangSmith traces.

## Web UI

```powershell
.\.venv\Scripts\python.exe -m ui.web_app --host 127.0.0.1 --port 8765
```

Open http://127.0.0.1:8765 in your browser. The UI is chat-first and desktop-first: paste a Kaggle dataset link or `owner/dataset-slug` reference, use suggested starter prompts, ask follow-up questions, and inspect dataset context plus plan/trace/output beside the conversation.

## LangSmith Evaluation Smoke

```powershell
.\.venv\Scripts\python.exe -m evals.langsmith_smoke
```

## Current Priority

Phase 4 is the first user-friendly, chat-first frontend over the deterministic backend:

- desktop-first Kaggle dataset import workflow
- conversational analyst thread
- top 3 suggested starter prompts
- custom user question input in the chat flow
- plan/trace inspection
- dataset preview
