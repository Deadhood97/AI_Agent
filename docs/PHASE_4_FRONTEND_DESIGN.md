# Phase 4 Frontend Design

This document is the design target for the first serious web UI of the Conversational Dataset Analyst.

The product direction is:

```text
Upload or attach data -> chat with an analyst -> inspect answer, plan, trace, and data context
```

The frontend should feel like a focused analyst workspace, not a set of scattered dashboard cards.

## Reference Study

The reference screenshots are useful because they both treat conversation as the main work surface.

### What To Learn From Julius

Julius has a strong "start here" experience:

- A persistent left workspace rail.
- A clear top bar with connection/runtime state.
- One central first action: upload a file or start a conversation.
- Starter workflows are visible, but they are secondary to the main input.
- Dark surfaces, subtle borders, and restrained accent colors keep attention on the task.

For our app, the equivalent should be:

- Upload CSV or attach data inside the main composer area.
- Show the top 3 suggested questions as starter prompts, not as unrelated cards.
- Keep dataset/session controls nearby, but visually secondary.

### What To Learn From Perplexity-Style Analyst Views

The second reference is stronger for after a question has been asked:

- Thread title is clear and centered in the workspace.
- Answer, images/sources/steps are organized as tabs or modes.
- The follow-up composer stays at the bottom of the main work area.
- The answer/result is the central artifact.
- Developer/explainability context exists, but does not overwhelm the answer.

For our app, the equivalent should be:

- Main thread contains user questions and analyst answers.
- `Answer`, `Data`, `Plan`, and `Trace` should become inspectable modes.
- The composer should remain available for follow-up questions.
- Plan/trace exists because the user is also the developer, but it should be structured.

## Product Principles

1. Chat is the product.

The user should feel like they are speaking to a data analyst. Upload, preview, suggestions, plans, traces, and outputs are supporting context.

2. Desktop is primary.

This is a data analysis app. Tables, traces, and plans need width. Mobile should not clip or break, but we optimize for desktop.

3. The interface should teach cause and effect.

The user wants to learn agentic development. The UI should make it easy to see:

- what the user asked
- which plan was created
- what code or deterministic path ran
- what output was produced
- what answer was returned

4. Do not overbuild the framework yet.

Keep the current standard-library web server and vanilla JS until state complexity truly demands React or another frontend framework.

5. Colors must be boring in the best way.

Use a restrained palette with tested contrast. Avoid one-note palettes, low-contrast gray text, and decorative gradients.

## Target Layout

```text
+--------------------------------------------------------------------------+
| Left Rail | Top Bar: Thread title / dataset status / runtime / settings  |
|----------+---------------------------------------------------------------|
| New      |                                                               |
| Threads  |                 Main Chat Workspace                           |
| Files    |                                                               |
| Runs     |    Empty state: "What do you want to analyze today?"           |
| Traces   |                                                               |
| Settings |    Composer: attach CSV + ask question + send                  |
|          |                                                               |
|          |    Starter prompts: top 3 suggested questions                  |
|          |                                                               |
|          |    Conversation: user messages + analyst answers               |
|          |                                                               |
|          |    Follow-up composer pinned near bottom                        |
|----------+---------------------------------------------------------------|
|          | Right Inspector / Drawer: Data, Plan, Trace, Session           |
+--------------------------------------------------------------------------+
```

The inspector can begin as a right column. Later it can become a drawer or tabbed panel if the chat needs more space.

## Core Screens

### Empty State

Purpose: start the first thread.

Content:

- App title or thread title.
- Prompt: `What do you want to analyze today?`
- Large composer with:
  - attach CSV
  - optional dataset note
  - question input
  - send/analyze button
- Starter workflow cards only if they map to real features.

Current starter cards we can support soon:

- Upload CSV
- Ask top 3 questions
- View dataset preview
- Inspect plan and trace

Avoid fake workflows like "time series analysis" until the backend can actually do them.

### Dataset Loaded State

Purpose: make the dataset feel active in the thread.

Content:

- Chat message from analyst:
  - filename
  - row count
  - column count
  - suggested next questions
- Right inspector:
  - dataset metrics
  - preview table
  - session id

The top 3 questions should appear as prompt chips below the analyst message or above the composer.

### Answer State

Purpose: show the result and teach how it happened.

Content:

- User message.
- Analyst answer.
- Result artifact if useful.
- Inspector tabs:
  - `Data`: preview/current dataset context
  - `Plan`: `AnalysisPlan`
  - `Trace`: local trace events and LangSmith status
  - `Output`: serialized output

## Component Plan

### App Shell

- `app-shell`
- `left-rail`
- `top-bar`
- `main-workspace`
- `inspector-panel`

The shell gives the product a stable app shape.

### Left Rail

Initial items:

- New thread
- Current dataset
- Runs
- Traces
- Settings

Early version can be mostly visual. Do not pretend navigation works if it does not. Disabled or inactive states are acceptable.

### Top Bar

Initial items:

