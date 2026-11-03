from emporio_agent.history import HistoryStore


def test_save_load_and_delete(tmp_path):
    store = HistoryStore(tmp_path / "h.db")
    messages = [
        {"role": "user", "content": "Olá, ação!"},
        {"role": "assistant", "content": [{"type": "text", "text": "Oi!"}]},
    ]

    assert store.load("ana") == []
    store.save("ana", messages)
    assert store.load("ana") == messages

    store.save("ana", messages + [{"role": "user", "content": "de novo"}])
    assert len(HistoryStore(tmp_path / "h.db").load("ana")) == 3  # survives a new store (restart)

    store.delete("ana")
    assert store.load("ana") == []


def test_sessions_are_isolated(tmp_path):
    store = HistoryStore(tmp_path / "h.db")
    store.save("a", [{"role": "user", "content": "A"}])
    store.save("b", [{"role": "user", "content": "B"}])
    assert store.load("a")[0]["content"] == "A"
    assert store.load("b")[0]["content"] == "B"
