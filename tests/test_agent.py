"""Agent loop tests with a scripted fake client (no API key or network needed)."""

import json
from types import SimpleNamespace

from emporio_agent import agent as agent_module
from emporio_agent.agent import FALLBACK_REPLY, Agent


class Message(SimpleNamespace):
    def model_dump(self, exclude_none=False):
        data = {"role": "assistant", "content": self.content}
        if self.tool_calls:
            data["tool_calls"] = [
                {"id": c.id, "type": "function", "function": {"name": c.function.name, "arguments": c.function.arguments}}
                for c in self.tool_calls
            ]
        return {k: v for k, v in data.items() if v is not None or not exclude_none}


def text(t):
    return Message(content=t, tool_calls=None)


def tools(*calls):
    """calls: (id, name, arguments dict or raw string)"""
    return Message(
        content=None,
        tool_calls=[
            SimpleNamespace(
                id=id_,
                function=SimpleNamespace(name=name, arguments=args if isinstance(args, str) else json.dumps(args)),
            )
            for id_, name, args in calls
        ],
    )


class FakeClient:
    """Returns the scripted messages in order and records every request."""

    def __init__(self, *messages):
        self.scripted = list(messages)
        self.requests = []
        self.chat = SimpleNamespace(completions=self)

    def create(self, **kwargs):
        self.requests.append(json.loads(json.dumps(kwargs, default=str)))  # snapshot
        return SimpleNamespace(choices=[SimpleNamespace(message=self.scripted.pop(0))])


def test_plain_answer_without_tools():
    client = FakeClient(text("Oi! Tudo bem?"))
    agent = Agent(client=client)

    reply, calls = agent.reply("Olá")

    assert reply == "Oi! Tudo bem?"
    assert calls == []
    assert [m["role"] for m in agent.messages] == ["user", "assistant"]
    request = client.requests[0]
    assert request["model"] == agent.model
    assert request["messages"][0]["role"] == "system"
    assert {t["function"]["name"] for t in request["tools"]} >= {"search_products", "search_policies"}


def test_tool_round_trip_runs_tools_and_feeds_results_back():
    client = FakeClient(
        tools(
            ("t1", "search_products", {"query": "Takamine GD20", "only_available": False}),
            ("t2", "get_store_status", {}),
        ),
        text("O Takamine GD20 custa ..."),
    )
    agent = Agent(client=client)

    reply, calls = agent.reply("Quanto custa o Takamine GD20?")

    assert reply.startswith("O Takamine GD20")
    assert [c.name for c in calls] == ["search_products", "get_store_status"]
    assert calls[0].result["total_found"] >= 1

    # One tool message per call, matched by tool_call_id, after the assistant message.
    sent = client.requests[1]["messages"]
    assert [m["role"] for m in sent[-3:]] == ["assistant", "tool", "tool"]
    assert [m["tool_call_id"] for m in sent[-2:]] == ["t1", "t2"]
    assert "Takamine" in sent[-2]["content"]


def test_invalid_tool_arguments_become_an_error_result():
    client = FakeClient(tools(("t1", "search_products", "{not json")), text("Pode repetir?"))
    agent = Agent(client=client)

    _, calls = agent.reply("?")

    assert "error" in calls[0].result
    assert client.requests[1]["messages"][-1]["role"] == "tool"


def test_history_carries_over_between_turns():
    client = FakeClient(text("Oi, Ana!"), text("Claro!"))
    agent = Agent(client=client)

    agent.reply("Sou a Ana")
    agent.reply("Pode me ajudar?")

    second = client.requests[1]["messages"]
    assert [m["role"] for m in second] == ["system", "user", "assistant", "user"]
    assert second[1]["content"] == "Sou a Ana"


def test_stops_after_max_tool_rounds(monkeypatch):
    monkeypatch.setattr(agent_module, "MAX_TOOL_ROUNDS", 2)
    client = FakeClient(tools(("t", "get_store_status", {})), tools(("t", "get_store_status", {})))
    agent = Agent(client=client)

    reply, calls = agent.reply("?")

    assert reply == FALLBACK_REPLY
    assert len(calls) == 2
    assert agent.messages[-1]["role"] == "assistant"  # history stays valid for the next turn


def test_prompt_asks_for_installment_tiers_without_hardcoding_them():
    from emporio_agent.agent import SYSTEM_PROMPT

    assert "every tier of the installment rules" in SYSTEM_PROMPT
    assert "R$ 80" not in SYSTEM_PROMPT  # the numbers come from the manual via search_policies
