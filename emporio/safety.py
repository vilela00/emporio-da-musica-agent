"""Limits that keep a hostile or broken conversation cheap, and redaction that keeps secrets out of
anything the app prints or writes. Each number has its reason next to it."""

from __future__ import annotations

import logging
import os
import re

# WhatsApp delivers text messages of up to 4,096 characters, so the API accepts that much; no
# customer question needs more than 2,000. Longer messages get a fixed reply without a model call.
API_MAX_CHARS = 4096
MAX_MESSAGE_CHARS = 2000

# Tool rounds the model may take for one customer message before the agent stops asking it.
# The busiest scenario uses three. LangGraph 1.2 defaults to a recursion limit of 10,007 steps, so a
# model stuck calling tools would keep calling, and billing, the API for a long time.
MAX_TOOL_ROUNDS = 6
# Graph steps per message: six rounds of agent + tools, the answer, the guard and one retry fit in 20.
RECURSION_LIMIT = 30

# Tool arguments come from the model, so they are checked like user input.
MAX_QUOTE_UNITS = 20  # a bigger order is a job for the team
MAX_QUOTE_AMOUNT = 1_000_000
MAX_SUMMARY_CHARS = 600  # a ticket summary is one to three sentences

TOO_LONG = (
    "Sua mensagem ficou longa demais pra eu ler de uma vez. Me manda só o que você precisa, "
    "em uma mensagem mais curta?"
)
UNREADABLE = "Não consegui ler a sua mensagem. Pode escrever de novo?"
STUCK = (
    "Não consegui fechar essa consulta por aqui. Me diz de novo, em poucas palavras, o que você "
    "precisa? Se preferir, passo o seu caso para a equipe."
)


# Characters that render as nothing but still reach the model: zero-width and bidi controls, and the
# Unicode tag block, which can hide a whole instruction inside an innocent-looking message.
# U+200D (zero-width joiner) stays: emoji sequences need it.
_INVISIBLE = re.compile(r"[\u200b\u200c\u2060\ufeff\u202a-\u202e\u2066-\u2069\U000e0000-\U000e007f]")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_message(text: str) -> str:
    """The customer's text without invisible and control characters; newlines and tabs stay."""
    return _CONTROL.sub("", _INVISIBLE.sub("", text)).strip()


def quote_problem(product_ids: list[int] | None, amount: float | None) -> str | None:
    """Why a quote request cannot be priced as asked, or None."""
    if product_ids and len(product_ids) > MAX_QUOTE_UNITS:
        return f"Orçamento por aqui vai até {MAX_QUOTE_UNITS} unidades; para mais, ofereça encaminhar para a equipe."
    if not product_ids and amount is not None and not 0 < amount <= MAX_QUOTE_AMOUNT:
        return "Valor inválido para orçamento: informe um valor positivo em reais."
    return None


def tool_rounds(messages) -> int:
    """Model turns that asked for tools since the customer's last message."""
    rounds = 0
    for message in reversed(messages):
        if message.type == "human":
            break
        if message.type == "ai" and getattr(message, "tool_calls", None):
            rounds += 1
    return rounds


# The Google SDK reads the key from the environment and sends it in a header (x-goog-api-key), never in
# the URL, and no code here reads it. redact() is the second line of defense: every error text the app
# prints, logs or writes to a file goes through it.
SECRET_VARS = ("GOOGLE_API_KEY", "GEMINI_API_KEY", "EMPORIO_API_TOKEN")
_GOOGLE_KEY = re.compile(r"AIza[0-9A-Za-z_\-]{35}")
_KEY_PARAM = re.compile(r"(?i)([?&](?:key|api_key|access_token)=)[^&\s\"']+")


def redact(text: str) -> str:
    """Mask API keys and the values of the secret environment variables."""
    text = _KEY_PARAM.sub(r"\1[redacted]", _GOOGLE_KEY.sub("[redacted]", text))
    for name in SECRET_VARS:
        value = (os.getenv(name) or "").strip()
        if len(value) >= 8:
            text = text.replace(value, f"[{name} redacted]")
    return text


class RedactingFilter(logging.Filter):
    """Runs every record a handler prints, traceback included, through redact()."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg, record.args = redact(record.getMessage()), None
        if record.exc_info and not record.exc_text:
            record.exc_text = logging.Formatter().formatException(record.exc_info)
        if record.exc_text:
            record.exc_text = redact(record.exc_text)
        return True


def protect_logs(*names: str) -> None:
    """Add the filter to the handlers of these loggers (the root logger when no name is given)."""
    for name in names or ("",):
        for handler in logging.getLogger(name or None).handlers:
            if not any(isinstance(f, RedactingFilter) for f in handler.filters):
                handler.addFilter(RedactingFilter())
