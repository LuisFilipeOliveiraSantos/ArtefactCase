# ADR 002 — Switch the LLM to Google Gemini (free tier) through an OpenAI-compatible client

- **Status:** accepted (supersedes [ADR 001](001-llm-provider.md))
- **Date:** 2026-11-03

## Context

ADR 001 chose Claude through the Anthropic SDK. When it was time to run the agent, it became clear that the
Anthropic API is prepaid only: a Claude subscription does not include API access, and credits must be bought
up front. For a prototype in a hiring case, this has two costs:

- the author pays to develop and generate the examples;
- **every reviewer who wants to run the project also needs a paid key**, which is a real barrier.

The brief allows a paid or free model, local or API.

## Decision

- Default model: **Google Gemini `gemini-3.5-flash`** on the **free tier** (key from Google AI Studio, no
  credit card).
- The agent talks to it through the **OpenAI-compatible Chat Completions API** using the official `openai`
  Python SDK, pointed at Gemini's OpenAI-compatible endpoint.
- Provider, key and model are configurable in `.env` (`EMPORIO_BASE_URL`, `EMPORIO_API_KEY`, `EMPORIO_MODEL`),
  so the same code runs on Groq, a local Ollama model or OpenAI without code changes.

## Reasons

1. **Zero cost for the author and for reviewers.** Anyone can clone the repo, create a free key in a minute and
   run it.
2. **Good tool use and Portuguese.** Tested on the case scenarios: it chains tools (order lookup + return policy),
   follows the persona and answers in natural Brazilian Portuguese.
3. **Provider independence almost for free.** The OpenAI-compatible format is the common denominator of most
   providers, so the "multi-provider" item that ADR 001 left as a next step is covered by configuration.
4. **Small change.** Only the request/response shape in the agent loop changed; data, retrieval, tools, CLI
   and history were untouched, because the tools were already provider-neutral.

## Trade-offs

- Free-tier **rate limits** (requests per minute/day). The client retries rate-limit errors with backoff; for
  a demo this is enough.
- Free-tier prompts may be used by Google to improve its products. Acceptable for fictional case data; not for
  real customer data (production would use a paid tier or another provider).
- `gemini-3.5-flash` is slower per answer (several seconds with tool calls) than smaller models.
- Gemini 3 attaches "thought signatures" to tool calls that must be sent back unchanged; the loop stores each
  assistant message exactly as returned, which satisfies this.
