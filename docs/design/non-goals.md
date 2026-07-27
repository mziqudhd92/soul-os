# Near-term non-goals

SoulOS focuses on **identity + episodic memory as a hybrid sidecar**. The following are intentionally **out of scope** for the near-term roadmap (unless a concrete adopter forces a thin slice).

| Non-goal | Why |
|----------|-----|
| Public community `.soul.json` registry | Licensing risk (ClawSouls removed); grow **in-repo MIT SoulPacks** instead |
| Storage SPI for Pinecone / Milvus / Qdrant / Redis memory tiers | Premature abstraction; Postgres + pgvector is the product bet |
| Kafka / Redis PubSub event bus | Apps own webhooks/events; kernel is request/response + SSE |
| Go / Rust SDKs | Python + TypeScript cover AI and web; OpenAPI is the contract |
| Full API RBAC role matrix | Tenant isolation via `account_id` / `owner_id` is the enterprise baseline |
| In-kernel PII scrubbing (e.g. Presidio) | Keep scrubbing in the app or a sidecar; avoid supply-chain/latency in the kernel |
| Replacing LangChain / AutoGen / Vercel AI as an agent runtime | Provide thin adapters; SoulOS is the state/persona layer |

## Related

- [Architecture overview](../guides/architecture-overview.md)
- [SoulPacks](../guides/persona-packs.md)
- [Multi-agent Phase A](../guides/multi-agent-teams.md) (app orchestration; no kernel teams API yet)
