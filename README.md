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
cp .env.example .env         # paste your free Gemini API key (https://aistudio.google.com/apikey)
```

Run the tests (no API key needed):

```bash
uv run pytest
```

Check that the curated policy manual still covers the original PDF:

```bash
uv run python scripts/validate_policies.py
```

Chat with the agent in the terminal (needs `GEMINI_API_KEY` in `.env`; the free tier is enough):

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

| Decision | Choice | Rationale |
|---|---|---|
| Agent approach | **Function calling** with a hand-written tool-use loop (`agent.py`, ~60 lines), no framework | The questions are either live data lookups or policy lookups, often both in one answer. Letting the model pick among six small, well-described tools covers both with one mechanism. A framework (LangChain, LlamaIndex) would hide the loop that reviewers want to see, for no gain at this size. |
| Model and provider | **Google Gemini `gemini-3.5-flash-lite` (free tier)** through the `openai` SDK and Gemini's OpenAI-compatible endpoint; base URL, key and model configurable | Free for the author and for reviewers (no card needed), good tool use and Portuguese. The OpenAI-compatible format also runs on Groq, Ollama or OpenAI by changing `.env`. Claude was the first choice ([ADR 001](docs/decisions/001-llm-provider.md)) but its API is prepaid only, see [ADR 002](docs/decisions/002-switch-to-gemini.md) |
| Retrieval (policies) | Curated Markdown of the PDF, split by section, ranked with a simplified **BM25** plus a short Portuguese synonym list, exposed as the `search_policies` tool | The manual is ~3k tokens / ~20 sections. Embeddings and a vector store would be infrastructure with no benefit; lexical ranking is deterministic and unit-tested (real questions → expected section). The raw PDF text came out one word per line, so it was rewritten as Markdown and checked against the PDF by `scripts/validate_policies.py`. |
| Data access (CSVs) | Loaded once into pandas; **typed tools** (`search_products`, `get_order_status`, …) instead of free SQL | Tens of rows. Typed tools let the business rules live in tested Python (availability, promotion vs PIX price, identity check before showing an order) instead of trusting the model to write correct queries, and keep private data from leaking through arbitrary queries. |
| Prompt strategy / persona | One system prompt (English, for reviewers) defining **Melodia**, rules taken from the manual §7: tone, "never state price/stock/dates without the system", promotion display, accessories redirect, order verification. Tool descriptions say *when* to use each tool | The manual already defines the persona and service rules; the prompt turns them into instructions. Facts are never in the prompt: they come from tools, so prices and policies stay in one source of truth. |
| Agent language | Brazilian Portuguese with customers; code and docs in English | Customers and data are Brazilian; the brief requires English deliverables. |
| Interface | Terminal chat (`uv run emporio`, `rich`) | The brief asks for the simplest interface; a CLI is enough to show behaviour and is what a WhatsApp webhook would wrap. `--show-tools` makes the agent's decisions visible. |
| Conversation history | Full message list per session in **SQLite** (`.sessions/conversations.db`), resumed with `--session` | A support chat is multi-turn ("o pedido é o 7" only makes sense after the previous question). SQLite is in the standard library, needs no server and survives restarts. In production the session id would be the customer's phone number. |

## Data handling

Details in [`docs/data_analysis.md`](docs/data_analysis.md). Each issue found and what the code does about it:

| Issue | Handling |
|---|---|
| `specs` stored as a JSON string | Parsed into a dict on load (`data_store.py`) |
| Product `active` with 0 stock (96); `discontinued` with stock (136); `coming_soon` with stock (130) | Availability is derived in one place: available only if `active` **and** stock > 0; otherwise `out_of_stock`, `discontinued` or `coming_soon`, and the prompt asks for alternatives |
| Promotions with no dates, some products with several | Only `is_active = 1` counts; if a product ever had two active, the larger discount wins (no stacking, §6.2); PIX 5% is not applied on top of a promotion |
| Order totals differ from the sum of items (orders 3, 20) | `total_brl` is reported as the amount paid; never recomputed |
| No real delivery date | `estimated_delivery` is used as the receipt date for return deadlines, and the agent says so |
| Shipped order past its estimated delivery (8) | Tool returns `delayed: true` and days late |
| Duplicated e-mail between customers; similar names | Identity check is per order: order number + e-mail or phone of *that* order's customer |
| Phone formats vary | Compared by digits only, last 8 digits |
| Accents and plurals in searches ("violões" vs "violao") | Accent-free search text plus a light stemmer |
| Two phones / two e-mail spellings in the manual | Curated Markdown keeps both phones with their stated purpose (§7 WhatsApp channel vs main line) and the accent-free e-mail |
| PDF text extraction loses structure | Curated `data/processed/policies.md`, validated against the PDF (all numbers present) |

## Interaction examples

Conversations live in [`examples/`](examples/). _TODO:_ list each scenario and what it demonstrates.

## Assumptions

1. **Today's date is the real current date** (Campo Grande time, UTC-4). Orders run up to Mar/2026, so return windows for those orders have expired; the agent explains that instead of pretending the date is earlier. A fixed reference date would be a one-line change (`now` is a parameter of the tools).
2. **Receipt date = estimated delivery date** for delivered orders, since there is no real delivery date.
3. **Identity check before order data (LGPD, §9):** order number + the e-mail or phone used in the purchase. A failed check returns the same message whether the order exists or not, so order numbers cannot be probed.
4. **"Available"** means `status = active` and stock > 0. Discontinued and coming-soon items are mentioned as such, never offered as available.
5. **Prices:** list price, plus original price / discount % / final price when a promotion is active; the 5% PIX price only for products without a promotion.
6. **Holidays** are not listed in the manual, so opening hours ignore them and the agent adds that the store is closed on holidays.
7. **Out of scope:** accessories are politely declined (§7.1); unrelated topics get a polite refusal and a return to store topics. Cancellations, refunds and complaints are not executed by the agent: it explains the policy and points to the human team.

## Known limitations and next steps

- **No real actions**: the agent only reads data. Next: tools to open a return/complaint ticket and hand off to a human, with confirmation.
- **Free-tier limits**: Gemini's free tier has daily request quotas (only ~20/day for `gemini-3.5-flash`, which is why the default is the lite model) and may use prompts for training; fine for fictional data, not for real customers (production: paid tier). Answers with tools take a few seconds.
- **Provider-specific APIs unused**: going through the OpenAI-compatible layer keeps the code portable but gives up native features (e.g. Gemini's context caching).
- **Evaluation**: tool logic and retrieval are unit-tested, but answer quality was checked by reading the example conversations. Next: an eval set of real questions with expected tools and facts, run on every prompt change.
- **Lexical retrieval** fails on wording far from the manual's; the synonym list is hand-made. With a larger manual: hybrid BM25 + embeddings.
- **Static data**: CSVs loaded at start-up. In production, read-only access to the store's database or API.
- **History grows without limit** per session; fine for a chat, but long sessions would need truncation or summarization.
- **Interface**: CLI only. Next: a WhatsApp/HTTP webhook (FastAPI) that calls `Agent.reply()` with the phone number as session id.

## Use of coding assistants

**Claude Code** (Anthropic's CLI agent) was used throughout, as a pair programmer:

- **Reading the brief and data**: summarizing the PDF brief, profiling the CSVs and listing data issues (`docs/data_analysis.md`), which I reviewed and turned into decisions.
- **Planning**: discussing options (framework vs hand-written loop, embeddings vs BM25, model provider) before writing code; decisions and their reasons were recorded (ADRs, this README), including the change of provider when the first choice turned out to need a paid key.
- **Implementation in small steps**: one feature per commit (data layer → retrieval → tools → agent → CLI → examples → docs), each with tests run before committing.
- **Review**: I read every change, asked for explanations of parts I did not know well and kept a study guide of the concepts used.

The design decisions, scope cuts ("simplest way possible") and final review were mine.
