# Telegram Manual AI Bot — GitHub + Railway Hobby + Gemini

This is a **new independent bot**. No Google Cloud account, webhook, OpenAI key or Google Drive API is needed for this first version.

## What it does

- Answers only using text extracted from files in `manuals/`.
- Responds with exactly `it's out of my knowledge` if no matching evidence is found or Gemini cannot support an answer.
- Offers a **Talk to Admin** button after an unsupported question.
- Sends support requests to **one admin's private Telegram chat**. The admin must send `/start` to the bot first.
- The admin replies **to the bot's support notification**; the reply is forwarded to the user. Reply `/close` to the notification to end the session.
- Uses polling as a Railway worker: **no domain, public port, webhook or API URL needed**.

## 1. Prepare the manuals

Put PDF (selectable text), DOCX, TXT, or MD files in `manuals/`. Scanned/image-only PDFs require OCR and are not supported yet. The manuals are packaged at deploy time: changing them requires a GitHub push/redeploy. For confidential manuals use a **private GitHub repository** with appropriate access controls. This initial version does not connect to Google Drive.

## 2. Create Telegram bot

Open the official [@BotFather](https://t.me/BotFather), send `/newbot`, and save your token privately. Get your numeric Telegram ID from [@userinfobot](https://t.me/userinfobot). Open your new bot from your own Telegram account and press **Start** (admin messages cannot arrive before this).

## 3. Create GitHub repository

Create a new **private** repository, for example `telegram-manual-ai-bot`, and upload the extracted project contents (including `bot.py`, `knowledge.py`, `storage.py`, `requirements.txt`, `railway.json`, and `manuals/`). Do **not** upload `.env` or real tokens.

## 4. Deploy on Railway Hobby

1. Open Railway → **New Project** → **Deploy from GitHub repo**.
2. Authorize/select the new repository.
3. In the service **Variables**, add:

| Variable | Example / meaning |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token from BotFather |
| `GEMINI_API_KEY` | Your existing Gemini API key |
| `ADMIN_CHAT_ID` | Your numeric Telegram ID, e.g. `123456789` |
| `GEMINI_MODEL` | `gemini-2.5-flash` (change if unavailable to your key) |
| `DB_PATH` | `/data/bot.db` when using a Railway volume |

4. **Recommended:** Add a Railway Volume mounted at `/data`. This preserves support-session mappings across restarts. Set `DB_PATH=/data/bot.db`. Without a volume, omit `DB_PATH` and the bot uses a temporary local SQLite file; sessions can be lost on redeploy.
5. Railway should use the included `railway.json` start command `python bot.py`. If not, set **Start Command** to `python bot.py` manually.
6. Deploy. In Railway logs look for `Starting Telegram long polling`.
7. Do **not** generate a domain: this bot uses polling and does not listen on a web port.
8. Keep **one replica** of the bot running; multiple polling replicas using the same Telegram token conflict.

## 5. Test end to end

1. Admin opens the bot and sends `/start`.
2. From a different Telegram account, send a question answered in your manual; check answer + source.
3. Ask an unrelated question. Expect exactly `it's out of my knowledge` plus **Talk to Admin**.
4. Tap **Talk to Admin**. The admin receives a support notification.
5. Admin replies directly to that notification. The user receives `Administrator: ...`.
6. Admin replies `/close` to that original notification. AI mode resumes.

## Notes and limits

- **Gemini key reuse:** You may use the same key as another project if the model is enabled. Both apps share quota/rate limits and potentially costs.
- **No general internet search:** The code sends only retrieved manual passages to Gemini, and instructs it to refuse unsupported questions. This reduces hallucinations but cannot guarantee perfect grounding.
- **Retrieval is keyword-based**, not semantic vector RAG. Good for small manuals, but it may miss paraphrased questions or find superficially similar text. Upgrade to embeddings/vector search for larger documentation collections.
- **Privacy:** Relevant excerpts and user questions are sent to the Gemini API. Review your organization's data-handling requirements before uploading proprietary manuals.
- **Technical safety:** Have qualified personnel verify safety-critical maintenance procedures.
- **Admin support is text-only** in this starter.
- **Costs:** Railway Hobby is paid; Gemini API charges and quotas are separate. GitHub Free is sufficient for a normal private code repository.
- **Security:** Never commit tokens. If a token leaks, rotate it in BotFather or your Gemini API console.
- **No Google Drive yet:** This keeps initial deployment simple. Drive synchronization can be added later.
