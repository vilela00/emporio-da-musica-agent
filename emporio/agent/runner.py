"""One entry point for the CLI, the API and the evals: send a message, get the reply and the trace."""

import sqlite3
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver

from emporio.agent.graph import build_graph, text_of
from emporio.agent.prompts import Session
from emporio.agent.whatsapp import whatsapp_text
from emporio.catalog import ROOT, phone_digits
from emporio.safety import MAX_MESSAGE_CHARS, RECURSION_LIMIT, TOO_LONG, UNREADABLE, clean_message


def model_failure(error: Exception) -> str:
    """Short Portuguese explanation for when every model in the chain failed."""
    text = str(error)
    if "402" in text or "prepayment" in text.lower():
        return (
            "o saldo pré-pago do projeto no Google AI Studio acabou (créditos do Google Cloud não valem "
            "para a API do Gemini)"
        )
    if "RESOURCE_EXHAUSTED" in text or "429" in text:
        return "a cota diária gratuita dos modelos Gemini acabou (ela renova à meia-noite, horário do Pacífico)"
    if "UNAVAILABLE" in text or "503" in text:
        return "os modelos Gemini estão sobrecarregados agora"
    return f"erro ao chamar o modelo ({type(error).__name__})"


@dataclass
class Turn:
    text: str
    tool_calls: list[tuple[str, dict]] = field(default_factory=list)
    tool_outputs: list[str] = field(default_factory=list)
    models: list[str] = field(default_factory=list)  # which model(s) answered, fallbacks included


class Agent:
    """The graph plus a SQLite checkpointer: one conversation thread per WhatsApp number."""

    def __init__(self, db_path: Path | None = None, llm=None) -> None:
        path = db_path or ROOT / "var" / "conversations.sqlite"
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self.graph = build_graph(SqliteSaver(self._connection), llm=llm)

    @staticmethod
    def thread_for(phone: str | None, fresh: bool = False) -> str:
        base = phone_digits(phone or "") or "anon"
        return f"{base}-{uuid.uuid4().hex[:8]}" if fresh or base == "anon" else base

    def reply(self, thread_id: str, phone: str | None, text: str) -> Turn:
        text = clean_message(text)
        if not text:
            return Turn(text=UNREADABLE)
        if len(text) > MAX_MESSAGE_CHARS:  # answered without calling the model
            return Turn(text=TOO_LONG)
        state = self.graph.invoke(
            {"messages": [HumanMessage(content=text)]},
            config={"configurable": {"thread_id": thread_id}, "recursion_limit": RECURSION_LIMIT},
            context=Session(phone=phone),
        )
        messages = state["messages"]
        start = max(i for i, m in enumerate(messages) if m.type == "human")
        turn = Turn(text=whatsapp_text(text_of(messages[-1])))
        for message in messages[start + 1 :]:
            if message.type == "ai":
                turn.tool_calls += [(c["name"], c["args"]) for c in message.tool_calls or []]
                model = (message.response_metadata or {}).get("model_name")
                if model and model not in turn.models:
                    turn.models.append(model)
            elif message.type == "tool":
                turn.tool_outputs.append(text_of(message))
        return turn
