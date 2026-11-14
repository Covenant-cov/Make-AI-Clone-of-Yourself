"""Turn parsed chats into redacted (message, my reply) pairs that show how you write."""

from __future__ import annotations

import io
import json
import zipfile
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from .parser import Message, parse_chat, participants
from .redact import Redactor

FILLERS = {"ok", "okay", "k", "kk", "hmm", "hm", "lol", "lmao", "yes", "no", "ya", "yeah", "hn", "?"}


@dataclass(frozen=True)
class Pair:
    prompt: str  # what the other person said
    reply: str  # what you answered


def _turns(messages: list[Message]) -> list[tuple[str, str]]:
    """Merge back-to-back messages from the same person into one turn."""
    turns: list[tuple[str, list[str]]] = []
    for m in messages:
        if turns and turns[-1][0] == m.sender:
            turns[-1][1].append(m.text)
        else:
            turns.append((m.sender, [m.text]))
    return [(sender, "\n".join(texts)) for sender, texts in turns]


def _is_filler(text: str) -> bool:
    return text.strip().lower().strip(".!") in FILLERS or len(text.strip()) <= 1


def build_pairs(messages: list[Message], me: str, redactor: Redactor) -> list[Pair]:
    """Pair each turn from someone else with the reply you sent straight after it."""
    pairs: list[Pair] = []
    turns = _turns(messages)
    for (sender, text), (next_sender, reply) in zip(turns, turns[1:]):
        if sender == me or next_sender != me or _is_filler(text):
            continue
        pairs.append(Pair(redactor.redact(text), redactor.redact(reply)))
    return pairs


def _read_exports(folder: Path) -> list[tuple[str, str]]:
    """Read every .txt export in the folder, including ones inside .zip files,
    without unpacking anything to disk (media in the zip is never written out)."""
    found: list[tuple[str, str]] = []
    for path in sorted(folder.iterdir()):
        if path.suffix.lower() == ".txt":
            found.append((path.name, path.read_text(encoding="utf-8", errors="replace")))
        elif path.suffix.lower() == ".zip":
            with zipfile.ZipFile(path) as archive:
                for name in archive.namelist():
                    if name.lower().endswith(".txt"):
                        with archive.open(name) as handle:
                            text = io.TextIOWrapper(handle, encoding="utf-8", errors="replace").read()
                        found.append((f"{path.name}/{name}", text))
    return found


def prepare(folder: Path, me: str) -> tuple[list[Pair], Counter[str], int]:
    """Process every chat export in a folder.

    Returns the pairs, how many of each kind of personal data were removed,
    and how many chats were read.
    """
    exports = _read_exports(folder)
    parsed = [parse_chat(text) for _, text in exports]
    everyone: list[str] = []
    for messages in parsed:
        for name in participants(messages):
            if name not in everyone:
                everyone.append(name)
    if me not in everyone:
        raise ValueError(
            f'"{me}" never sends a message in these chats. Use your name exactly as '
            f"it appears in the export. Names found: {', '.join(everyone) or 'none'}"
        )
    redactor = Redactor(names=everyone, me=me)
    pairs = [pair for messages in parsed for pair in build_pairs(messages, me, redactor)]
    return pairs, redactor.counts, len(exports)


def save_pairs(pairs: list[Pair], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for pair in pairs:
            f.write(json.dumps(asdict(pair), ensure_ascii=False) + "\n")


def load_pairs(path: Path) -> list[Pair]:
    with path.open(encoding="utf-8") as f:
        return [Pair(**json.loads(line)) for line in f if line.strip()]


def pick_examples(pairs: list[Pair], n: int = 40) -> list[Pair]:
    """Choose up to n examples spread evenly across the history, skipping very
    long ones, so the style prompt covers many moods without getting huge."""
    usable = [p for p in pairs if len(p.prompt) <= 400 and len(p.reply) <= 400]
    if len(usable) <= n:
        return usable
    step = len(usable) / n
    return [usable[int(i * step)] for i in range(n)]
