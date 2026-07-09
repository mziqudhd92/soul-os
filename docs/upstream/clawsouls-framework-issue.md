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

## Submit

When authenticated with GitHub CLI:

```bash
bash scripts/submit-clawsouls-upstream.sh
```

Or open a prefilled issue: [clawsouls/soulspec — new issue](https://github.com/clawsouls/soulspec/issues/new?title=Add%20soulos%20to%20compatibility.frameworks&body=Request%20adding%20%60soulos%60%20to%20Soul%20Spec%20%60compatibility.frameworks%60%20for%20discoverability.%0A%0ASoulOS%20import%3A%20%60POST%20%2Fv1%2Favatars%2Fimport-clawsouls%60%20%7C%20docs%3A%20https%3A%2F%2Fgithub.com%2Fmziqudhd92%2Fsoul-os%2Fblob%2Fmain%2Fdocs%2Fguides%2Fclawsouls-import.md)
