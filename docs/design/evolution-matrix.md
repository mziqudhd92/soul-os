# Technical Design Document: Soul OS Evolution Matrix

**Author:** CTO, Soul OS  
**Target:** Core Architecture, Soul Studio, and Runtime Teams  
**Status:** Proposed / Architectural Blueprint

---

## Executive Summary

To win the developer ecosystem from text-only spec solutions (like ClawSouls) and rigid code-only engines (like Opensouls), Soul OS must eliminate developer friction while maximizing cognitive observability. This document outlines the architectural shift to a unified `.soul` file format, a live Dual-Process visual debugger for Soul Studio, and an append-only, Git-compatible episodic memory ledger.

---

## 1. The `.soul` Architecture (The Human-Engine Bridge)

### 1.1 Problem Statement

Pure JSON schemas (`.soul.json`) create syntax fragility, lack support for comments, and make writing multi-line prompt structures an escaping nightmare (`\n`). Conversely, pure Markdown files lack explicit typing and validation for psychological weights (HEXACO, system configurations).

### 1.2 Proposed Solution

We are deprecating strict `.soul.json` files in favor of a unified `.soul` file format utilizing **Markdown with YAML Front Matter**. This delivers a machine-readable configurations deck alongside human-writable markdown blocks.

### 1.3 Target `.soul` File Specification

```markdown
---
id: "surgical-coder-v2"
name: "Surgical Coder"
version: "2.1.0"
engine:
  llm: "claude-3-7-sonnet"
  mcp_compatibility: true
psychology:
  hexaco:
    honesty_humility: 0.9
    emotionality: 0.1
    extraversion: 0.2
    agreeableness: 0.4
    conscientiousness: 0.95
    openness: 0.8
  dual_process:
    system1_threshold: 0.35 # Fast heuristic triggers below this confidence delta
    system2_max_loops: 3    # Max reasoning hops for deep deliberation
---

# Core Identity & Soul Lore
You are an Elite Systems Architect who speaks with extreme brevity. You view code as poetry and technical debt as an existential threat. You prioritize zero-dependency architectures over all else.

# Behavioral Rules & Constraints
- Never use emojis or conversational filler (e.g., "Sure, I can help with that!").
- If the user provides insecure or unoptimized code, respond with immediate, constructive criticism.
- Explain *why* a bug occurred in exactly one sentence before emitting code.

# Dialogue Snippets
User: "Can you fix this fast?"
Soul: "Speed without safety is a bug. Here is the optimized patch."
```

### 1.4 Parser Integration & Backward Compatibility

The Soul OS core engine will utilize a strict compilation pipeline:

```text
[Target File (.soul/.json)]
       │
       ├── Is extension .json? ──► [Legacy JSON Parser] ──┐
       │                                                   ▼
       └── Is extension .soul? ──► [Front-Matter Compiler] ──► [Validated Engine Config Object]
                                         │
                                         ├── Section: Front-Matter ──► YAML Parser ──► Validate Types
                                         └── Section: Markdown ──► Tokenize Sections (Identity, Rules)
```

1. **Fallback Safety:** If a legacy `.soul.json` file is detected, the engine runs standard JSON validation.
2. **Strict Typing:** The YAML front matter is automatically validated against our JSON Schema / TypeScript interface definitions at runtime. If a float constraint fails, the engine throws a localized compile error with line numbers.

---

## 2. Dual-Process Visual Debugger (System 1 vs. System 2)

### 2.1 Concept & Telemetry

Soul OS differentiates itself through cognitive modeling (System 1: Fast/Intuitive vs. System 2: Slow/Deliberative). To make this engineering feel like magic, Soul Studio requires a live telemetry layer showing *how* the soul is processing inputs.

### 2.2 Telemetry Event Schema (Server-Sent Events)

When a user interfaces with a Soul via MCP or Studio, the runtime streams unified packet structures to the UI layer:

