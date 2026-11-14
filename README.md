# Make-AI-Clone-of-Yourself

> **This is a fork.** The original project, which fine-tunes Llama 3 on your WhatsApp history and replies through Ollama, is by [Eviltr0N](https://github.com/Eviltr0N/Make-AI-Clone-of-Yourself). Its README follows below, unchanged.
>
> **What I added in this fork (by [Covenant Odeyemi](https://github.com/Covenant-cov)):** a privacy-first pipeline and a Claude backend, in the `clone/` folder.

## Added in this fork: privacy-first pipeline with a Claude backend

The original sends your raw chats into training and lets the model reply to anyone about anything. I wanted a version I'd trust with real conversations, so I added:

| Piece | What it does |
|---|---|
| `clone/parser.py` | Parses WhatsApp exports from **Android and iPhone**, joins multi-line messages, drops system notices, media placeholders and deleted messages. |
| `clone/redact.py` | **Removes personal data before anything is saved or sent to a model:** names (each person gets a stable `[CONTACT_n]` tag), phone numbers, emails, links, card numbers (Luhn-checked) and one-time codes. Prints a count of what it removed. |
| `clone/dataset.py` | Builds message → reply pairs from the redacted chats. Reads `.zip` exports in memory, so media files are never unpacked to disk. |
| `clone/guardrails.py` | **Hand-off rules.** Messages about money, codes or passwords, emergencies, commitments, or "is this a bot?" never reach the model. The clone sends a holding reply and alerts you. Outgoing replies are scrubbed again and capped in length. |
| `clone/clone.py` | Replies **with Claude** (`claude-opus-5-5`) instead of a fine-tuned local model. Style comes from your redacted examples in a cached system prompt, so there's no GPU or training step. The first reply in each chat says it's an AI assistant. Includes an offline mock for demos and tests. |
| `tests/` | 20 pytest tests covering parsing, redaction, hand-off rules and the exact Claude request. |

**Why Claude instead of fine-tuning?** Fine-tuning needs a GPU and a training run every time your style changes. Few-shot examples in a cached prompt adapt instantly and cost little per message. Because the examples are redacted first, the model never sees your contacts' real names or numbers.

### Quick start

```bash
pip install -r requirements-claude.txt
python -m pytest                                   # 20 tests, no API key needed

# 1. Put your exported chats (.txt or .zip) in chats/, then build the redacted dataset
python -m clone prepare chats/ --me "Your Name"

# 2. Chat with your clone in the terminal (uses the offline mock until you set an API key)
python -m clone chat
```

Set `ANTHROPIC_API_KEY` to use Claude. To connect it to WhatsApp, install `requirements.txt` too and run `CLONE_BACKEND=claude python ai_to_whatsapp.py`.

Chat exports, datasets and logs are in `.gitignore`, so they can't be committed by accident.

Try it on the made-up sample chat: `python -m clone prepare examples/ --me "Sam Okafor"`.

---

## Original README (by Eviltr0N)

### Full Video Tutorial on [Youtube](https://youtu.be/a2_ZvzE55cA) - <https://youtu.be/a2_ZvzE55cA>

## Motivation

I saw a reel on Instagram in which an AI enthusiast created an AI clone of himself to talk to his girlfriend (Certainly, I won't do that... xd) using [RAG](https://youtu.be/YVWxbHJakgg?feature=shared) Retrieval Augmented Generation and the Chat GPT-3.5 turbo API. It kind of worked, but it had major privacy issues. Sending personal chats to Chat GPT could potentially result in those chats being used by OpenAI to train its model. This led me to think, what if I fine-tuned a pre-existing model like Llama or Mixtral on my personal WhatsApp chat history? It would be cool to have a model that can talk like me as I do on WhatsApp, primarily in Hinglish (Hindi + English).

[Fine-tuning a large language model (LLM)](https://youtu.be/YVWxbHJakgg?feature=shared) requires a good understanding of LLMs in general. The major challenge with fine-tuning big models, such as a 7B parameter model, is that it requires a minimum of 32GB of GPU RAM, which is costly and not available in free-tier GPU compute services like Colab or Kaggle. So, I had to find a way around this limitation.

Another important aspect is that the fine-tuning results heavily depend on the quality and size of the dataset used. Converting raw WhatsApp chat data into a usable dataset is challenging but worth pursuing.

Let's see how it looks in reality and how it's being carried out.

## Google Colab Notebook

Here is link of [Google Colab Notebook](https://colab.research.google.com/drive/1OGkiAZsYfShY0o8ZphCUuXkmb2Om422X?usp=sharing)

* This Notebook Contains - 
    * Data Collection From Whatsapp
    * Data Prepration
    * Data Filtering
    * Model Training
    * Inference
    * Saving Finetuned Model
    * GGUF Conversion
    * Downloading Saved Model


## Chatting With Fine-Tuned Model Using Ollama (You can also use [LM Studio](https://lmstudio.ai/) & [GPT4ALL](https://www.nomic.ai/gpt4all))

### Downloading Ollama
Go to the [downloads page of Ollama](https://ollama.com/download) and download and install it according to your OS.

### Loading the Model into Ollama
1. Open your file manager.
2. Navigate to the directory where you have downloaded the fine-tuned model, generally the Downloads folder.
3. Right-click anywhere on the screen and choose "Open terminal here." If you are using Windows, you can directly type `cmd` into the address bar and hit enter.
4. Type `ollama --version` into the terminal to check if you have installed Ollama successfully.
5. Make sure the model `unsloth.Q8_0.gguf` and `Modelfile` are in the current directory.
6. Open `Modelfile` using any text editor.
7. Edit the first line to ensure it looks like `FROM ./unsloth.Q8_0.gguf`, and save it.
8. Type this command: `ollama create my_model -f Modelfile`. This will add the model into Ollama.
9. Now type `ollama run my_model`.
10. You can now chat with your model.

## Using Model to Automate WhatsApp
Here comes the final part. I am using this wonderful tool [WPP_Whatsapp](https://github.com/3mora2/WPP_Whatsapp) to automate WhatsApp. By using this, we can use our model to respond to any incoming messages on WhatsApp. We can define specific people to talk to. Here is the step-by-step guide:

1. Clone this repo using:
    `git clone https://github.com/Eviltr0N/Make-AI-Clone-of-Yourself.git`

2. Go to the cloned repo:
    `cd Make-AI-Clone-of-Yourself/`

3. Install all the required packages by:
    `pip install -r requirements.txt`

4. First run:
    `python3 chat.py`

   Then type something like "Hello" and hit enter. If it works, it means everything is set up correctly.

5. Exit by pressing `Ctrl+C`.
6. Now run:
    `python3 ai_to_whatsapp.py`

7. It will take a bit of time at first to download the Chromium browser. As it finishes, a browser window will appear, and you have to scan the QR code using WhatsApp to link your WhatsApp account.
8. Switch back to the terminal. You have to provide the phone number of the other person you want to respond to with this AI model.
9. The phone number must include the country code without the `+` symbol, such as `916969696969`, then press enter.
10. As soon as that person sends any message, it will be printed on the terminal, and the AI model will respond to it.

### Keep in Mind
* If you want to change the temperature and top_k of the model (in simpler terms, temperature means creativity of the model), then:
    1. Open the `ai_to_whatsapp.py` file using any text editor.
    2. Go to the 9th line where you will find:
       `my_llm = LLM("my_model", 0.3, 50, 128)`

    3. Change `0.3` to a higher value such as `0.9` to increase the temperature (creativity) of the model.
    4. You can also change top_k from `50` to a higher value like `95`.

* Temperature can vary from `0.1` to `1` and top_k from `1` to `100`. The higher the temperature, the more creative and unpredictable the model becomes.
* Keep playing with the values of `temperature` and `top_k` until you are satisfied with the model's responses.


## What's Next
* Adding multimodal capabilities so this can understand and react to images too, as it currently supports only text messages.

* Adding some sort of agent pipeline above this model so another model, such as `LLaMA 3.1`, can see the message and the response of this model and judge if it is suitable or not, and can modify the model response accordingly.
