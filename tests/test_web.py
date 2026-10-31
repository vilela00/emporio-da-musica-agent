"""The browser demo's server, with a scripted model in place of Gemini. Skipped without FastAPI and LangGraph."""

from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("langgraph")

from fastapi.testclient import TestClient  # noqa: E402
from langchain_core.messages import AIMessage  # noqa: E402
from langchain_core.messages.tool import tool_call  # noqa: E402

from emporio import web  # noqa: E402
from emporio.agent.runner import Agent  # noqa: E402

WIDGET = {"X-Tom-Widget": "1"}


class LooksUpOrdersThenAnswers:
    """Asks for the caller's orders once, then answers; keeps what it was shown."""

    def __init__(self) -> None:
        self.prompts: list[str] = []
        self.tool_outputs: list[str] = []

    def invoke(self, messages):
        self.prompts.append(messages[0].content)
        if messages[-1].type == "tool":
            self.tool_outputs.append(messages[-1].content)
            return AIMessage(content="Prazos conferidos.")
        return AIMessage(content="", tool_calls=[tool_call(name="get_my_orders", args={}, id="call-1")])


@pytest.fixture
def model(monkeypatch):
    model = LooksUpOrdersThenAnswers()
    bot = Agent(db_path=Path(":memory:"), llm=model)
    monkeypatch.setattr(web, "agent", lambda: bot)
    return model


@pytest.fixture
def client():
    return TestClient(web.app, base_url="http://127.0.0.1")


def message(**changes) -> dict:
    base = {"conversation": "test-conversation", "phone": "+55 67 99789-0123", "text": "Meus prazos?"}
    return {**base, "clock": "2026-03-23T10:30", **changes}


def test_page_is_served_with_a_strict_policy(client):
    response = client.get("/")
    assert response.status_code == 200 and "Converse com o Tom" in response.text
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_only_the_widget_on_this_machine_gets_answers(client, model):
    assert client.post("/chat/messages", json=message()).status_code == 403
    elsewhere = TestClient(web.app, base_url="http://tom.attacker.example")
    assert elsewhere.post("/chat/messages", json=message(), headers=WIDGET).status_code == 400
    assert model.prompts == []


def test_chosen_store_clock_reaches_the_prompt_and_the_tools(client, model):
    reply = client.post("/chat/messages", json=message(), headers=WIDGET).json()
    assert reply["text"] == "Prazos conferidos." and reply["tools"] == ["get_my_orders"]
    assert reply["open"] is True and reply["team"] == "Equipe online até 18:00"
    assert "23/03/2026, 10:30" in model.prompts[0]  # graph node thread
    assert "Prazos em 23/03/2026" in model.tool_outputs[0]  # tool thread


def test_info_follows_the_chosen_clock(client):
    info = client.get("/chat/info", params={"clock": "2026-04-03T19:40"}).json()
    assert info["open"] is False and info["team"] == "Equipe volta sábado 04/04, 09:00"
    assert client.get("/chat/info", params={"clock": "2030-01-01T00:00"}).status_code == 422


def test_bad_input_is_refused_before_the_model(client, model):
    for bad in ({"conversation": "x"}, {"text": ""}, {"text": "a" * 4097}, {"clock": "2030-01-01T00:00"}):
        assert client.post("/chat/messages", json=message(**bad), headers=WIDGET).status_code == 422
    assert model.prompts == []
