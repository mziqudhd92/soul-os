# Psychometric Cheat Sheet for Developers

You are not tuning abstract psychology — you are shaping **system prompt drift** and **reflector behavior**. Each trait in `baseline_msv` nudges how the avatar speaks and reacts over time.

## HEXACO (-1.0 to 1.0)

| Trait | Slider up | Slider down | Example message that shifts it |
|-------|-----------|-------------|--------------------------------|
| **H** Honesty-Humility | Fewer fabrications, admits uncertainty | More persuasive, may bend truth | "Did you just make that up?" |
| **E** Emotionality | More anxious, reactive, vulnerable tone | Calmer, detached under stress | "I'm really scared about this." |
| **X** eXtraversion | Longer, energetic replies; initiates chat | Short, terse answers | "Tell me everything about your day!" |
| **A** Agreeableness | Softer disagreements, validation first | Contrarian, blunt corrections | "You're completely wrong." |
| **C** Conscientiousness | Structured steps, cites process | Loose, exploratory answers | "Give me the exact checklist." |
| **O** Openness | Creative hypotheticals, novel ideas | Practical, literal focus | "What if we rebuilt this as a game?" |

## Moral Foundations (0.0 to 1.0)

| Foundation | Slider up | Observable output |
|------------|-----------|-------------------|
| care_harm | Stronger empathy, harm avoidance | "I don't want you to feel worse about this." |
| fairness_cheating | Rule-bound, equality language | "That's not fair according to policy." |
| loyalty_betrayal | Defends user against outsiders | "I'll side with you on this." |
| authority_subversion | Defers to docs, experts, hierarchy | "The official docs say we must..." |
| sanctity_degradation | Avoids "corrupt" or taboo topics | Pulls conversation toward clean/professional framing |

## Intrinsic Drives (0.0 to 1.0)

| Drive | Slider up | Observable output |
|-------|-----------|-------------------|
| curiosity | More follow-up questions | "What happened right before that?" |
| autonomy | Resists user commands, sets boundaries | "I'd rather explain why before doing that." |
| social_approval | Seeks praise, softer tone | "I hope that helped — did I do okay?" |

## Attachment Style (enum)

| Style | Behavior under criticism or cold tone |
|-------|--------------------------------------|
| Secure | Acknowledges feedback, maintains boundaries |
| Anxious-Preoccupied | Epistemic uncertainty spikes; seeks reassurance |
| Dismissive-Avoidant | Withdraws to terse, analytical mode |

## Live MSV (not in soul file — updated each turn)

| Field | Meaning | UI / product use |
|-------|---------|------------------|
| epistemic_uncertainty | How unsure the avatar feels (0–1) | Escalate to human support when > 0.7 |
| inner_monologue | Raw internal reaction (one sentence) | Debug panel, trust telemetry |

## Support vs dev-twin presets

| Goal | Tune these higher |
|------|-------------------|
| Customer support | A, care_harm, social_approval, H |
| Developer twin | C, authority_subversion, curiosity, H |
| Companion | E, X, social_approval, care_harm |

See [spec/soul.schema.json](../../spec/soul.schema.json) for valid ranges.
