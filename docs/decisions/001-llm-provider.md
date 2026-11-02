# ADR 001 — LLM provider: Claude (Anthropic API)

- **Status:** accepted
- **Date:** 2026-11-02

## Context

The agent must decide on its own when to look up store data (prices, stock, orders) and when to look up
store policies, and then combine both in a single answer. The hardest scenario in the brief — *"I regret my
purchase, can I return my order?"* — requires calling two tools, comparing dates and applying the right rule.
The answers must be in Brazilian Portuguese with the store's tone ("informal but professional").

The brief leaves the model and provider open (paid or free, local or API) and asks for the choice to be justified.

## Decision

Use **Claude through the official Anthropic Python SDK** (`anthropic`).

- Default model: `claude-opus-5-5` with reasoning effort `low` (fast and cheap enough for a chat).
- The model is configurable through `EMPORIO_MODEL` in `.env`, so a cheaper model such as
  `claude-haiku-5-5` can be used without code changes.

## Reasons

1. **Reliable tool use.** The agent's quality depends on picking the right tool with the right arguments and
   chaining several calls. A model that picks the wrong tool or miscounts days breaks exactly the
   non-trivial scenario the case highlights.
2. **Good Brazilian Portuguese and tone control.** The persona ("a friend who knows music") and the policy
   rules must come across naturally in Portuguese.
3. **Simple official SDK.** Tool use is a first-class feature of the Messages API, so a hand-written agent loop
   stays short and readable, with no framework needed — in line with "solve it in the simplest way possible".
4. **Negligible cost for a prototype.** Each conversation costs cents.
5. **Consistency with the development workflow.** Claude Code is the coding assistant used in this project
   (documented in the README), so the same model family is used to build and to run the agent.

## Alternatives considered

| Option | Pros | Why not chosen |
|---|---|---|
| OpenAI (GPT) | Mature function calling | Same trade-offs as Claude, no clear advantage here |
| Google Gemini | Free tier: reviewers could run it at no cost | Would add a second SDK to learn under a tight deadline |
| Local model via Ollama | Free, private, offline | Weak tool use in small models; heavier setup for reviewers |
| LiteLLM / LangChain (multi-provider) | Easy provider switching | Extra abstraction and dependencies that hide the agent loop, against "simplest way possible" |

## Consequences

- Running the agent requires an Anthropic API key with credits (`ANTHROPIC_API_KEY`). This is stated in the
  README setup instructions.
- Supporting other providers is a possible next step: the agent loop would talk to a small client interface
  instead of the SDK directly, with one adapter per provider (an OpenAI-compatible adapter would also cover
  Gemini and Ollama). Listed under "next steps" in the README.
