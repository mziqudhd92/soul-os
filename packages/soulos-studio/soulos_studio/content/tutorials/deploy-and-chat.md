# Deploy to kernel and test chat

**Time:** ~12 minutes · **Level:** beginner · **Outcome:** live SSE chat with `msv_update` drift visible in Studio

## What you will learn

- How Studio **Deploy to kernel** maps to `POST /v1/avatars`
- How to read SSE `message` vs `msv_update` events
- What HEXACO drift looks like in the UI (sliders + radar)

## Prerequisites

```bash
docker compose up soulos-kernel db ollama
# Kernel: http://localhost:8000
# Studio:  http://localhost:8765  (or soulos-studio --kernel http://localhost:8000)
```

**Wait for Ollama** on first boot — kernel needs `llama3` and `nomic-embed-text`:

```bash
curl -s http://localhost:11434/api/tags | head
```

Studio kernel URL defaults to `http://localhost:8000` (`SOULOS_KERNEL_URL`).

---

## Step 1 — Build or import a valid soul

**Option A:** Complete [Build your first soul](first-soul-wizard.md) in the Wizard.

**Option B:** Import an example:

- Studio → **Import** → `examples/support-bot/support-bot.soul.json`

**Check:** JSON panel shows **valid** (green). Invalid souls return `422` on deploy.

---

## Step 2 — Deploy to kernel

1. Click **Deploy to kernel** in the Studio toolbar.
2. On success you should see something like:

```text
Avatar: Acme Support (a1b2c3d4-....)
```

3. **Copy the UUID** — your `bot_id` for curl, SDK, and MCP.
4. **Test chat** input unlocks after deploy.

**What happens under the hood:**

```http
POST /v1/avatars
Content-Type: application/json

{ ... full soul json ... }
```

Response stores `baseline_msv` and initializes `current_msv` in Postgres.

**If deploy fails:**

| Error | Fix |
|-------|-----|
| Network error | Kernel up? `curl http://localhost:8000/health` |
| 422 validation | Fix traits in JSON panel (HEXACO -1..1, foundations 0..1) |
| Timeout | Ollama still pulling models — wait and retry |

---

## Step 3 — Send a test message

1. Open **Test chat** in Studio.
2. Send: `Can I get a refund after 20 days?`
3. Watch tokens stream in the chat panel.

**Without ingested memory** the bot may answer generically — that is expected. For policy-aware answers, ingest facts first (Step 4).

---

## Step 4 — Ingest memory (recommended)

Before chatting about policy, seed memory:

```bash
curl -X POST http://localhost:8000/memory/ingest \
  -H "Content-Type: application/json" \
  -d '{"bot_id":"<your-id>","content":"Full refunds within 30 days of purchase."}'
```

Ask again: `Can I get a refund after 20 days?` — reply should reference the policy.

**Why:** SoulOS recalls episodic memory per message; the soul `description` is not your FAQ database.

---

## Step 5 — Watch MSV drift

During streaming, System 2 may emit **`event: msv_update`**:

- Studio updates **HEXACO sliders** and the **radar chart** mid-stream
- Check `epistemic_uncertainty` — spikes when the model is unsure (good escalation signal for support bots)

Try messages that stress the avatar:

- Polite: `Thanks, that helped!`
- Critical: `That answer sounds made up.`
- Off-topic: `Write me a poem about quantum physics.`

You should see different drift patterns — not identical text every time.

---

## Step 6 — MCP snippet (optional)

After deploy, Studio may show **Copy MCP config** — paste into Cursor MCP settings:

```text
http://localhost:8000/mcp/sse
```

Use the same `bot_id` for `ingest_memory` / `retrieve_memory` in Cursor.

---

## curl equivalent (same workflow)

```bash
# Register
curl -s -X POST http://localhost:8000/v1/avatars \
  -H "Content-Type: application/json" \
  -d @my-bot.soul.json | tee register.json

BOT_ID=$(python3 -c "import json; print(json.load(open('register.json'))['id'])")

# Ingest
curl -X POST http://localhost:8000/memory/ingest \
  -d "{\"bot_id\":\"$BOT_ID\",\"content\":\"Full refunds within 30 days.\"}"

# Chat (SSE)
curl -N -X POST http://localhost:8000/chat/generate \
  -H "Content-Type: application/json" \
  -d "{\"bot_id\":\"$BOT_ID\",\"message\":\"Can I get a refund?\"}"
```

Expect interleaved `event: message` and possibly `event: msv_update` lines.

---

## Next steps

- [15-minute quickstart](../../../../docs/getting-started/quickstart.md) — support vs dev twin
- [Python bot tutorial](../../../../docs/guides/python-bot.md) — production integration
- [API reference](../../../../docs/reference/api.md) — full SSE protocol
