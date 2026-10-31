"""Last-mile formatting for WhatsApp: models slip into Markdown even when told not to."""

import re

_BOLD = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
_HEADING = re.compile(r"(?m)^#{1,6}\s+")
_BULLET = re.compile(r"(?m)^(\s*)[-*]\s+")


def whatsapp_text(text: str) -> str:
    text = _BOLD.sub(r"*\1*", text)
    text = _HEADING.sub("", text)
    return _BULLET.sub(r"\1• ", text).strip()
