# Build your first soul with the Wizard

**Time:** ~15 minutes · **Level:** beginner · **Outcome:** a validated `my-bot.soul` or `my-bot.soul.json` you can deploy or hand to the Python SDK

## What you will learn

- How SoulOS splits **behavior** (`description` / Markdown body) from **personality** (HEXACO sliders)
- What each Wizard step writes into the soul file
- How to **Export JSON** or **Export .soul** for `POST /v1/avatars` or `register_avatar`

## Before you start

```bash
git clone https://github.com/mziqudhd92/soul-os.git && cd soul-os
docker compose up --build
# Studio: http://localhost:8765
```

You do **not** need the kernel running to finish the Wizard and **Export** — only for **Deploy to kernel**.

---

## Step 1 — Open the Wizard

1. Open http://localhost:8765
2. Click **Wizard** in the header (or toolbar).
3. You should see **8 steps** and a progress indicator.

**If Studio won’t load:** `pip install -e packages/soulos-studio && soulos-studio --port 8765`

---

## Step 2 — Name your avatar

**Field:** `name` in the soul file.

Pick something users will recognize — not a model name.

| Good | Avoid |
|------|--------|
| Acme Support | GPT-4 Bot |
| Dev Twin | Assistant v2 |

**Check:** the live JSON panel on the right updates `name` as you type.

---

## Step 3 — Role and description

**Fields:** `role`, `description`

- **Role** — short job title (≤ one line). Example: `Customer Support Agent`
- **Description** — behavioral rules: tone, boundaries, escalation. This replaces most of your old **system prompt**.

**Write description like this:**

```text
You help with orders, refunds, and product questions.
Be concise and empathetic. Cite policy when unsure.
Escalate billing disputes you cannot resolve.
```

**Do not** paste your entire FAQ here — ingest FAQ as **memory** later (kernel RAG).

**Check:** JSON shows non-empty `role` and `description`. Validation badge should stay green.

---

## Step 4 — Attachment style

**Field:** `attachment_style`

How the avatar reacts when the user is cold, critical, or demanding:

| Style | Use when |
|-------|----------|
| **Secure** | Default for support and dev assistants |
| **Anxious-Preoccupied** | Companion bots that should seek reassurance |
| **Dismissive-Avoidant** | Technical bots that withdraw under emotional pressure |

Support bots: usually **Secure**.

---

## Step 5 — HEXACO traits

**Field:** `baseline_msv.hexaco` (H, E, X, A, C, O) — range **-1.0 to 1.0**

| Trait | Support bot (starting point) | What it does |
|-------|------------------------------|--------------|
| **H** Honesty | 0.85 – 0.95 | Less fabrication; admits uncertainty |
| **E** Emotionality | 0.3 – 0.5 | Calm under stress |
| **X** eXtraversion | 0.4 – 0.6 | Reply length / energy |
| **A** Agreeableness | 0.8 – 0.95 | Warmth vs bluntness |
| **C** Conscientiousness | 0.7 – 0.9 | Structured answers |
| **O** Openness | 0.4 – 0.6 | Creative vs literal |

Tune one slider and watch the **radar chart** — that shape is your baseline personality.

Deep reference: [HEXACO cheat sheet](../../../../docs/guides/psychometrics.md)

---

## Step 6 — Moral foundations and drives

**Fields:** `moral_foundations`, `drives` (0.0 – 1.0)

**Moral foundations** — what the avatar treats as sacred:

- **care_harm** ↑ → more empathy (support: high)
- **fairness_cheating** ↑ → rule-bound refunds and policy language
- **authority_subversion** ↑ → cites docs and official process (dev twin: high)

**Drives** — motivation, not just reactivity:

- **curiosity** ↑ → more follow-up questions
- **autonomy** ↑ → sets boundaries (“I won’t do that without explaining why”)
- **social_approval** ↑ → softer tone, seeks validation

**Epistemic uncertainty** (0–1) — baseline willingness to say “I’m not sure.” Support bots often start around **0.15–0.25**.

---

## Step 7 — Inner monologue

**Field:** `baseline_msv.inner_monologue`

One sentence of **internal state at boot** — used for telemetry and System 2 reflection, not shown to users by default.

Example: `Ready to help with clarity and fairness.`

---

## Step 8 — Review and create

1. Read the full JSON in the preview panel — confirm **valid** (no red errors).
2. Click **Create soul** — Wizard loads values into the main Studio editor.
3. Click **Export JSON** (`your-name-slug.soul.json`) or **Export .soul** (YAML + Markdown).
4. Optional: commit `.soul-memory/` and sync with `soulos memory-sync <bot_id>`.

**Verify export:**

```bash
python3 -c "import json, jsonschema; s=json.load(open('acme-support.soul.json')); ..."
# Or register directly:
curl -s -X POST http://localhost:8000/v1/avatars \
  -H "Content-Type: application/json" \
  -d @acme-support.soul.json | python3 -m json.tool
```

You should get JSON with an `id` field — that is your `bot_id`.

---

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Whole FAQ in `description` | Short policy tone in soul; FAQ via `memory/ingest` |
| All HEXACO at 1.0 | Traits interact; start from presets above |
| Export without validating | Fix errors in JSON panel before deploy |
| Same soul for support + dev twin | One persona = one soul file + one `bot_id` |

---

## Next steps

1. **Studio:** Tutorials → **Deploy and test chat**
2. **Code:** [Python bot tutorial](../../../../docs/guides/python-bot.md) — recommended integration path
3. **curl only:** [Quickstart Path A](../../../../docs/getting-started/quickstart.md#path-a)
