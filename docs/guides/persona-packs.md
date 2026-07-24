# Persona packs (planned)

Third-party **ClawSouls** persona import was **removed** from SoulOS because of licensing complexity: upstream persona prose creates derivative-work and attribution obligations (including CC-BY / Apache-2.0 redistribution rules) that are hard to keep correct for every deploy and redistribute path.

**We will implement our own persona-pack format and import path** instead of re-adding a ClawSouls bridge. Until then:

- Author souls in Soul Studio or hand-write `.soul.json` ([soul schema](../../spec/soul.schema.json))
- Register with `POST /v1/avatars` or `POST /v1/avatars/ensure`
- Use the [hybrid sidecar](sidecar-integration.md) path for apps that already have an LLM

See [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md) for dependency licenses and the historical note on this removal.
