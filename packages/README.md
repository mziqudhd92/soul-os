# Packages

| Package | Path | Description |
|---------|------|-------------|
| **Kernel** | `soulos-core/` | FastAPI runtime — avatars, memory, dual-process chat, MCP (`mcp_server.py`). Docker image: `soulos-kernel`. |
| **Gateway** | `soulos-gateway/` | Cloud API gateway — Bearer keys, rate limits, MCP/REST proxy to kernel. |
| **SDK (TS)** | `soulos-sdk/ts/` | `@soulos/sdk` — HTTP client + SSE `sendMessage`. |
| **SDK (Python)** | `soulos-sdk/python/` | `soulos-sdk` — async client for bots and scripts. |
| **Soul Studio** | `soulos-studio/` | `pip install soulos-studio` — Soul Builder UI on port 8765. See [README](soulos-studio/README.md). |

Docs: [docs/README.md](../docs/README.md) · Agent upload: [docs/SOULOS_AGENT_CONTEXT.md](../docs/SOULOS_AGENT_CONTEXT.md)
