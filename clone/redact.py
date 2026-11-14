"""Remove personal data from chat text before it is stored or sent to any model."""

from __future__ import annotations

import re
from collections import Counter

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_URL = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
_CARD = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
_PHONE = re.compile(r"(?<![\w/])\+?\d[\d ().-]{6,}\d(?![\w/])")
# One-time codes and PINs that people paste into chats ("code is 482913").
_CODE = re.compile(
    r"\b(otp|code|pin|password|passcode)\b(\s*(?:is|:|=)?\s*)([A-Za-z0-9]{4,10})\b",
    re.IGNORECASE,
)


def _luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


class Redactor:
    """Replaces emails, links, card numbers, phone numbers, one-time codes and
    people's names with placeholders, and counts what it removed.

    Names get a stable label per person (the first contact is always
    [CONTACT_1]), so the conversation still reads naturally after redaction.
    """

    def __init__(self, names: list[str] | None = None, me: str | None = None):
        self.counts: Counter[str] = Counter()
        self._labels: dict[str, str] = {}
        self._name_patterns: list[tuple[re.Pattern[str], str]] = []
        if me:
            self._add_name(me, "[ME]")
        contacts = 0
        for name in names or []:
            if name and name != me and name not in self._labels:
                contacts += 1
                self._add_name(name, f"[CONTACT_{contacts}]")

    def _add_name(self, name: str, label: str) -> None:
        self._labels[name] = label
        # Match the full name and each part of it ("Ada Obi" also hides "Ada").
        parts = [name] + [p for p in re.split(r"\s+", name) if len(p) >= 3]
        for part in sorted(set(parts), key=len, reverse=True):
            pattern = re.compile(rf"(?<!\w){re.escape(part)}(?!\w)", re.IGNORECASE)
            self._name_patterns.append((pattern, label))

    def label_for(self, name: str) -> str:
        return self._labels.get(name, name)

    def _sub(self, pattern: re.Pattern[str], kind: str, text: str, repl: str) -> str:
        new, n = pattern.subn(repl, text)
        self.counts[kind] += n
        return new

    def redact(self, text: str) -> str:
        text = self._sub(_EMAIL, "email", text, "[EMAIL]")
        text = self._sub(_URL, "link", text, "[LINK]")

        def card(match: re.Match[str]) -> str:
            digits = re.sub(r"\D", "", match.group(0))
            if 13 <= len(digits) <= 19 and _luhn_ok(digits):
                self.counts["card"] += 1
                return "[CARD]"
            return match.group(0)

        text = _CARD.sub(card, text)
        text = self._sub(_PHONE, "phone", text, "[PHONE]")

        def code(match: re.Match[str]) -> str:
            value = match.group(3)
            if not any(ch.isdigit() for ch in value):
                return match.group(0)  # "the code is ready" is not a secret
            self.counts["code"] += 1
            return f"{match.group(1)}{match.group(2)}[CODE]"

        text = _CODE.sub(code, text)
        for pattern, label in self._name_patterns:
            text = self._sub(pattern, "name", text, label)
        return text
