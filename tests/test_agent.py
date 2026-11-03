"""Agent loop tests with a scripted fake client (no API key or network needed)."""

import json
from types import SimpleNamespace

from emporio_agent import agent as agent_module
from emporio_agent.agent import FALLBACK_REPLY, Agent


class Block(SimpleNamespace):
    def to_dict(self):
        return dict(vars(self))


def text(t):
    return Block(type="text", text=t)


def tool_use(id_, name, input_):
    return Block(type="tool_use", id=id_, name=name, input=input_)


class FakeClient:
    """Returns the scripted responses in order and records every request."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []
        self.messages = self

    def create(self, **kwargs):
        self.requests.append(json.loads(json.dumps(kwargs, default=str)))  # snapshot
        content, stop = self.responses.pop(0)
        return SimpleNamespace(content=content, stop_reason=stop)


def test_plain_answer_without_tools():
    client = FakeClient(([text("Oi! Tudo bem?")], "end_turn"))
    agent = Agent(client=client)

    reply, calls = agent.reply("Olá")

    assert reply == "Oi! Tudo bem?"
    assert calls == []
    assert [m["role"] for m in agent.messages] == ["user", "assistant"]
    request = client.requests[0]
    assert request["model"] == agent.model
    assert {t["name"] for t in request["tools"]} >= {"search_products", "search_policies"}


def test_tool_round_trip_runs_tools_and_feeds_results_back():
    client = FakeClient(
        (
            [
                tool_use("t1", "search_products", {"query": "Takamine GD20", "only_available": False}),
                tool_use("t2", "get_store_status", {}),
            ],
            "tool_use",
        ),
        ([text("O Takamine GD20 custa ...")], "end_turn"),
    )
    agent = Agent(client=client)

    reply, calls = agent.reply("Quanto custa o Takamine GD20?")

    assert reply.startswith("O Takamine GD20")
    assert [c.name for c in calls] == ["search_products", "get_store_status"]
    assert calls[0].result["total_found"] >= 1

    # Both results go back in ONE user message, matched by tool_use_id.
    tool_results = client.requests[1]["messages"][-1]
    assert tool_results["role"] == "user"
    assert [r["tool_use_id"] for r in tool_results["content"]] == ["t1", "t2"]
    assert "Takamine" in tool_results["content"][0]["content"]


def test_tool_errors_are_flagged_not_raised():
    client = FakeClient(
        ([tool_use("t1", "get_order_status", {"order_id": 9999, "email_or_phone": "x@y.com"})], "tool_use"),
        ([text("Não encontrei esse pedido.")], "end_turn"),
    )
    agent = Agent(client=client)

    agent.reply("Cadê meu pedido 9999?")

    result = client.requests[1]["messages"][-1]["content"][0]
    assert result["is_error"] is True


def test_history_carries_over_between_turns():
    client = FakeClient(([text("Oi, Ana!")], "end_turn"), ([text("Claro!")], "end_turn"))
    agent = Agent(client=client)

    agent.reply("Sou a Ana")
    agent.reply("Pode me ajudar?")

    second = client.requests[1]["messages"]
    assert [m["role"] for m in second] == ["user", "assistant", "user"]
    assert second[0]["content"] == "Sou a Ana"


def test_stops_after_max_tool_rounds(monkeypatch):
    monkeypatch.setattr(agent_module, "MAX_TOOL_ROUNDS", 2)
    loop = ([tool_use("t", "get_store_status", {})], "tool_use")
    client = FakeClient(loop, loop)
    agent = Agent(client=client)

    reply, calls = agent.reply("?")

    assert reply == FALLBACK_REPLY
    assert len(calls) == 2
    assert agent.messages[-1]["role"] == "assistant"  # history stays valid for the next turn
