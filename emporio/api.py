"""HTTP entry point with the shape of a messaging webhook: who sent it and what they wrote.

    uv run uvicorn emporio.api:app --port 8000

A real WhatsApp Cloud API integration would add the verify-token handshake, the signature check and
the unwrapping of Meta's payload; the agent only needs the two fields below.
"""

from functools import lru_cache

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from emporio.safety import API_MAX_CHARS

load_dotenv()

app = FastAPI(title="Empório da Música - Tom", version="0.1.0")


class IncomingMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    sender: str = Field(
        alias="from",
        min_length=1,
        max_length=32,
        description="Customer's WhatsApp number, as the channel delivers it",
    )
    text: str = Field(min_length=1, max_length=API_MAX_CHARS)


class OutgoingMessage(BaseModel):
    to: str
    text: str
    tools_used: list[str]


@lru_cache(maxsize=1)
def agent():
    from emporio.agent.runner import Agent

    return Agent()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/whatsapp/messages", response_model=OutgoingMessage)
def receive(message: IncomingMessage) -> OutgoingMessage:
    from emporio.agent.runner import model_failure

    bot = agent()
    try:
        turn = bot.reply(bot.thread_for(message.sender), message.sender, message.text)
    except Exception as error:  # every model in the chain failed
        raise HTTPException(status_code=503, detail=model_failure(error)) from error
    return OutgoingMessage(to=message.sender, text=turn.text, tools_used=[name for name, _ in turn.tool_calls])
