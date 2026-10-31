"""The agent loop with a scripted model in place of Gemini: no key, no network. Skipped without LangGraph."""

import pytest

pytest.importorskip("langgraph")

from langchain_core.messages import AIMessage  # noqa: E402
from langchain_core.messages.tool import tool_call  # noqa: E402

from emporio.agent.guard import FALLBACK  # noqa: E402
from emporio.agent.runner import Agent  # noqa: E402
from emporio.safety import MAX_TOOL_ROUNDS, STUCK, TOO_LONG  # noqa: E402


class ScriptedModel:
    """Returns the scripted replies in order, then keeps asking for the same tool forever."""

    def __init__(self, *replies: str) -> None:
        self.replies, self.calls = list(replies), 0

    def invoke(self, messages):
        self.calls += 1
        if self.replies:
            return AIMessage(content=self.replies.pop(0))
        call = tool_call(name="get_store_policy", args={"topic": "horario"}, id=f"call-{self.calls}")
        return AIMessage(content="", tool_calls=[call])


def ask(tmp_path, model, text: str):
    return Agent(db_path=tmp_path / "conversations.sqlite", llm=model).reply("test", None, text)


def test_a_model_stuck_on_tools_is_stopped(tmp_path):
    model = ScriptedModel()
    turn = ask(tmp_path, model, "Que horas vocês abrem?")
    assert turn.text == STUCK
    assert model.calls == MAX_TOOL_ROUNDS and len(turn.tool_calls) == MAX_TOOL_ROUNDS


def test_a_long_message_never_reaches_the_model(tmp_path):
    model = ScriptedModel()
    assert ask(tmp_path, model, "a" * 2001).text == TOO_LONG and model.calls == 0


def test_an_invented_price_goes_back_once_then_is_replaced(tmp_path):
    model = ScriptedModel("Sai por R$ 999,00.", "Fica R$ 888,00.")
    assert ask(tmp_path, model, "Quanto custa o GD20?").text == FALLBACK and model.calls == 2


def test_a_grounded_answer_passes(tmp_path):
    model = ScriptedModel("Oi! Sou o Tom. Em que posso ajudar?")
    assert ask(tmp_path, model, "Oi").text == "Oi! Sou o Tom. Em que posso ajudar?" and model.calls == 1
