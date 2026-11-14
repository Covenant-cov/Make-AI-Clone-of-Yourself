# Privacy-first AI clone of yourself

An AI that replies to WhatsApp messages in your own style, built so personal chats can be used without exposing anyone's data.

Built on [Eviltr0N's open-source project](https://github.com/Eviltr0N/Make-AI-Clone-of-Yourself), which fine-tunes Llama 3 on WhatsApp history and replies through Ollama. I added a privacy pipeline, safety hand-off rules and a Claude backend, all in the `clone/` folder.

## Why

The original sends raw chats, full of names, phone numbers and one-time codes, into training, and lets the model reply to anyone about anything, including requests for money. I wanted a version I would trust with real conversations.

## What I built

| Piece | What it does |
|---|---|
| `clone/parser.py` | Parses WhatsApp exports from **Android and iPhone**, joins multi-line messages, and drops system notices, media placeholders and deleted messages. |
| `clone/redact.py` | **Removes personal data before anything is saved or sent to a model:** names (each person gets a stable `[CONTACT_n]` tag), phone numbers, emails, links, card numbers (Luhn-checked) and one-time codes. Reports how much of each it removed. |
| `clone/dataset.py` | Builds message → reply pairs from the redacted chats. Reads `.zip` exports in memory, so media files are never unpacked to disk. |
| `clone/guardrails.py` | **Hand-off rules.** Messages about money, codes or passwords, emergencies, commitments, or "is this a bot?" never reach the model. The clone sends a holding reply and alerts you. Outgoing replies are scrubbed again and capped in length. |
| `clone/clone.py` | Replies **with Claude** instead of a fine-tuned local model. Your style comes from redacted examples in a cached system prompt, so there is no GPU or training step. The first reply in each chat says it is an AI assistant. Includes an offline mock for demos and tests. |
| `tests/` | 20 pytest tests covering parsing, redaction, hand-off rules and the exact Claude request. |

**Why Claude instead of fine-tuning?** Fine-tuning needs a GPU and a new training run every time your style changes. Few-shot examples in a cached prompt adapt instantly and cost little per message. Because the examples are redacted first, the model never sees your contacts' real names or numbers.

## How it works

```
WhatsApp export → parse → redact personal data → message/reply pairs
incoming message → hand-off rules → Claude (style examples, cached) → scrub reply → WhatsApp
```

## Quick start

```bash
pip install -r requirements-claude.txt
python -m pytest                                   # 20 tests, no API key needed

# Build the redacted dataset from your exported chats (.txt or .zip)
python -m clone prepare chats/ --me "Your Name"

# Chat with your clone in the terminal (offline mock until ANTHROPIC_API_KEY is set)
python -m clone chat
```

Try it on the made-up sample chat: `python -m clone prepare examples/ --me "Sam Okafor"`.

To connect it to WhatsApp, also install `requirements.txt` and run `ai_to_whatsapp.py` with `CLONE_BACKEND=claude`.

Chat exports, datasets and logs are listed in `.gitignore`, so they can't be committed by accident.

## Credits

The original fine-tuning notebook, Ollama setup and WhatsApp bridge (`chat.py`, `chat_process.py`, `ai_to_whatsapp.py`, `colab.ipynb`) are by [Eviltr0N](https://github.com/Eviltr0N/Make-AI-Clone-of-Yourself); I added the Claude backend option to `ai_to_whatsapp.py`. See the original repository for the fine-tuning guide.

---

Built by [Covenant Odeyemi](https://github.com/Covenant-cov).