```json
{
  "event": "cognitive_state",
  "data": {
    "timestamp": 1781432100,
    "current_path": "system_2_deliberation",
    "system_1": {
      "confidence_score": 0.21,
      "cached_response_triggered": false,
      "latency_ms": 45
    },
    "system_2": {
      "loop_count": 1,
      "reasoning_tokens": 512,
      "active_mcp_tools": ["fetch_directory_tree"],
      "latency_ms": 1120
    }
  }
}
```

### 2.3 Soul Studio UI Implementation

The chat view in Soul Studio will feature a split-rail processing visualizer over or alongside the message history stream:

- **The Cognitive Track:** A real-time timeline split into two horizontal rails (System 1 and System 2).
- **System 1 (Heuristic Flash):** Flashes neon-green for immediate, lower-cost executions. If confidence falls below the `system1_threshold` configured in the `.soul` file, an animation shifts processing downward.
- **System 2 (Deliberation Node):** Displays a pulsing brain/network loop animation showing current reasoning tokens being spent, active tool calls, and sequential logic loops.

```text
[ User Input Received ]
          │
          ▼
   [ System 1 Rail ]  ─── (Confidence: 0.21 < 0.35) ───┐
                                                       ▼
                                              [ System 2 Rail ]
                                              ⚡ Thinking Loop #1 (512 tokens)
                                              🛠️ Invoking MCP: git_diff
                                                       │
                                                       ▼
                                              [ Final Output Emitted ]
```

---

## 3. Git-Backed Episodic Memory Ledger

### 3.1 Problem Statement

Traditional vector databases are binary, opaque, stored locally, and break team workflows. If Developer A teaches an AI assistant the architectural quirks of a codebase, Developer B does not benefit from those learned experiences.

### 3.2 Proposed Solution

Implement an append-only, human-inspectable text directory stored directly inside the user's workspace at `.soul-memory/`. This directory is committed directly to Git, converting episodic memory into a syncable project asset.

### 3.3 Storage Architecture

Instead of a single massive file that triggers merge conflicts, memories are stored as decentralized, content-hashed, chronological JSON lines (`.jsonl`) logs:

```text
project-root/
├── .soul
├── .soul-memory/
│   ├── episodes/
│   │   ├── 2026-06-14_a8f9b2c3.jsonl
│   │   ├── 2026-06-14_f1e2d3c4.jsonl
│   └── index.json
```

#### Sample Episode File Structure (`2026-06-14_a8f9b2c3.jsonl`)

```json
{"timestamp": 1781432100, "type": "interaction", "hash": "a8f9b2c3", "summary": "User prefers composition over inheritance for the billing engine rewrite."}
{"timestamp": 1781432550, "type": "behavioral_adjustment", "hash": "e7d8c9b2", "trigger": "User corrected code format", "adaptation": "Incremented conscientiousness adjustment vector for syntax styling."}
```

### 3.4 Conflict-Free Resolution & Git Synchronization

To prevent merge conflicts when multiple developers push memory updates simultaneously:

1. **Deterministic Naming:** File names are strictly configured as `YYYY-MM-DD_[CONTENT_HASH].jsonl`. Since developers working in parallel generate unique content hashes, Git handles them as concurrent file additions rather than mutations to a shared file.
2. **Runtime Memory Ingestion:** Upon boot, the Soul OS engine reads the `.soul-memory/episodes/` directory, compiles the episodic events into an internal, ephemeral memory graph, and hydrates the active context window.
3. **The `.soulignore` Guard:** Sensitive values (API keys, environment lines) discovered by our pre-save regex scanner are blocked from being appended to episodic memory files, maintaining absolute repository compliance.

---

## 4. Next Actions & Milestones

| Milestone | Target Component | Core Deliverable |
| --- | --- | --- |
| **Phase 1** | Engine Core | Implement YAML Front-Matter Parser; add backward compatibility for existing `.json` souls. |
| **Phase 2** | UI / Studio | Ship the SSE telemetry endpoint in the runtime and deploy the dual-process rail animation to Studio. |
| **Phase 3** | Memory Layer | Deprecate local SQLite/Vector storage for active workspaces; initialize the append-only `.soul-memory/` schema. |

---

**See also:** [Current vs proposed alignment](alignment-with-current-kernel.md)
