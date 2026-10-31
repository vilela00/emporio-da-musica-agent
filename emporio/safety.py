"""Limits that keep a hostile or broken conversation cheap. Each number has its reason next to it."""

from __future__ import annotations

# Tool rounds the model may take for one customer message before the agent stops asking it.
# The busiest scenario uses three. LangGraph 1.2 defaults to a recursion limit of 10,007 steps, so a
# model stuck calling tools would keep calling, and billing, the API for a long time.
MAX_TOOL_ROUNDS = 6
# Graph steps per message: six rounds of agent + tools, the answer, the guard and one retry fit in 20.
RECURSION_LIMIT = 30

STUCK = (
    "Não consegui fechar essa consulta por aqui. Me diz de novo, em poucas palavras, o que você "
    "precisa? Se preferir, passo o seu caso para a equipe."
)


def tool_rounds(messages) -> int:
    """Model turns that asked for tools since the customer's last message."""
    rounds = 0
    for message in reversed(messages):
        if message.type == "human":
            break
        if message.type == "ai" and getattr(message, "tool_calls", None):
            rounds += 1
    return rounds