- Thread title, default `New Thread`
- Dataset status: `No dataset`, `Dataset loaded`, `Running`
- Runtime/planner label: `Deterministic`
- LangSmith label if tracing is enabled later

### Chat Thread

Message types:

- assistant
- user
- system/status
- error

Each assistant answer should be able to reference:

- plan id
- trace id
- output key
- turn id

### Composer

The composer is the most important component.

Initial controls:

- CSV attach button
- text input
- send button

Later controls:

- planner mode toggle
- Kaggle import
- saved prompts
- RAG knowledge mode
- MCP tool mode

### Starter Prompts

Prompt chips should be generated from `core.question_suggestions`.

Behavior:

- Click prompt -> fills composer.
- Enter/send -> asks that question.

Later:

- Click prompt can send immediately if that feels better.

### Inspector

Initial tabs:

- Data
- Plan
- Trace

The inspector is what makes the app good for learning. It should answer: "What caused this output?"

## Visual Direction

The references are dark, focused, and app-like. We should move in that direction carefully.

### Recommended Theme

Use a dark analyst workspace with restrained accents:

```css
--bg: #0f1115;
--rail: #090a0d;
--surface: #171a1f;
--surface-elevated: #1f232a;
--border: #2b3038;
--text: #f4f7fb;
--muted: #a7b0bd;
--subtle: #6f7a88;
--accent: #2dd4bf;
--accent-strong: #14b8a6;
--blue: #60a5fa;
--warning: #f59e0b;
--error: #fb7185;
```

Contrast targets:

- Normal text: at least 4.5:1.
- Small muted text: prefer at least 4.5:1, not merely 3:1.
- Buttons: white or near-white text on accent must pass 4.5:1.
- Borders should be visible but not noisy.

### Shape And Spacing

- Cards/panels: 8px radius maximum.
- Inputs: 8px radius maximum.
- No decorative gradient orbs.
- No oversized hero section.
- Dense enough for repeated work, not a marketing page.

### Typography

- Do not scale font size with viewport width.
- Use fixed desktop/mobile breakpoints.
- Keep letter spacing at `0`.
- Use small headings inside panels.
- Reserve large text only for empty-state prompt.

## Interaction Flow

### First Use

1. User opens app.
2. Main workspace asks: `What do you want to analyze today?`
3. User attaches CSV and optionally asks a question.
4. Backend ingests CSV.
5. UI shows analyst message with dataset summary.
6. UI shows top 3 suggested prompts.

### Asking A Question

1. User sends prompt.
2. User message appears immediately.
3. Assistant status says planning/running.
4. Backend runs `DatasetTools.run_planned_turn`.
5. Assistant answer replaces the pending status.
6. Inspector updates with plan and trace.

### Planning Failure

1. User message remains in thread.
2. Assistant explains that the planner could not handle the question.
3. Inspector shows failed attempts.
4. Suggested starter prompts remain available.

## Incremental Implementation Plan

### Step 1: App Shell

- Add left rail.
- Add top bar.
- Keep current backend endpoints.
- Keep vanilla JS.

Acceptance:

- Desktop screenshot looks like one cohesive app.
- Chat workspace is visually primary.
- Dataset context is clearly secondary.

### Step 2: Composer-Centered Upload

- Move CSV upload into the main composer/empty state.
- Keep optional dataset note.
- After upload, show dataset summary as assistant message.

Acceptance:

- User can start with upload only.
- User can start with upload plus question later.
- No separate dominant upload card.

### Step 3: Inspector Tabs

- Add tabs for `Data`, `Plan`, `Trace`.
- Move preview and plan/trace into one inspector.

Acceptance:

- User can inspect what caused an answer without scanning multiple unrelated panels.

### Step 4: Starter Prompts

- Render top 3 suggestions as prompt chips.
- Prompt chips fill the composer.

Acceptance:

- Suggested questions feel like conversation starters.

### Step 5: Visual Theme Pass

- Move to dark theme.
- Run contrast checks.
- Capture desktop screenshot.

Acceptance:

- Text is readable.
- Accent color is consistent.
- UI does not feel one-note or mismatched.

### Step 6: LangSmith/Developer Visibility

- Add LangSmith status to top bar or inspector.
- Link local trace/plan data to turns.

Acceptance:

- User can connect UI behavior to LangSmith traces and local artifacts.

## What Not To Do Yet

- Do not add fake workflow cards that the backend cannot execute.
- Do not make a marketing landing page.
- Do not move to React just for aesthetics.
- Do not optimize for mobile as the primary experience.
- Do not hide plan/trace; this project is also a learning tool.

## Success Criteria

Phase 4 frontend is successful when:

- The first screen is clearly chat-first.
- Uploading data feels like adding context to a conversation.
- Suggested questions feel like starter prompts.
- The answer appears in a thread.
- The user can inspect plan and trace beside the answer.
- Desktop layout feels cohesive and calm.
- Color contrast is verified.
- Existing backend tests still pass.
