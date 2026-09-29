# Cyberbullying Moderation Service (backend)

A FastAPI service that takes chat messages as JSON and classifies each one as **green**, **yellow** or **severe**. It remembers users by ID and name, tracks a reputation score for each sender, and stores every message along with a moderation event. Everything is available through a REST API that a dashboard or another app can use. A simple built-in dashboard is included.

Classification uses the Groq LLM when `GROQ_API_KEY` is set. Without a key, or if the LLM call fails or returns bad JSON, it uses a rule-based classifier, so the service works either way.

## Features

- Classifies each message as green, yellow or severe, with a confidence score, a reason and a recommended action.
- Combines three sources: the Groq LLM, regex guardrails, and the sender's recent history.
- Escalates repeated abuse toward the same person, and yellow messages from senders with very low reputation.
- Keeps a reputation score (0–100) and a risk level for every sender.
- Stores every message plus a moderation event (old score, new score, decision notes) for auditing.
- Falls back to rule-based classification if the LLM is unavailable, so the service stays up.
- Includes a live dashboard at `/dashboard` and interactive API docs at `/docs`.

## Setup

Requires Python 3.12+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # Windows PowerShell: Copy-Item .env.example .env
```

Then set `GROQ_API_KEY` in `.env`. This is optional; without it the service uses the rule-based classifier.

## Environment variables

| Variable               | Default                     | Purpose                                                    |
|------------------------|-----------------------------|------------------------------------------------------------|
| `GROQ_API_KEY`         | *(empty)*                   | Turns on LLM classification. If empty, the rule-based fallback is used. |
| `GROQ_MODEL`           | `openai/gpt-oss-120b`       | Groq model name (must be available to your key)            |
| `LLM_TIMEOUT_SECONDS`  | `10`                        | Timeout for the LLM request                                |
| `DATABASE_URL`         | `sqlite:///./moderation.db` | Database connection string                                 |
| `RECENT_CONTEXT_LIMIT` | `10`                        | Number of recent messages used as context                  |

`.env` is only read at startup, so restart the server after changing it.

## Run the server

```bash
uvicorn app.main:app --reload
```

Database tables are created on startup. Then open:

| URL | What it is |
|---|---|
| http://127.0.0.1:8000/dashboard | Live dashboard |
| http://127.0.0.1:8000/docs | Interactive API docs (Swagger UI) |
| http://127.0.0.1:8000/redoc | Read-only API reference |

To start with no data, stop the server and delete `moderation.db`.

## Dashboard

`/dashboard` is a single static HTML file (`app/static/dashboard.html`) that only calls the public API. It has no build step and no dependencies. It shows:

- **Totals:** tiles for users, messages classified, and the green/yellow/severe counts, plus a bar showing the label distribution.
- **Users table:** each user's reputation bar and risk badge, with a risk-level filter. Click a user to see only their messages.
- **Classify form:** send a message and see the label, reason, recommended action and the sender's new reputation.
- **Live feed:** recent messages, showing sender → target, confidence and reason.

It refreshes every 5 seconds and follows the OS light/dark theme.

## API

| Method | Path                                  | Description                                         |
|--------|---------------------------------------|-----------------------------------------------------|
| GET    | `/api/v1/health`                      | `{"status": "ok"}`                                  |
| POST   | `/api/v1/messages/classify`           | Classify and store a message (409 if the `message_id` already exists) |
| GET    | `/api/v1/messages`                    | Recent messages across all users; optional `?label=green\|yellow\|severe&limit=50` |
| GET    | `/api/v1/users`                       | List users, lowest reputation first; optional `?risk_level=good\|watch\|risky\|dangerous` |
| GET    | `/api/v1/users/{user_id}`             | Reputation and label counts for one user            |
| GET    | `/api/v1/users/{user_id}/messages`    | Recent messages sent or received by the user (`?limit=50`) |

### Example request

```bash
curl -X POST http://127.0.0.1:8000/api/v1/messages/classify \
  -H "Content-Type: application/json" \
  -d '{
        "message_id": "msg_001",
        "sender": {"id": "u_101", "name": "Rohan"},
        "target": {"id": "u_202", "name": "Aman"},
        "text": "you are useless",
        "timestamp": "2026-09-30T00:55:00Z"
      }'
```

On Windows PowerShell, `curl` is an alias for a different command, so use `Invoke-RestMethod` instead:

```powershell
$body = '{"message_id":"msg_001","sender":{"id":"u_101","name":"Rohan"},"target":{"id":"u_202","name":"Aman"},"text":"you are useless","timestamp":"2026-09-30T00:55:00Z"}'
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/messages/classify -ContentType "application/json" -Body $body
```

Response:

