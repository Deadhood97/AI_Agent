# Project 02 — Conversational Dataset Analyst

## Overview

This project is the next evolution of the Smart AI Dashboarding System.

The previous project focused on:

> Upload dataset → generate dashboard automatically

This project focuses on:

> Upload dataset → chat with an AI analyst about the dataset

Instead of producing a fixed dashboard immediately, the system becomes conversational and iterative. The user can ask questions about the uploaded dataset, explore ideas, request charts, drill deeper into insights, and refine analysis over multiple turns.

The goal is to learn how AI systems handle:

* memory
* context management
* tool calling
* iterative analytical reasoning
* conversational state over time

---

# Core Objective

Build an AI-powered dataset analyst that can:

* accept CSV uploads
* understand the dataset structure
* retain context about the dataset throughout a conversation
* answer analytical questions conversationally
* generate code to compute answers
* create charts when useful
* explain what it is doing step-by-step

The assistant should feel like chatting with a data analyst who has already studied the uploaded file.

---

# Example User Experience

## Dataset Upload

User uploads:

`netflix_titles.csv`

System responds:

> Dataset loaded successfully.
> 8,807 rows · 12 columns
> Main entities detected: titles, genres, release years, countries, directors

---

## Conversation

### User

Which countries produce the most Netflix content?

### Assistant

* generates pandas code
* executes analysis
* returns chart + answer

> United States leads by a wide margin, followed by India and the United Kingdom.

---

### User

Now only compare movies after 2015

Assistant understands:

* “movies” refers to `type == Movie`
* “after 2015” is a filter
* previous question context should be reused

---

### User

Why do you think India grew so fast?

Assistant:

* references prior analysis
* synthesizes insight
* explains reasoning

---

# Learning Goals

This project is primarily about learning.

## 1. Conversational Memory

Understand how an AI system remembers prior interactions in a session.

Examples:

* “compare with previous chart”
* “show that again”
* “filter the earlier results”

---

## 2. Context Management

Learn what context should be passed into prompts.

Examples:

* full dataset metadata
* prior conversation turns
* previous generated charts
* previous computed metrics

Also learn:

* what to keep
* what to summarize
* what to drop

to manage token usage.

---

## 3. Tool Calling

Teach the assistant to use tools instead of answering from text alone.

Examples:

* inspect dataframe
* run pandas code
* generate chart
* retrieve earlier metric output

---

## 4. Stateful Analytical Reasoning

Unlike dashboard generation, this project is iterative.

The system needs to support:

* follow-up questions
* changing filters
* comparisons
* deeper investigation

---

## 5. Explainability

The assistant should explain what it is doing while working.

Example:

> I filtered the dataset to movies released after 2015, grouped by country, and counted titles per country before plotting the result.

This is useful for:

* debugging
* trust
* learning

---

# Proposed Architecture

## Existing pieces to reuse

Reuse from Project 01:

* CSV ingestion
* Kaggle dataset import
* dataframe profiling
* dataset metadata generation
* metric code generation
* code execution sandbox
* artifact logging
* run tracing
* contracts

---

# New Architecture

```plaintext
Upload Dataset
    ↓
Dataset Profile + Metadata
    ↓
Create Conversation Session
    ↓
User asks question
    ↓
Planner Agent
    ↓
Code Generation Agent
    ↓
Sandbox Execution
    ↓
Insight Generation Agent
    ↓
Optional Chart Generation
    ↓
Assistant responds
```

---

# Conversation State

Each uploaded dataset gets its own session.

## Session contains:

* session id
* dataset id
* dataset metadata
* chat history
* generated metrics
* generated charts
* saved analytical insights

This allows the assistant to reference previous work.

---

# Memory Model

Use 3 layers of memory.

---

## 1. Dataset Memory

Persistent per uploaded dataset.

Stores:

* column metadata
* semantic understanding
* dataset summary
* inferred roles

Created once at upload time.

---

## 2. Conversational Memory

Stores recent chat history.

Examples:

* user question
* assistant answer
* follow-up clarification

Used for references like:

* “that”
* “same as before”
* “compare those”

---

## 3. Analytical Memory

Stores generated analytical artifacts.

Examples:

* computed metric outputs
* generated charts
* prior insights

Useful for:

> Compare this chart with the earlier one

without rerunning everything.

---

# MCP Learning Track

A major goal of this project is learning Model Context Protocol (MCP).

## Why MCP

MCP is a standard way for language models to interact with tools and external systems.

Think of it as:

> a shared protocol between the model and your application tools

Instead of wiring custom tool interfaces manually, MCP provides a structured interface.

---

# First MCP Server to Build

## Dataset MCP Server

Expose tools like:

### `describe_dataset()`

Returns:

* row count
* column count
* dataset summary

---

### `describe_column(column_name)`

Returns:

* dtype
* null count
* min/max
* representative values

---

### `preview_rows(limit)`

Returns:

sample dataframe rows

---

### `run_dataframe_query(code)`

Executes safe pandas code in sandbox and returns results

---

# Why this is a good first MCP server

It is:

* directly relevant to the app
* small in scope
* easy to test locally
* reusable in future projects

---

# Suggested Build Plan

# Phase 1 — Dataset + Chat UI

Build:

* CSV upload
* dataset profiling
* chat interface

No complex memory yet.

---

# Phase 2 — Question Answering

For each user message:

* read dataset metadata
* generate pandas code
* execute
* return answer

---

# Phase 3 — Conversational Memory

Add:

* recent message history
* follow-up question support
* reference resolution

Examples:

* “show that again”
* “compare with previous one”

---

# Phase 4 — Analytical Memory

Store:

* prior chart outputs
* prior metric outputs
* previous insights

Allow reuse in future turns.

---

# Phase 5 — MCP Server

Build dataset MCP server.

Expose:

* describe dataset
* describe column
* query dataframe

Then connect assistant to it.

---

# Success Criteria

Project is successful if the user can:

* upload any CSV
* ask natural-language questions
* receive correct analysis
* request charts
* ask follow-up questions
* reference prior results naturally
* understand what the assistant is doing

---

# Example Stretch Goals

Optional future ideas:

* downloadable notebook export from conversation
* “save this chart” feature
* branching conversations
* chart history sidebar
* SQL query generation
* compare multiple uploaded datasets
* shareable analysis sessions

---

# Main Reason for Building This

To deeply learn:

* conversational AI architecture
* memory handling
* context-window design
* tool calling
* MCP servers
* iterative AI reasoning over structured data

This project extends the previous dashboard generator into a much more interactive AI analyst experience while reusing the backend foundation already built.
