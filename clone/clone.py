"""The clone itself: replies in your style using Claude, or offline with a simple
matcher for testing. Both run every message through the same guardrails."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .dataset import Pair
from .guardrails import DISCLOSURE, HOLDING_REPLY, clean_reply, hand_off_reason
from .redact import Redactor

MODEL = "claude-opus-5-5"
MAX_HISTORY_TURNS = 20

_STYLE_PROMPT = """You are writing WhatsApp replies on behalf of one person, in their voice.

Below are real examples of messages they received and how they replied. Personal
details were removed and replaced with tags like [PHONE] or [CONTACT_1].

Match their style: message length, tone, slang, language mix, punctuation, emoji
use and how quickly they get to the point. Write only the reply text.

Rules:
- Never invent facts about their life, plans, location or other people. If a reply
  would need information you don't have, give a short, non-committal answer.
- Never agree to send money, share codes or passwords, sign anything or make plans.
- Never include phone numbers, emails, links or the bracketed tags in a reply.
- If you can't reply safely, write exactly: {holding}

<examples>
{examples}
</examples>"""


@dataclass
class CloneReply:
    text: str
    handed_off: bool = False
    reason: str | None = None


def _format_examples(examples: list[Pair]) -> str:
    return "\n\n".join(f"Them: {e.prompt}\nMe: {e.reply}" for e in examples)


@dataclass
class _Base:
    examples: list[Pair]
    disclose: bool = True
    redactor: Redactor = field(default_factory=Redactor)
    history: list[dict] = field(default_factory=list)
    _disclosed: bool = False

    def reply(self, incoming: str) -> CloneReply:
        reason = hand_off_reason(incoming)
        if reason:
            return CloneReply(HOLDING_REPLY, handed_off=True, reason=reason)

        safe_incoming = self.redactor.redact(incoming)
        raw = self._generate(safe_incoming)
        if raw is None:
            return CloneReply(HOLDING_REPLY, handed_off=True, reason="model_declined")
        text = clean_reply(raw, self.redactor)
        if not text or text == HOLDING_REPLY:
            return CloneReply(HOLDING_REPLY, handed_off=True, reason="model_unsure")

        self.history += [
            {"role": "user", "content": safe_incoming},
            {"role": "assistant", "content": text},
        ]
        self.history = self.history[-2 * MAX_HISTORY_TURNS:]
        if self.disclose and not self._disclosed:
            self._disclosed = True
            text = f"{text}\n\n{DISCLOSURE}"
        return CloneReply(text)

    def _generate(self, incoming: str) -> str | None:  # pragma: no cover
        raise NotImplementedError


@dataclass
class ClaudeClone(_Base):
    """Replies with Claude. The style examples sit in a cached system prompt,
    so each new message only pays full price for the recent conversation."""

    client: object = None
    model: str = MODEL

    def __post_init__(self) -> None:
        if self.client is None:
            import anthropic

            self.client = anthropic.Anthropic()
        self._system = [{
            "type": "text",
            "text": _STYLE_PROMPT.format(
                holding=HOLDING_REPLY, examples=_format_examples(self.examples)
            ),
            "cache_control": {"type": "ephemeral"},
        }]

    def _generate(self, incoming: str) -> str | None:
        response = self.client.beta.messages.create(
            model=self.model,
            max_tokens=16000,
            system=self._system,
            messages=self.history + [{"role": "user", "content": incoming}],
            output_config={"effort": "low"},  # casual chat doesn't need deep reasoning
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        if response.stop_reason == "refusal":
            return None
        return "".join(b.text for b in response.content if b.type == "text")


@dataclass
class MockClone(_Base):
    """Offline stand-in for demos and tests: answers with the reply from the
    example whose message shares the most words with the new one."""

    def _generate(self, incoming: str) -> str | None:
        words = set(re.findall(r"\w+", incoming.lower()))
        best = max(
            self.examples,
            key=lambda e: len(words & set(re.findall(r"\w+", e.prompt.lower()))),
            default=None,
        )
        return best.reply if best else None