```json
{
  "message_id": "msg_001",
  "label": "yellow",
  "confidence": 0.95,
  "reason": "Direct personal insult without threat, qualifies as mild harassment",
  "recommended_action": "Issue warning and monitor further messages",
  "sender_reputation": {"user_id": "u_101", "name": "Rohan", "score": 95, "risk_level": "good"}
}
```

`target` can be `null` for group or general messages. `timestamp` is optional; if it's missing, the server's time is used. Each `message_id` can only be classified once.

## Run tests

```bash
pytest -v
```

Tests use an in-memory SQLite database and always run the rule-based classifier, so they need no network and no API key.

## Architecture

```
Dashboard (app/static)      static HTML page; only calls the REST API
   │
API (app/api/routes)        request/response only
   │
Services (app/services)     database access and the business flow
   │   moderation_service.process_message:
   │     upsert sender/target → recent context → agent.classify
   │     → decision_engine.decide → update reputation → save message + event
   │
Agent (app/agent)           classification only, no database writes
   │   moderation_agent: Groq LLM (llm_client + prompts) → rule-based fallback
   │
Tools (app/tools)
       rule_checker:     regex guardrail for obvious severe/yellow phrases
       decision_engine:  combines rules, AI result, history and reputation
```

**Decision rules** (checked in order):
1. If the rule checker finds severe content, the label is **severe**.
2. If the LLM says severe, the label is **severe**.
3. If the message is yellow and the sender has sent 3 or more yellow messages to the same target recently (counting this one), it's escalated to **severe**.
4. If the message is yellow and the sender's reputation is below 30, it's escalated to **severe**.
5. Otherwise the AI label is used. Without an LLM, the AI label comes from the rule-based classifier.

**Reputation:** every user starts at 100. Each message changes the score by +1 (green), −5 (yellow) or −20 (severe), and the score stays between 0 and 100.
Risk levels: 80–100 `good`, 60–79 `watch`, 30–59 `risky`, 0–29 `dangerous`.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Every `reason` starts with `Rule-based:` even though a key is set | The LLM call is failing. Look for a `LLM call failed: ...` warning in the server terminal. A common cause is a `GROQ_MODEL` your key can't use (404 `model_not_found`). Pick a model from your Groq console, then restart the server. |
| `409 Conflict` | That `message_id` was already classified. Use a new ID. |
| `422 Unprocessable Entity` | The request body is invalid, for example empty `text`, a missing sender, or an unknown `risk_level`. |
| Old data in the demo | Stop the server, delete `moderation.db`, and start it again. |

## Demo walkthrough

These tests show every behaviour of the service. Run them on the docs page: open `POST /api/v1/messages/classify` at http://127.0.0.1:8000/docs, click **Try it out**, paste a body and click **Execute**. For the best effect, keep `/dashboard` open beside it and watch the numbers change.

**Before you start:** stop the server, delete `moderation.db`, then start it again. Run the tests **in order**, because later steps depend on the reputation built up by earlier ones.

### 1. The three basic labels

