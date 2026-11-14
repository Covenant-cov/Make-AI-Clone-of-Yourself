"""Parse WhatsApp "Export chat" text files (Android and iPhone formats) into messages."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Android: "12/03/2024, 9:41 pm - Name: text"
_ANDROID = re.compile(
    r"^‎?(\d{1,2}/\d{1,2}/\d{2,4}), (\d{1,2}:\d{2}(?:[\s ]?[APap]\.?[Mm]\.?)?) - (.*)$"
)
# iPhone: "[12/03/2024, 21:41:05] Name: text"
_IOS = re.compile(
    r"^‎?\[(\d{1,2}/\d{1,2}/\d{2,4}),? (\d{1,2}:\d{2}(?::\d{2})?(?:[\s ]?[APap][Mm])?)\] (.*)$"
)

# Lines WhatsApp adds itself, or content with no text worth learning from.
_SKIP_MARKERS = (
    "<Media omitted>",
    "image omitted",
    "video omitted",
    "audio omitted",
    "sticker omitted",
    "GIF omitted",
    "document omitted",
    "<attached:",
    "(file attached)",
    "This message was deleted",
    "You deleted this message",
    "Messages and calls are end-to-end encrypted",
    "Tap to learn more.",
    "null",
)
_EDITED = re.compile(r"\s*<This message was edited>\s*$")


@dataclass(frozen=True)
class Message:
    sender: str
    text: str


def _start(line: str) -> tuple[str, str] | None:
    """Return (sender, text) if the line starts a new message, else None."""
    match = _ANDROID.match(line) or _IOS.match(line)
    if not match:
        return None
    body = match.group(3)
    if ": " not in body:
        # System line such as "X added Y" or "You created group". Not a message.
        return ("", "")
    sender, text = body.split(": ", 1)
    return sender.strip().lstrip("‎~ ").strip(), text


def parse_chat(raw: str) -> list[Message]:
    """Turn a whole exported chat into a list of messages, in order.

    Multi-line messages are joined back together, system notices are dropped,
    and media placeholders or deleted messages are skipped.
    """
    messages: list[Message] = []
    sender: str | None = None
    lines: list[str] = []

    def flush() -> None:
        if sender:
            text = _EDITED.sub("", "\n".join(lines)).strip()
            if text and not any(marker in text for marker in _SKIP_MARKERS):
                messages.append(Message(sender, text))

    for line in raw.splitlines():
        started = _start(line)
        if started is None:
            if sender:
                lines.append(line)
            continue
        flush()
        sender, first = started
        lines = [first]
    flush()
    return messages


def participants(messages: list[Message]) -> list[str]:
    """Everyone who sent at least one message, in order of first appearance."""
    seen: dict[str, None] = {}
    for message in messages:
        seen.setdefault(message.sender, None)
    return list(seen)
