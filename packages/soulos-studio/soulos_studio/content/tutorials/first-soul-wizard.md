# Build your first soul with the Wizard

Create a validated `.soul.json` without hand-editing JSON.

## Step 1 — Open the Wizard

1. In SoulOS Studio, click **Wizard** in the top menu.
2. You will see an 8-step guided flow.

## Step 2 — Name your avatar

Give your avatar a clear name (e.g. **Site Support** or **Dev Twin**). This becomes the `name` field in your soul file.

## Step 3 — Role and description

- **Role** — short job title (e.g. Customer Support Agent).
- **Description** — this is the behavioral system prompt: tone, boundaries, escalation rules.

Tip: write the description as you would a system prompt, but leave personality to HEXACO sliders.

## Step 4 — Attachment style

Pick how your avatar relates under stress:

| Style | Effect |
|-------|--------|
| Secure | Warm, consistent, low anxiety |
| Anxious-Preoccupied | Seeks reassurance, sensitive to rejection |
| Dismissive-Avoidant | Independent, may seem distant |

## Step 5 — HEXACO traits

Tune Honesty, Emotionality, eXtraversion, Agreeableness, Conscientiousness, and Openness (0–1). These define baseline personality in `baseline_msv.hexaco`.

## Step 6 — Morals and drives

Moral foundations shape ethical choices. Drives shape curiosity, autonomy, and social approval. Set **epistemic uncertainty** higher if the avatar should admit uncertainty more often.

## Step 7 — Inner monologue

A short default internal thought (telemetry, not always shown to users).

## Step 8 — Review and create

Click **Create soul**. The wizard loads your soul into the Studio editor. Use **Export** to download `your-bot.soul.json`.

## Next

- Open the **Tutorial** tab → **Deploy and test chat**
- Open the **Docs** tab → **Soul Builder UI** for export and import details
