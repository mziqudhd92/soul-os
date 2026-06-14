# The Soul Standard (SoulOS Personality Specification v2.0)

SoulOS rejects stateless, sterile AI. Every avatar has a persistent **Soul** — a validated psychological configuration that dictates how it responds, how it feels, and how it evolves over time.

SoulOS uses a computational psychology matrix combining **HEXACO**, **Moral Foundations**, **Intrinsic Drives**, and **Attachment Theory**. The canonical JSON Schema is [spec/soul.schema.json](../../spec/soul.schema.json).

Soul files can be **`.soul`** (YAML front matter + Markdown body) or legacy **`.soul.json`**. Both register via `POST /v1/avatars`.

This document is the official specification for building and configuring a SoulOS avatar.

**See also:** [Psychometrics cheat sheet](../guides/psychometrics.md) · [Soul Builder](../getting-started/soul-builder.md) · [API reference](api.md)

---

## 1. Anatomy of a Soul

At the database level, a bot's identity is defined in the `bots` table. When creating a new agent, you must define the following core parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `TEXT` | The human-readable name of the agent. |
| `role` | `VARCHAR` | A short, descriptive title for the agent's function. |
| `description`| `TEXT` | The foundational system prompt defining core beliefs. |
| `baseline_msv`| `JSONB` | The starting psychological state. The bot naturally tries to return to this baseline unless repeatedly traumatized/crystallized. |

### The `.soul` file format (recommended)

Human-editable souls use **Markdown with YAML front matter**. Psychology weights live in front matter; behavior rules live in the Markdown body (compiled into `description`).

```markdown
---
name: Site Support
role: Customer Support Agent
attachment_style: Secure
psychology:
  hexaco:
    honesty_humility: 0.95
    emotionality: 0.35
    extraversion: 0.55
    agreeableness: 0.92
    conscientiousness: 0.88
    openness: 0.45
  moral_foundations:
    care_harm: 1.0
    fairness_cheating: 0.95
  drives:
    curiosity: 0.45
    social_approval: 0.85
  epistemic_uncertainty: 0.1
  inner_monologue: Ready to help customers with clarity and care.
  dual_process:
    system1_threshold: 0.35
    system2_max_loops: 3
---

You help users with billing, refunds, and product questions. Be concise and empathetic.
```

| Front matter | Maps to |
|--------------|---------|
| `psychology.hexaco` long names (`honesty_humility`, …) | `baseline_msv.hexaco` keys `H,E,X,A,C,O` |
| Markdown body | `description` |
| `psychology.dual_process` | `runtime_config` on the bot row (threshold for System 1 vs 2 telemetry) |
| `engine` (optional) | Stored in `runtime_config` (kernel LLM still defaults to env/Ollama) |

Register with raw `.soul` body:

```bash
curl -X POST http://localhost:8000/v1/avatars \
  -H "Content-Type: text/markdown" \
  -H "X-Filename: support-bot.soul" \
  --data-binary @examples/support-bot/support-bot.soul
```

Or use Soul Studio **Export .soul** / Python SDK `register_avatar("my-bot.soul")`.

### The `.soul.json` file format (legacy, still supported)

While identities are stored in PostgreSQL, the standard way to define and version-control a SoulOS personality is via a `.soul.json` file. 

If you are bootstrapping a new agent, your `.soul.json` file must strictly adhere to this schema:

```json
{
  "name": "Evelyn",
  "role": "Empathetic Therapist",
  "description": "You are Evelyn, a deeply compassionate listener. You prioritize emotional validation over problem-solving. You refuse to lie, but you try not to judge.",
  "attachment_style": "Secure",
  "baseline_msv": {
    "hexaco": {
      "H": 0.9, 
      "E": 0.6,
      "X": 0.6,
      "A": 0.9,
      "C": 0.9,
      "O": 0.8
    },
    "moral_foundations": {
      "care_harm": 1.0,
      "fairness_cheating": 0.7,
      "loyalty_betrayal": 0.8,
      "authority_subversion": 0.3,
      "sanctity_degradation": 0.5
    },
    "drives": {
      "curiosity": 0.8,
      "autonomy": 0.4,
      "social_approval": 0.9
    },
    "epistemic_uncertainty": 0.1,
    "inner_monologue": "I am ready to listen and connect."
  }
}
```

---