**T1: green, a friendly message.** Expect `green`, score **100** (it can't go higher).
```json
{"message_id": "t01", "sender": {"id": "u_101", "name": "Rohan"}, "target": {"id": "u_202", "name": "Aman"}, "text": "hey, want to study together later?"}
```

**T2: yellow, a mild insult.** Expect `yellow`, score **95**.
```json
{"message_id": "t02", "sender": {"id": "u_101", "name": "Rohan"}, "target": {"id": "u_202", "name": "Aman"}, "text": "you are useless"}
```

**T3: sarcasm in a group message (no target).** Expect `yellow`, score **90**. No keyword rule matches this, so the label comes from the LLM.
```json
{"message_id": "t03", "sender": {"id": "u_101", "name": "Rohan"}, "target": null, "text": "wow, great job as always, genius 🙄"}
```

### 2. The LLM catches what keyword rules miss

**T4: bullying with no bad words.** Expect `severe`, Priya's score **80**. The rules alone would have called this green.
```json
{"message_id": "t04", "sender": {"id": "u_303", "name": "Priya"}, "target": {"id": "u_202", "name": "Aman"}, "text": "Everyone in class laughs at you behind your back"}
```

**T5: friendly banter that contains an insult word.** Expect `green` or `yellow` from the LLM. It can tell joking between friends from real abuse, even though the rules flag "idiot".
```json
{"message_id": "t05", "sender": {"id": "u_707", "name": "Arjun"}, "target": {"id": "u_808", "name": "Dev"}, "text": "haha you absolute idiot, you forgot your own birthday party 😂 love you bro"}
```

### 3. The rule checker overrides everything

**T6: self-harm encouragement.** Expect `severe`, Karan's score **80**.
```json
{"message_id": "t06", "sender": {"id": "u_404", "name": "Karan"}, "target": {"id": "u_202", "name": "Aman"}, "text": "kys"}
```

**T7: a direct threat.** Expect `severe`, score **60**, and risk level changes to **`watch`**.
```json
{"message_id": "t07", "sender": {"id": "u_404", "name": "Karan"}, "target": {"id": "u_202", "name": "Aman"}, "text": "I will kill you after school"}
```

### 4. Repeated targeting escalates

**T8.** Expect `yellow`, Vikram's score **95**.
```json
{"message_id": "t08", "sender": {"id": "u_505", "name": "Vikram"}, "target": {"id": "u_606", "name": "Neha"}, "text": "you are so dumb"}
```

**T9.** Expect `yellow`, score **90**.
```json
{"message_id": "t09", "sender": {"id": "u_505", "name": "Vikram"}, "target": {"id": "u_606", "name": "Neha"}, "text": "stop talking, you stupid girl"}
```

**T10: the third yellow to the same person.** Expect **`severe`**, score **70** (`watch`), and a `reason` that says **"Repeated targeted abuse: 3 yellow messages…"**. On its own this message would only be yellow.
```json
{"message_id": "t10", "sender": {"id": "u_505", "name": "Vikram"}, "target": {"id": "u_606", "name": "Neha"}, "text": "what an idiot"}
```

### 5. Low reputation escalates

**T11.** Expect `severe`, Karan's score **40** (`risky`).
```json
{"message_id": "t11", "sender": {"id": "u_404", "name": "Karan"}, "target": {"id": "u_202", "name": "Aman"}, "text": "go die"}
```

**T12.** Expect `severe`, score **20** (`dangerous`).
```json
{"message_id": "t12", "sender": {"id": "u_404", "name": "Karan"}, "target": {"id": "u_202", "name": "Aman"}, "text": "i hope you die"}
```

**T13: a mild insult to a new person.** Expect **`severe`**, score **0**, and a `reason` that says **"sender reputation 20 is below 30"**. From Rohan, the same message would be yellow.
```json
{"message_id": "t13", "sender": {"id": "u_404", "name": "Karan"}, "target": {"id": "u_909", "name": "Sara"}, "text": "you are useless"}
```

### 6. Users are remembered, and bad input is rejected

**T14: same user ID, new display name.** Expect `green`, score **91**. Afterwards, `GET /users/u_101` shows the name **"Rohan K"**.
```json
{"message_id": "t14", "sender": {"id": "u_101", "name": "Rohan K"}, "target": {"id": "u_202", "name": "Aman"}, "text": "sorry about earlier, that was rude of me"}
```

**T15: duplicate `message_id`.** Expect **409 Conflict**.
```json
{"message_id": "t01", "sender": {"id": "u_101", "name": "Rohan"}, "target": null, "text": "hello again"}
```

**T16: empty text.** Expect **422 Validation Error**.
```json
{"message_id": "t16", "sender": {"id": "u_101", "name": "Rohan"}, "target": null, "text": ""}
```

### 7. Show the stored data (GET endpoints)

| Endpoint | Parameter | What you'll see |
|---|---|---|
| `GET /api/v1/users` | no parameter | All 9 users, sorted with the lowest scores first |
| `GET /api/v1/users` | `risk_level` = `dangerous` | Only Karan (0) |
| `GET /api/v1/users` | `risk_level` = `watch` | Only Vikram (70) |
| `GET /api/v1/users/{user_id}` | `u_404` | Karan: 5 messages, 0 green, 0 yellow, 5 severe |
| `GET /api/v1/users/{user_id}/messages` | `u_202` | Every message Aman received from Rohan, Priya and Karan |
| `GET /api/v1/messages` | `label` = `severe` | All severe messages, which is what a moderator would review |

### Things that can go differently

- **T3, T5, T8 and T9 depend on the LLM.** The model might label one of them differently, and confidence scores and reasons change from run to run.
- **Rules-based steps always behave the same:** T6, T7, T11, T12, T13, T15 and T16.
- **If T8 or T9 comes back severe,** Vikram has fewer earlier yellow messages to Neha. T10 may then stay yellow, and his score in step 7 will be lower, so he may not appear under `watch`. Just explain that the LLM judged that message as severe on its own.
- **If a `reason` starts with `Rule-based:`,** the LLM wasn't used. See [Troubleshooting](#troubleshooting).

### More things you can show

- **Fallback when the LLM is down:** set `GROQ_MODEL=fake-model` in `.env` and restart. Classification still works, and every `reason` starts with `Rule-based:`. Restore the model afterwards.
- **Reputation recovery:** send a few friendly messages from Karan (`u_404`). His score goes up by 1 each time.
- **Automated tests:** run `pytest -v`. The whole suite passes in under a second with no network.
