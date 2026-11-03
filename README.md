# Empório da Música — Customer Service Agent

Prototype of a text-message agent that serves customers of **Empório da Música**, a fictional
musical instrument store in Campo Grande/MS, Brazil.
Artefact technical case — AI Engineer (2026). An English summary of the brief and a requirements checklist are in [`docs/challenge.md`](docs/challenge.md).

> 🚧 **Work in progress.** Sections marked _TODO_ will be filled in as development progresses.

---

## Contents

1. [How to run](#how-to-run)
2. [Repository layout](#repository-layout)
3. [Technical decisions](#technical-decisions)
4. [Data handling](#data-handling)
5. [Interaction examples](#interaction-examples)
6. [Assumptions](#assumptions)
7. [Known limitations and next steps](#known-limitations-and-next-steps)
8. [Use of coding assistants](#use-of-coding-assistants)

---

## How to run

**Prerequisites:** Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync                      # creates .venv and installs dependencies
source .venv/bin/activate
cp .env.example .env         # fill in the model provider API key
```

Run the tests (no API key needed):

```bash
uv run pytest
```

Check that the curated policy manual still covers the original PDF:

```bash
uv run python scripts/validate_policies.py
```

Chat with the agent in the terminal (needs `ANTHROPIC_API_KEY` in `.env`):

```bash
uv run emporio                    # conversation "default"
uv run emporio --session ana      # resume or start the conversation "ana" (history kept in SQLite)
uv run emporio --show-tools       # also print the tool calls behind each answer
```

Inside the chat, `/nova` clears the session history and `/sair` quits.

## Repository layout

```
.
├── data/
│   ├── raw/                 # original data provided by the store (read-only)
│   └── processed/           # cleaned/derived data (e.g. policies as Markdown)
├── docs/
│   ├── decisions/           # architecture decision records (ADRs)
│   ├── challenge.md         # requirements and deliverables checklist
│   └── data_analysis.md     # exploratory analysis and data issues found
├── examples/                # 3–5 real conversations with the agent (.md)
├── scripts/                 # helper scripts (ingestion, example generation)
├── src/emporio_agent/       # agent source code
├── tests/                   # automated tests
├── .env.example
└── pyproject.toml
```

## Technical decisions

_TODO:_ justify each decision (required by the brief).

| Decision | Choice | Rationale |
|---|---|---|
| Agent framework / approach | _TODO_ | _TODO_ |
| Model and provider | Claude via the Anthropic SDK (`claude-opus-5-5`, effort `low`, configurable) | Reliable tool use, good Portuguese, simple SDK for a hand-written loop. See [ADR 001](docs/decisions/001-llm-provider.md) |
| Retrieval architecture (policies) | _TODO_ | _TODO_ |
| Data access (CSVs) | _TODO_ | _TODO_ |
| Prompt strategy / persona | _TODO_ | _TODO_ |
| Agent language | Brazilian Portuguese (customers are Brazilian); code and docs in English | _TODO_ |
| Interface | _TODO_ | _TODO_ |
| Conversation history persistence | _TODO_ | _TODO_ |

## Data handling

Summary of the issues found in the data and how each was handled.
Details in [`docs/data_analysis.md`](docs/data_analysis.md).

_TODO_

## Interaction examples

Conversations live in [`examples/`](examples/). _TODO:_ list each scenario and what it demonstrates.

## Assumptions

_TODO:_ interpretations adopted where the brief or the data are ambiguous
(initial list in [`docs/data_analysis.md`](docs/data_analysis.md#open-decisions)).

## Known limitations and next steps

_TODO_

## Use of coding assistants

_TODO:_ which tool was used (e.g. Claude Code) and how it fit into the workflow.