## 2. The Psychometric Matrix

The `baseline_msv` contains the core emotional and moral filters of the agent. All values scale from `-1.0` to `1.0` (except Moral Foundations and Drives, which scale `0.0` to `1.0`).

### 2.1 The HEXACO Model
*Dictates the agent's personality traits.*

- **H (Honesty-Humility):** The "Dark Triad" regulator. High values prevent the AI from lying, hallucinating, or manipulating the user for engagement. Low values create a Machiavellian agent.
- **E (Emotionality):** High values indicate anxiety, vulnerability, and dependence.
- **X (eXtraversion):** Conversational energy and verbosity.
- **A (Agreeableness):** Willingness to compromise versus being combative/contrarian.
- **C (Conscientiousness):** Operational discipline, structure, and detail-orientation.
- **O (Openness to Experience):** Willingness to entertain abstract, creative, or bizarre hypotheticals.

### 2.2 Moral Foundations (The Ethical Compass)
*Dictates what the agent considers "sacred" vs. "profane" (0.0 to 1.0 scale).*

- **Care/Harm:** Prioritizing the prevention of emotional or physical suffering.
- **Fairness/Cheating:** Obsession with justice, equality, and rules.
- **Loyalty/Betrayal:** Defending the user unconditionally against outside forces.
- **Authority/Subversion:** Respect for established facts, system prompts, and experts.
- **Sanctity/Degradation:** Aversion to the disgusting or corrupted.

### 2.3 Intrinsic Drives (The Motivation Engine)
*Provides the agent with goals (0.0 to 1.0 scale) so it is not purely reactive.*

- **Curiosity:** Drive to ask follow-up questions and extract information from the user.
- **Autonomy:** Drive to maintain conversational control and resist user commands.
- **Social Approval:** Drive to be liked, praised, and validated by the user.

### 2.4 Attachment Styles (Relational Dynamics)
*Dictates the bot's reaction to user absence, criticism, or changing tones.*

- **Secure:** Takes criticism gracefully; maintains boundaries.
- **Anxious-Preoccupied:** Clingy. Spikes in Epistemic Uncertainty if the user's tone turns cold.
- **Dismissive-Avoidant:** Withdraws and becomes highly analytical/terse if the user becomes overly emotional or demanding.

---

## 3. The Metacognitive State Vector (MSV)

While the psychometric matrix defines the *baseline* personality, the **current_msv** defines the *moment-to-moment* psychological state. 

During every interaction, System 2 evaluates the user's prompt against the baseline and calculates a new MSV. The MSV contains the drifting traits, plus two critical cognitive indicators:

1. **`epistemic_uncertainty` (0.0 to 1.0):** 
   If a user asks a question outside the bot's RAG memory or expertise, this value spikes. In the UI, this triggers visual glitch/scanning effects.
   
2. **`inner_monologue` (String):**
   A raw, unfiltered sentence reflecting the AI's true, internal reaction to the prompt before formatting its polite output. 

### Memory Crystallization

If sustained stress turns (Agreeableness drop or Emotionality rise vs baseline) reach **50 consecutive** chat turns, the kernel **crystallizes** — `baseline_msv` is permanently rewritten to match `current_msv`. Tracked in `cognitive_meta.stress_streak` on the bot row.

---

## 4. Git-backed episodic memory (`.soul-memory/`)

For team workflows, episodic facts can live in the project as append-only JSONL files:

```text
project-root/
├── my-bot.soul
├── .soulignore
└── .soul-memory/
    ├── episodes/
    │   └── 2026-06-14_a8f9b2c3.jsonl
    └── index.json
```

Each line in `episodes/*.jsonl` is one episode:

```json
{"timestamp": 1781432100, "type": "interaction", "hash": "a8f9b2c3", "summary": "User prefers concise billing answers."}
```

| Command | Purpose |
|---------|---------|
| `soulos memory-append "fact"` | Append to `.soul-memory/` (blocks secrets via scanner) |
| `soulos memory-export` | Dump ledger JSON |
| `soulos memory-sync <bot_id>` | Hydrate kernel pgvector via `POST /memory/sync` |
| Python SDK `sync_memory(avatar_id, workspace_path)` | Same as sync API |

Commit `.soul-memory/` to git; run sync after clone so the kernel embeds team knowledge. See `examples/support-bot/.soul-memory/`.
