"""Terminal chat with the agent.

    uv run emporio                     # new conversation in session "default"
    uv run emporio --session ana       # resume (or start) the conversation "ana"
    uv run emporio --show-tools        # also print the tool calls behind each answer

Commands inside the chat: /sair (quit), /nova (forget this session's history).
"""

import argparse
import json
import os

import openai
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown

from emporio_agent.agent import Agent, ToolCall
from emporio_agent.history import HistoryStore

console = Console()


def print_tool_calls(calls: list[ToolCall]) -> None:
    for call in calls:
        args = json.dumps(call.arguments, ensure_ascii=False)
        console.print(f"  [dim]🔧 {call.name}({args})[/dim]")


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Chat with the Empório da Música assistant.")
    parser.add_argument("--session", default="default", help="conversation id to resume or create")
    parser.add_argument("--show-tools", action="store_true", help="print the tools called for each answer")
    args = parser.parse_args()

    if not (os.getenv("GEMINI_API_KEY") or os.getenv("EMPORIO_API_KEY")):
        console.print("[red]GEMINI_API_KEY is not set. Copy .env.example to .env and fill it in.[/red]")
        raise SystemExit(1)

    store = HistoryStore()
    agent = Agent(messages=store.load(args.session))

    console.print("[bold]Empório da Música[/bold] — assistente virtual. Digite /sair para sair, /nova para recomeçar.")
    if agent.messages:
        console.print(f"[dim](continuando a conversa '{args.session}')[/dim]")

    while True:
        try:
            text = console.input("\n[bold cyan]Você:[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            continue
        if text == "/sair":
            break
        if text == "/nova":
            agent.messages.clear()
            store.delete(args.session)
            console.print("[dim](histórico apagado)[/dim]")
            continue

        size = len(agent.messages)
        try:
            with console.status("digitando..."):
                reply, calls = agent.reply(text)
        except openai.AuthenticationError:
            console.print("[red]The API key was rejected (see .env.example).[/red]")
            del agent.messages[size:]  # drop the unanswered turn
            break
        except openai.APIError as exc:
            console.print(f"[red]API error: {exc}. Try again.[/red]")
            del agent.messages[size:]
            continue

        if args.show_tools:
            print_tool_calls(calls)
        console.print("[bold green]Melodia:[/bold green]", Markdown(reply))
        store.save(args.session, agent.messages)


if __name__ == "__main__":
    main()
