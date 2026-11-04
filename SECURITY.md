# Security policy

## Supported versions

| Version | Supported |
|---------|-----------|
| `main` branch | Yes |
| Released tags | Best effort |

## Reporting a vulnerability

**Do not** open public GitHub issues for security bugs.

Email or contact the maintainers privately with:

- Description and impact
- Steps to reproduce
- Suggested fix (if any)

We aim to acknowledge reports within a few business days.

## Deployment expectations

- **Self-host (`REQUIRE_AUTH=0`)**: intended for local development only — do not expose the kernel port publicly without gateway auth. MCP endpoints (`/mcp/*`) have the same power as REST (memory ingest, avatar registration, MSV updates).
- **Cloud (`REQUIRE_AUTH=1`)**: expose only `soulos-gateway`; rotate `GATEWAY_SECRET` and API keys in production. MCP is available at `/mcp/sse` through the gateway with Bearer API keys.
- **Soul Studio**: local dev tool; do not expose port 8765 publicly without access control.

See [docs/deployment/self-hosted.md](docs/deployment/self-hosted.md).

## MCP blast radius (draft)

MCP tools mirror REST privileges. Treat MCP SSE URLs like admin APIs.

| Surface | Risk if exposed publicly |
|---------|--------------------------|
| `ingest_memory` | Arbitrary fact injection into any accessible bot |
| `register_avatar` | New avatar creation under tenant scope |
| `update_cognitive_state` | Direct MSV manipulation |
| `retrieve_memory` / resources | Exfiltration of episodic memory |
| `/hybrid/*` (REST) | Prompt building + memory ingest without chat auth |
| Conversation shared memory | Cross-bot fact injection within tenant conversation_id |
| `POST /v1/handoffs` | Multi-bot memory writes; require idempotency + auth in production |

**Mitigation:** gateway-only exposure, API keys, network policies, never `:8000` with `REQUIRE_AUTH=0` on the public internet.

Full blast-radius table and Anthropic MCP alignment notes: see Phase 4 section below and [docs/guides/mcp.md](docs/guides/mcp.md).

## MCP blast radius (full)

| Tool / resource | Data accessed | Write scope | Anthropic alignment |
|-----------------|---------------|-------------|---------------------|
| `ingest_memory` | Episodic store | Insert for `bot_id` | Tool — matches expected side-effect disclosure |
| `retrieve_memory` | pgvector | Read | Tool — read-only recall |
| `get_identity` | `bots` row MSV | Read | Resource `soul://identity/{bot_id}` |
| `register_avatar` | `bots` | Insert | Tool — high privilege; gate behind auth |
| `list_avatars` | `bots` | Read list | Tool — tenant-scoped when auth on |
| `update_cognitive_state` | `current_msv` | Update | Tool — equivalent to `/state/update` |
| `forget_memory` | Episodic store | Delete by content match | Tool — GDPR-style erase |
| `delete_session` | Session memories + turn_sessions | Delete | Tool — session wipe |
| `ensure_avatar` | `bots` | Insert if missing | Tool — idempotent bootstrap |
| `hybrid_prepare` / `hybrid_complete` | Identity + memory + optional reflect | Read + write | Tool — same privilege as REST hybrid |
| `memory://episodic/{bot_id}` | Memories | Read resource | Resource URI pattern |
| Chat streaming | — | **Not on MCP** | Use REST/SDK — intentional gap |

**Gaps vs Anthropic MCP expectations:** no resource subscription lifecycle; Streamable HTTP sessions are in-memory (use sticky routing or single worker for `/mcp`).

### Bidirectional MCP threat model (hardened)

| Threat | Control |
|--------|---------|
| Cross-tenant IDOR via `bot_id` in tools/resources | Task-local `SecurityContext` (ContextVar) + `verify_bot_access`; strict ID/URI validation (`runtime/mcp_ids.py`) |
| Gateway Host mismatch | `SOULOS_MCP_HOST_ALLOWLIST` empty by default (docker/gateway Hostnames work); set explicitly for browser-facing kernels |
| MCP episodic/conversation writes | Stored wrapped as `<untrusted_memory trust_level="external_mcp">` |
| `confirm_force`-style LLM bypass | Admin MSV write via `mcp:admin:msv_write` (gateway API-key `scopes` → `X-SoulOS-Scopes`) / `SOULOS_MCP_ADMIN_TOOLS`; tool omitted from `list_tools` otherwise; clients cannot forge scopes through the gateway |
| Memory poisoning / handoff escalation | MCP writes tagged `trust_level=external_mcp`; `allowed_handoff_targets` graph; consolidate `too_early` + rate limits |
| Streamable HTTP session hijack | `Mcp-Session-Id` bound to auth principal hash; Origin/Host allowlists; 256KB body cap; gateway stream caps |
| Outbound SSRF / rug-pull | DNS-then-block private/link-local; `follow_redirects=False`; `schema_sha256` pin re-checked via `tools/list` before each `tools/call`; `description_override`; untrusted output wrap; `auth_env_key` |

**Never expose `:8000` with `REQUIRE_AUTH=0` publicly.**
