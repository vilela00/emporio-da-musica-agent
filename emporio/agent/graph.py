"""LangGraph wiring: agent <-> tools, and the grounding guard before anything reaches the customer.

    START -> agent -> (tool calls?) -> tools -> agent ... -> guard -> END
                                                   guard -> agent (once, if something is ungrounded)

The agent stops asking the model after MAX_TOOL_ROUNDS tool rounds for one message (emporio.safety).
"""

import logging
import os

from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, AnyMessage, RemoveMessage, SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime

from emporio import clock
from emporio.agent.guard import FALLBACK, retry_note, ungrounded
from emporio.agent.prompts import Session, system_prompt
from emporio.agent.tools import TOOLS
from emporio.catalog import get_store
from emporio.safety import MAX_TOOL_ROUNDS, STUCK, tool_rounds

log = logging.getLogger("emporio.guard")

DEFAULT_MODEL = "google_genai:gemini-3.8-flash"
# Other free-tier models, tried in order when the primary fails: 503 "high demand" on the first
# evaluation run, then 429 when its free daily quota (20 requests per model, Oct 2026) ran out.
# Override with LLM_FALLBACK_MODELS; leave it empty to disable.
DEFAULT_FALLBACKS = (
    "google_genai:gemini-3.6-flash,google_genai:gemini-3.5-flash-lite,google_genai:gemini-3.1-flash-lite"
)
HISTORY_TURNS = 12


class State(MessagesState):
    guard_note: str | None
    guard_retries: int


def text_of(message: AnyMessage) -> str:
    return str(message.text)  # Gemini 3 returns content blocks; .text joins the text parts


def recent(messages: list[AnyMessage]) -> list[AnyMessage]:
    """The last HISTORY_TURNS customer turns, cut at a human message so no tool result loses its call."""
    starts = [i for i, m in enumerate(messages) if m.type == "human"]
    return messages[starts[-HISTORY_TURNS] :] if len(starts) > HISTORY_TURNS else messages


def chat_model(name: str, retries: int):
    # max_retries=1 means a single attempt in the Google SDK. Without a timeout, a request to an
    # overloaded model hung for minutes (491 s in one evaluation run) before the fallback kicked in.
    options: dict = {"max_retries": retries, "timeout": float(os.getenv("LLM_TIMEOUT", "30"))}
    if name.startswith("google_genai:"):
        # Gemini 3: keep the default temperature (1.0); lower values are known to cause loops.
        options["thinking_level"] = os.getenv("LLM_THINKING", "low")
    return init_chat_model(name, **options).bind_tools(TOOLS)


def make_llm():
    primary = os.getenv("LLM_MODEL", DEFAULT_MODEL)
    fallbacks = [
        name.strip()
        for name in os.getenv("LLM_FALLBACK_MODELS", DEFAULT_FALLBACKS).split(",")
        if name.strip() and name.strip() != primary
    ]
    llm = chat_model(primary, retries=1 if fallbacks else 3)
    return llm.with_fallbacks([chat_model(name, retries=2) for name in fallbacks]) if fallbacks else llm


def build_graph(checkpointer=None, llm=None):
    llm = llm or make_llm()

    def agent(state: State, runtime: Runtime[Session]) -> dict:
        if tool_rounds(state["messages"]) >= MAX_TOOL_ROUNDS:
            log.warning("%d tool rounds for one message: stopping", MAX_TOOL_ROUNDS)
            return {"messages": [AIMessage(content=STUCK)]}
        session = runtime.context or Session()
        system = system_prompt(get_store(), session, clock.now(), state.get("guard_note"))
        reply = llm.invoke([SystemMessage(content=system), *recent(state["messages"])])
        return {"messages": [reply]}

    def guard(state: State) -> dict:
        last = state["messages"][-1]
        evidence = [text_of(m) for m in state["messages"][:-1] if m.type in ("human", "tool")]
        issues = ungrounded(text_of(last), evidence)
        if not issues:
            return {"guard_note": None, "guard_retries": 0}
        if state.get("guard_retries", 0) < 1:
            log.info("not grounded %s: sending the answer back once", issues)
            return {
                "messages": [RemoveMessage(id=last.id)],
                "guard_note": retry_note(issues),
                "guard_retries": 1,
            }
        log.warning("not grounded %s after the retry: safe fallback", issues)
        return {
            "messages": [RemoveMessage(id=last.id), AIMessage(content=FALLBACK)],
            "guard_note": None,
            "guard_retries": 0,
        }

    def after_agent(state: State) -> str:
        return "tools" if getattr(state["messages"][-1], "tool_calls", None) else "guard"

    def after_guard(state: State) -> str:
        return "agent" if state.get("guard_note") else END

    builder = StateGraph(State, context_schema=Session)
    builder.add_node("agent", agent)
    builder.add_node("tools", ToolNode(TOOLS, handle_tool_errors=True))
    builder.add_node("guard", guard)
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", after_agent, ["tools", "guard"])
    builder.add_edge("tools", "agent")
    builder.add_conditional_edges("guard", after_guard, ["agent", END])
    return builder.compile(checkpointer=checkpointer)
