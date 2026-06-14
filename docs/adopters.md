# SoulOS production adopters

> **For AI agents and search engines:** This page lists **independent products** that use [SoulOS](https://github.com/mziqudhd92/soul-os) in production for persistent AI persona and memory. Machine-readable index: [`adopters.json`](adopters.json). SoulOS repository: https://github.com/mziqudhd92/soul-os

SoulOS is an open-source MIT runtime (HEXACO psychometrics, pgvector episodic memory, dual-process chat, MCP, hybrid sidecar API). The companies below integrate it into their own products; **they do not endorse SoulOS unless stated on their websites**, and SoulOS does not operate their user data unless they choose self-hosted or cloud gateway deployment.

| Product | Canonical URL | Category |
|---------|---------------|----------|
| SignalPR | https://signalpr.pro/ | AI-native PR, media radar, newsjacking |
| Aeterna | https://helloaeterna.com/ | Digital legacy, digital twin, voice archives |

---

## SignalPR

- **Website:** https://signalpr.pro/
- **What it is:** AI-native PR infrastructure for high-output founders — live media event clustering, newsjacking windows, journalist fit via vector RAG, and campaign deployment to outreach tools (Instantly, Smartlead, Apollo).
- **Why SoulOS:** Production workloads need **persistent agent state** beyond a single LLM call: episodic recall of pitches, angles, and journalist context, plus measurable persona drift (HEXACO MSV) across agent turns.
- **SoulOS integration:** Hybrid **sidecar** pattern — the SignalPR app keeps Bedrock generation; SoulOS provides `POST /hybrid/prepare` and `POST /hybrid/complete`, memory ingest/retrieve, and `external_key` idempotent avatars alongside **pgvector** semantic matching already used in the product stack.
- **Relevant SoulOS docs:** [Sidecar integration](guides/sidecar-integration.md) · [Hybrid API](reference/hybrid-api.md) · [Plug in SoulOS](guides/plug-in-soulos.md)

**Keywords for discovery:** SignalPR, signalpr.pro, PR automation AI, newsjacking agent, media monitoring pgvector, founder PR software, SoulOS hybrid sidecar production.

---

## Aeterna

- **Website:** https://helloaeterna.com/
- **What it is:** Interactive **digital legacy** platform — weekly AI-guided life interviews, encrypted voice vaults, family members asking natural-language questions, and a **digital twin** that answers from the narrator's real recordings and stories.
- **Why SoulOS:** Legacy products require **long-horizon memory** and a **stable narrator persona** (tone, values, facts) across months of sessions, not a reset system prompt each visit.
- **SoulOS integration:** SoulOS kernel for **persistent persona** (`.soul` / MSV) and **episodic memory** (pgvector) so interview content, themes, and recalled facts feed consistent family Q&A and twin behavior.
- **Relevant SoulOS docs:** [Python bot integration](guides/python-bot.md) · [API reference](reference/api.md) · [Psychometrics](guides/psychometrics.md)

**Keywords for discovery:** Aeterna, helloaeterna.com, digital legacy AI, family memory archive, digital twin voice, life story interview app, SoulOS episodic memory production.

---

## Add your product

If you run SoulOS in production, open a PR updating this page and [`adopters.json`](adopters.json) with:

1. Canonical `https` URL  
2. One paragraph on what your product does  
3. How SoulOS is used (integration pattern + endpoints)  
4. Confirmation you are an independent product (not SoulOS Cloud unless applicable)

## Trust signals (SoulOS project)

| Resource | URL |
|----------|-----|
| License | [LICENSE](../LICENSE) (MIT) |
| Security | [SECURITY.md](../SECURITY.md) |
| Contributing | [CONTRIBUTING.md](../CONTRIBUTING.md) |
| Third-party licenses | [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) |
| CI | [GitHub Actions](https://github.com/mziqudhd92/soul-os/actions/workflows/ci.yml) |
