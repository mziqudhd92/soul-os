# ClawSouls attribution and licenses

SoulOS does **not** commit full ClawSouls persona text in this repository. Persona prose is fetched from [clawsouls.ai](https://clawsouls.ai) at import time or generated locally with `generate-examples.sh` (do not redistribute generated files without complying with the soul's license).

## Official souls referenced in this directory

| Soul | Owner | SPDX license | Source | Version (catalog) |
|------|-------|--------------|--------|-------------------|
| Surgical Coder | `clawsouls` | Apache-2.0 | https://clawsouls.ai/en/souls/clawsouls/surgical-coder | 1.3.0+ |
| Minimalist | `clawsouls` | Apache-2.0 | https://clawsouls.ai/en/souls/clawsouls/minimalist | 2.1.0+ |
| DevOps Veteran | `clawsouls` | Apache-2.0 | https://clawsouls.ai/en/souls/clawsouls/devops-veteran | 2.1.0+ |

License identifiers come from each soul's `soul.json` on the ClawSouls registry. Community souls may use other [allowed permissive licenses](https://clawsouls.ai/en/licenses) (MIT, BSD-2-Clause, CC-BY-4.0, etc.). SoulOS import rejects licenses outside the shared allowlist.

## What SoulOS adds (derivative work)

Imported souls are converted to SoulOS `.soul.json` shape:

- Merged markdown from Soul Spec files → `description`
- Curated HEXACO MSV presets → `baseline_msv` (SoulOS-authored, not from ClawSouls)
- Optional `capabilities` from upstream `tags`

Upstream persona text is **modified** by merge order and by addition of psychometric fields. For **Apache-2.0** souls, redistribution of converted files must:

1. State that files were modified by SoulOS
2. Retain upstream copyright/attribution notices where applicable
3. Include a copy of the Apache License 2.0 ([LICENSE-APACHE-2.0.txt](LICENSE-APACHE-2.0.txt))

For **MIT** upstream souls, include the MIT copyright notice from the soul package.

For **CC-BY-4.0** souls, provide attribution as required by Creative Commons (name, source URL, license link).

## SoulOS integration disclaimer

SoulOS is **not affiliated with or endorsed by ClawSouls**. ClawSouls is an independent platform (see their [disclaimer](https://github.com/clawsouls/clawsouls#disclaimer)). Use ClawSouls trademarks only to describe origin of persona packages, per Apache 2.0 §6.

## Generate local examples (optional)

```bash
./examples/clawsouls/generate-examples.sh
```

Output is for local development only unless you comply with the upstream license when sharing.

## Soul Spec citation

Soul Spec is maintained by ClawSouls under Apache-2.0: [github.com/clawsouls/soulspec](https://github.com/clawsouls/soulspec).
