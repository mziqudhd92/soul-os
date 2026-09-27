# soulos-sdk

Client libraries for the SoulOS kernel / gateway.

| Language | Path | Install |
|----------|------|---------|
| TypeScript | `ts/` | `npm install` / workspace `@soulos/sdk` |
| Python | `python/` | `pip install -e packages/soulos-sdk/python` |

Self-host: `baseUrl: 'http://localhost:8000'` · Cloud: `apiKey` (+ optional `baseUrl` for local gateway).

**Hybrid turn contracts:** Python `merge_contract_into_system_prompt` / TS `mergeContractIntoSystemPrompt`; `complete_turn` / `completeTurn` accept `filled_slots`, `expected_version`, auto `idempotency_key` in contract mode. Guide: [turn-contracts.md](../../docs/guides/turn-contracts.md).

**Phase B handoffs:** Python `handoff_to` (prefers `POST /v1/handoffs`) · TS `handoffTo` / `conversationSessionId` / `roleExternalKey`. Guide: [multi-agent-teams.md](../../docs/guides/multi-agent-teams.md).

Docs: [Quickstart](../../docs/getting-started/quickstart.md) · [Python bot guide](../../docs/guides/python-bot.md)
