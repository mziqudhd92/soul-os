---
name: ClawSouls SoulOS framework request
about: Request adding soulos to ClawSouls compatibility.frameworks
title: "Add soulos to compatibility.frameworks"
labels: upstream
---

## Summary

Request upstream [ClawSouls](https://clawsouls.ai) to list **`soulos`** in persona `compatibility.frameworks` so importers can discover SoulOS-native souls.

## Proposed entry

```json
{
  "frameworks": ["soulos", "..."]
}
```

## SoulOS import path

- `POST /v1/avatars/import-clawsouls` with `CLAWSOULS_IMPORT_ENABLED=1`
- Studio **ClawSouls** tab
- Docs: https://github.com/mziqudhd92/soul-os/blob/main/docs/guides/clawsouls-import.md

## References

- SoulOS repo: https://github.com/mziqudhd92/soul-os
- Hybrid sidecar: `ensure → prepare → LLM → complete`
