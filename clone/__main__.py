"""Command line entry point.

    python -m clone prepare chats/ --me "Your Name"   # build the redacted style dataset
    python -m clone chat                               # talk to your clone in the terminal
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .clone import ClaudeClone, MockClone
from .dataset import load_pairs, pick_examples, prepare, save_pairs

DEFAULT_DATA = Path("data/pairs.jsonl")


def load_clone(data: Path = DEFAULT_DATA, mock: bool | None = None, examples: int = 40):
    """Build a clone from a prepared dataset. Uses Claude when an API key is set,
    otherwise the offline mock (or force either with `mock`)."""
    pairs = pick_examples(load_pairs(data), examples)
    if mock is None:
        mock = not os.environ.get("ANTHROPIC_API_KEY")
    return (MockClone if mock else ClaudeClone)(examples=pairs)


def _prepare(args: argparse.Namespace) -> int:
    try:
        pairs, removed, chats = prepare(Path(args.folder), args.me)
    except ValueError as err:
        print(err, file=sys.stderr)
        return 1
    save_pairs(pairs, Path(args.out))
    print(f"Read {chats} chat(s) and built {len(pairs)} message/reply pairs -> {args.out}")
    print("Personal data removed before saving:")
    for kind in ("name", "phone", "email", "link", "card", "code"):
        print(f"  {kind:<6} {removed.get(kind, 0)}")
    print("Open the file and skim it before using it. Nothing has been sent anywhere.")
    return 0


def _chat(args: argparse.Namespace) -> int:
    clone = load_clone(Path(args.data), mock=True if args.mock else None)
    mode = "offline mock" if isinstance(clone, MockClone) else f"Claude ({clone.model})"
    print(f"Chatting with your clone [{mode}]. Type 'done' to stop.")
    while True:
        try:
            incoming = input("Them: ")
        except EOFError:
            return 0
        if incoming.strip().lower() == "done":
            return 0
        result = clone.reply(incoming)
        print(f"Clone: {result.text}")
        if result.handed_off:
            print(f"  ! Not answered automatically ({result.reason}). Reply to this one yourself.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m clone")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("prepare", help="build a redacted dataset from WhatsApp exports")
    p.add_argument("folder", help="folder with exported chats (.txt or .zip)")
    p.add_argument("--me", required=True, help="your name exactly as it appears in the export")
    p.add_argument("--out", default=str(DEFAULT_DATA))
    p.set_defaults(func=_prepare)

    c = sub.add_parser("chat", help="chat with your clone in the terminal")
    c.add_argument("--data", default=str(DEFAULT_DATA))
    c.add_argument("--mock", action="store_true", help="use the offline mock even if an API key is set")
    c.set_defaults(func=_chat)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
