"""Tom in a browser chat window, served on this machine only.

    uv run python -m emporio.web          # Windows: double-click abrir-chat.bat

A demo of how the agent would sit on the store's website. The page is web/chat.html, one file with no
build step. Unlike the webhook in emporio/api.py, the widget picks who the customer is and what time the
store clock shows, so the conversation history lives in memory and is gone when the server stops.

It listens on 127.0.0.1, refuses any other Host header (DNS rebinding) and any POST without the widget's
own header (another site cannot send one without a CORS preflight, and there is no CORS here).
"""

import argparse
import logging
import os
import socket
import sys
import threading
import time
import webbrowser
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from emporio import clock
from emporio.agent import DEFAULT_MODEL
from emporio.catalog import ROOT
from emporio.clock import WEEKDAYS, fmt_moment
from emporio.hours import StoreStatus, store_status
from emporio.safety import API_MAX_CHARS, protect_logs, redact

PAGE = ROOT / "web" / "chat.html"
HOST, PORT = "127.0.0.1", 8000
WIDGET_HEADER = "X-Tom-Widget"

# The real clock, the day after the last order in the data (the recordings use it) and Good Friday night.
Clock = Literal["agora", "2026-03-23T10:30", "2026-04-03T19:40"]
CLOCKS: dict[str, datetime | None] = {
    "agora": None,
    "2026-03-23T10:30": datetime(2026, 3, 23, 10, 30),
    "2026-04-03T19:40": datetime(2026, 4, 3, 19, 40),
}
PAGE_HEADERS = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": (
        "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; "
        "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    ),
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
}

log = logging.getLogger("emporio.web")

app = FastAPI(title="Empório da Música - Tom no navegador", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])


class ChatMessage(BaseModel):
    conversation: str = Field(pattern=r"^[A-Za-z0-9-]{8,64}$", description="one id per conversation in the widget")
    phone: str | None = Field(default=None, max_length=32, description="who the customer is, as a login would")
    text: str = Field(min_length=1, max_length=API_MAX_CHARS)
    clock: Clock = "agora"


class StoreLine(BaseModel):
    clock: str  # "segunda-feira, 23/03/2026, 10:30"
    open: bool
    team: str  # "Equipe online até 18:00" / "Equipe volta terça 03/11, 09:00"


class ChatReply(StoreLine):
    text: str
    tools: list[str]
    models: list[str]
    seconds: float


@lru_cache(maxsize=1)
def agent():
    from emporio.agent.runner import Agent

    return Agent(db_path=Path(":memory:"))  # nothing about the conversation is written to disk


def team_line(status: StoreStatus) -> str:
    if status.is_open:
        return f"Equipe online até {status.closes_at:%H:%M}"
    reopen = status.next_opening
    return f"Equipe volta {WEEKDAYS[reopen.weekday()].split('-')[0]} {reopen:%d/%m}, {reopen:%H:%M}"


def store_line() -> dict:
    status = store_status(clock.now())
    return {"clock": fmt_moment(status.at), "open": status.is_open, "team": team_line(status)}


@app.get("/", include_in_schema=False)
def page() -> FileResponse:
    return FileResponse(PAGE, media_type="text/html; charset=utf-8", headers=PAGE_HEADERS)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/chat/info")
def info(clock_name: Annotated[Clock, Query(alias="clock")] = "agora") -> dict:
    with clock.frozen_at(CLOCKS[clock_name]):
        line = store_line()
    return {**line, "model": os.getenv("LLM_MODEL", DEFAULT_MODEL).split(":")[-1]}


@app.post("/chat/messages", response_model=ChatReply)
def chat(message: ChatMessage, widget: Annotated[str | None, Header(alias=WIDGET_HEADER)] = None) -> dict:
    if widget != "1":
        raise HTTPException(status_code=403, detail="use the chat window")
    from emporio.agent.runner import model_failure

    started = time.perf_counter()
    with clock.frozen_at(CLOCKS[message.clock]):
        try:
            bot = agent()
            turn = bot.reply(f"web-{message.conversation}", message.phone, message.text)
        except Exception as error:  # every model in the chain failed
            log.warning("no reply: %s", redact(f"{type(error).__name__}: {error}")[:300])
            raise HTTPException(status_code=503, detail=model_failure(error)) from None
        line = store_line()
    return {
        **line,
        "text": turn.text,
        "tools": list(dict.fromkeys(name for name, _ in turn.tool_calls)),
        "models": turn.models,
        "seconds": round(time.perf_counter() - started, 1),
    }


def port_in_use(port: int) -> bool:
    with socket.socket() as probe:
        return probe.connect_ex((HOST, port)) == 0


def main() -> None:
    load_dotenv()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Tom in a browser chat window, served on this machine only.")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--no-browser", action="store_true", help="do not open the browser")
    args = parser.parse_args()
    url = f"http://{HOST}:{args.port}/"

    model = os.getenv("LLM_MODEL", DEFAULT_MODEL)
    if model.startswith("google_genai:") and not (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
        sys.exit("GOOGLE_API_KEY is not set. Copy .env.example to .env and paste a key (see the README).")
    if port_in_use(args.port):
        print(f"A porta {args.port} já está em uso: se for o chat do Tom, ele está em {url}")
        if not args.no_browser:
            webbrowser.open(url)
        return

    tickets = ROOT / "var" / "web"  # tickets opened in the demo, numbered from 001 on every start
    os.environ["EMPORIO_VAR_DIR"] = str(tickets)
    (tickets / "handoffs.jsonl").unlink(missing_ok=True)

    logging.basicConfig(level=logging.WARNING, format="  [%(name)s] %(message)s")
    protect_logs()
    print(f"Tom no navegador: {url}")
    print("Para desligar, feche esta janela ou aperte Ctrl+C.")
    if not args.no_browser:
        threading.Timer(1.5, webbrowser.open, args=(url,)).start()

    import uvicorn

    uvicorn.run(app, host=HOST, port=args.port, log_config=None, log_level="warning")


if __name__ == "__main__":
    main()
