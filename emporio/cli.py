"""Terminal chat that simulates the store's WhatsApp line.

    uv run python -m emporio.cli --phone "(67) 99789-0123" --trace
"""

import argparse
import logging
import os
import sys

from dotenv import load_dotenv

from emporio.safety import protect_logs, redact


def _short(args: dict) -> str:
    return ", ".join(f"{k}={v!r}" for k, v in args.items())


def main() -> None:
    load_dotenv()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Chat with Tom, the Empório da Música assistant.")
    parser.add_argument("--phone", help="the customer's WhatsApp number; it identifies the customer")
    parser.add_argument("--new", action="store_true", help="start a fresh conversation for this number")
    parser.add_argument("--trace", action="store_true", help="show tool calls and price-guard decisions")
    args = parser.parse_args()

    model = os.getenv("LLM_MODEL", "google_genai:gemini-3.8-flash")
    if model.startswith("google_genai:") and not (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
        sys.exit("GOOGLE_API_KEY is not set. Copy .env.example to .env and paste a free key from "
                 "https://aistudio.google.com/apikey")
    if args.trace:
        logging.basicConfig(level=logging.INFO, format="  [%(name)s] %(message)s")
        logging.getLogger("httpx").setLevel(logging.WARNING)
        protect_logs()

    from emporio.agent.runner import Agent, model_failure  # imported after .env is loaded
    from emporio.catalog import get_store

    agent = Agent()
    thread = agent.thread_for(args.phone, fresh=args.new)
    customer = get_store().customer_by_phone(args.phone)
    who = f"{customer.name}, {customer.city}" if customer else ("número fora do cadastro" if args.phone else "sem número")
    print(f"Empório da Música | WhatsApp simulado | {args.phone or '-'} ({who}) | {model}")
    print("Comandos: /novo recomeça a conversa, /sair encerra.\n")
    while True:
        try:
            text = input("você > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text:
            continue
        if text.lower() in {"/sair", "/exit", "/quit"}:
            break
        if text.lower() == "/novo":
            thread = agent.thread_for(args.phone, fresh=True)
            print("(nova conversa)\n")
            continue
        try:
            turn = agent.reply(thread, args.phone, text)
        except Exception as error:  # every model in the chain failed
            print(f"\n[sem resposta: {model_failure(error)}. Tente de novo mais tarde ou troque LLM_MODEL no .env]\n")
            if args.trace:
                print(f"  [{type(error).__name__}] {redact(str(error))[:300]}")
            continue
        if args.trace:
            for name, call_args in turn.tool_calls:
                print(f"  -> {name}({_short(call_args)})")
        print(f"\nTom > {turn.text}\n")


if __name__ == "__main__":
    main()
