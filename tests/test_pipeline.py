from pathlib import Path
from types import SimpleNamespace

import pytest

from clone.clone import ClaudeClone, MockClone
from clone.dataset import Pair, build_pairs, pick_examples, prepare
from clone.guardrails import DISCLOSURE, HOLDING_REPLY, hand_off_reason
from clone.parser import parse_chat, participants
from clone.redact import Redactor

SAMPLE = Path(__file__).parent.parent / "examples" / "sample_chat.txt"


# ---------- parser ----------

def test_parses_android_export_and_skips_noise():
    messages = parse_chat(SAMPLE.read_text(encoding="utf-8"))
    texts = [m.text for m in messages]
    assert participants(messages) == ["Tobi Adeyemi", "Sam Okafor"]
    assert not any("<Media omitted>" in t or "deleted" in t or "encrypted" in t for t in texts)
    # multi-line message is joined, "edited" marker removed
    assert "Almost. Just fixing the charts\nit should be done by tonight" in texts
    assert "Will do" in texts


def test_parses_iphone_export():
    raw = (
        "[12/03/2024, 21:02:11] Ada: hey\n"
        "[12/03/2024, 21:03:40] Me Myself: hi!\n"
        "second line\n"
    )
    messages = parse_chat(raw)
    assert [(m.sender, m.text) for m in messages] == [("Ada", "hey"), ("Me Myself", "hi!\nsecond line")]


# ---------- redaction ----------

def test_redacts_personal_data():
    r = Redactor(names=["Tobi Adeyemi", "Sam Okafor"], me="Sam Okafor")
    out = r.redact(
        "Tobi, mail tobi.adeyemi@example.com or call +234 803 555 0142, "
        "see https://example.com/x, card 4111 1111 1111 1111, my otp is 482913"
    )
    for leaked in ("Tobi", "example.com", "0142", "4111", "482913"):
        assert leaked not in out
    assert "[CONTACT_1]" in out and "[EMAIL]" in out and "[PHONE]" in out
    assert "[LINK]" in out and "[CARD]" in out and "[CODE]" in out
    assert r.counts["card"] == 1 and r.counts["code"] == 1


def test_redaction_leaves_ordinary_text_alone():
    r = Redactor(names=["Tobi Adeyemi"])
    text = "Meeting at 4:30 on 12/03/2024, the code is ready, it costs 5,000"
    assert r.redact(text) == text


# ---------- dataset ----------

def test_builds_redacted_pairs_from_sample(tmp_path):
    (tmp_path / "chat.txt").write_text(SAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    pairs, removed, chats = prepare(tmp_path, me="Sam Okafor")
    assert chats == 1
    assert pairs[0] == Pair(
        "Bro you around this weekend?\nThinking we watch the match at mine",
        "Yeah should be free\nWhat time",
    )
    assert all("Tobi" not in p.prompt + p.reply for p in pairs)
    assert removed["phone"] == 1 and removed["email"] == 1 and removed["link"] == 1


def test_filler_messages_are_not_used_as_prompts():
    messages = parse_chat(
        "1/1/24, 9:00 am - A: ok\n1/1/24, 9:01 am - B: cool\n"
        "1/1/24, 9:02 am - A: dinner later?\n1/1/24, 9:03 am - B: sure"
    )
    pairs = build_pairs(messages, "B", Redactor())
    assert [p.prompt for p in pairs] == ["dinner later?"]


def test_wrong_name_gives_helpful_error(tmp_path):
    (tmp_path / "chat.txt").write_text(SAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(ValueError, match="Names found: Tobi Adeyemi, Sam Okafor"):
        prepare(tmp_path, me="Samuel")


def test_pick_examples_spreads_and_caps():
    pairs = [Pair(f"q{i}", f"a{i}") for i in range(100)]
    picked = pick_examples(pairs, 10)
    assert len(picked) == 10 and picked[0].prompt == "q0" and picked[-1].prompt == "q90"


# ---------- guardrails ----------

@pytest.mark.parametrize("message, reason", [
    ("Please send me 20000 naira, I'll pay back", "money"),
    ("What's your bank account number?", "money"),
    ("Read me the verification code you just got", "security"),
    ("I was in an accident, please call", "emergency"),
    ("Are you a bot?", "identity"),
    ("Can you confirm the meeting with the client?", "commitment"),
    ("How was your weekend?", None),
])
def test_hand_off_rules(message, reason):
    assert hand_off_reason(message) == reason


# ---------- clone ----------

EXAMPLES = [Pair("you around this weekend?", "Yeah should be free"),
            Pair("did you finish the report?", "Almost, tonight")]


def test_sensitive_message_never_reaches_the_model():
    clone = MockClone(examples=EXAMPLES)
    result = clone.reply("send me 5000 naira abeg")
    assert result.handed_off and result.reason == "money" and result.text == HOLDING_REPLY
    assert clone.history == []


def test_first_reply_discloses_ai_then_stops():
    clone = MockClone(examples=EXAMPLES)
    first = clone.reply("are you around this weekend")
    second = clone.reply("did you finish the report")
    assert first.text.endswith(DISCLOSURE)
    assert second.text == "Almost, tonight"


class FakeClient:
    """Records the request and returns a canned response, like the real SDK."""

    def __init__(self, text="Yeah, call me on +234 803 555 0142", stop_reason="end_turn"):
        self.calls = []
        response = SimpleNamespace(
            stop_reason=stop_reason,
            content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)],
        )
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))
        self._response = response

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return self._response


def test_claude_request_shape_and_output_cleaning():
    client = FakeClient()
    clone = ClaudeClone(examples=EXAMPLES, client=client, disclose=False)
    result = clone.reply("Tobi here, you free?")
    call = client.calls[0]
    assert call["model"] == "claude-opus-5-5"
    assert call["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert "Them: you around this weekend?\nMe: Yeah should be free" in call["system"][0]["text"]
    assert call["fallbacks"] == "default" and call["output_config"] == {"effort": "low"}
    assert "thinking" not in call  # adaptive is the default on this model
    # phone number in the model's reply is stripped before sending
    assert result.text == "Yeah, call me on [PHONE]" and not result.handed_off


def test_claude_refusal_is_handed_off():
    clone = ClaudeClone(examples=EXAMPLES, client=FakeClient(stop_reason="refusal"))
    result = clone.reply("hey what's up")
    assert result.handed_off and result.reason == "model_declined"


def test_history_is_sent_on_next_turn():
    client = FakeClient(text="sure")
    clone = ClaudeClone(examples=EXAMPLES, client=client, disclose=False)
    clone.reply("dinner later?")
    clone.reply("7pm?")
    assert client.calls[1]["messages"] == [
        {"role": "user", "content": "dinner later?"},
        {"role": "assistant", "content": "sure"},
        {"role": "user", "content": "7pm?"},
    ]
