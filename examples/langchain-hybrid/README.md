# LangChain + SoulOS hybrid

Thin example: use SoulOS as the **persona/memory** layer while LangChain (or any LLM) generates the reply.

## Install

```bash
pip install langchain-core httpx
# From repo: PYTHONPATH=packages/soulos-sdk/python
```

## Run

```bash
# Kernel with mock bridge
docker compose -f docker-compose.sidecar.yml --profile bridge-mock up -d

python3 examples/langchain-hybrid/run_turn.py
```

## Pattern

1. `SoulHybridClient.prepare_turn` → `system_prompt` + memories  
2. LangChain `ChatPromptTemplate` / your chat model with that system prompt  
3. `SoulHybridClient.complete_turn` with a short summary  

SoulOS does **not** replace LangChain agents/tools — it manages identity and episodic memory.
