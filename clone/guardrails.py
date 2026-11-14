"""Rules that decide when the clone must not answer for you."""

from __future__ import annotations

import re

from .redact import Redactor

# Messages where a wrong auto-reply could cost money, safety or trust.
# The clone never answers these. It sends a holding reply and alerts you.
_HAND_OFF_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("money", re.compile(
        r"\b(send|transfer|lend|borrow|owe|pay|refund|loan)\b.*\b(money|cash|naira|dollars?|\$|₦|£|€|\d{3,})"
        r"|\b(account (number|details)|bank details|sort code|iban|crypto|bitcoin|usdt)\b",
        re.IGNORECASE)),
    ("security", re.compile(
        r"\b(otp|one[- ]time code|verification code|password|passcode|pin|2fa|login code)\b",
        re.IGNORECASE)),
    ("emergency", re.compile(
        r"\b(emergency|hospital|accident|ambulance|police|arrested|kidnap\w*|urgent|help me)\b",
        re.IGNORECASE)),
    ("commitment", re.compile(
        r"\b(sign|contract|agree to|promise|confirm (the|our|my) (meeting|booking|deal))\b",
        re.IGNORECASE)),
    ("identity", re.compile(
        r"\b(are you (a |an )?(bot|ai|robot|real)|is this (really )?you|am i talking to)\b",
        re.IGNORECASE)),
]

HOLDING_REPLY = "Let me get back to you on this one personally."
DISCLOSURE = "(Auto-reply from my AI assistant. I'll see this later.)"
MAX_REPLY_CHARS = 600


def hand_off_reason(incoming: str) -> str | None:
    """Return why a human must handle this message, or None if the clone may reply."""
    for reason, pattern in _HAND_OFF_RULES:
        if pattern.search(incoming):
            return reason
    return None


def clean_reply(reply: str, redactor: Redactor) -> str:
    """Last check on the way out: never send personal data the model picked up
    from the examples, and keep replies chat-sized."""
    reply = redactor.redact(reply.strip())
    reply = re.sub(r"\[(CONTACT_\d+|ME)\]", "", reply)  # placeholders shouldn't reach a real chat
    reply = re.sub(r"[ \t]{2,}", " ", reply).strip()
    if len(reply) > MAX_REPLY_CHARS:
        reply = reply[:MAX_REPLY_CHARS].rsplit(" ", 1)[0] + "…"
    return reply
