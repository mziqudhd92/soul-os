# Third-party notices

SoulOS (MIT License — see [LICENSE](LICENSE)) may interoperate with external persona registries and specifications. The SoulOS **source code** is MIT-licensed; **imported persona prose** remains under each upstream soul's license.

## ClawSouls

SoulOS can fetch persona packages from [ClawSouls](https://clawsouls.ai) via their public API (`https://clawsouls.ai/api/v1`). ClawSouls persona packages are community or official works published under permissive licenses (typically **Apache-2.0** or **MIT** per soul `soul.json`).

- ClawSouls platform README: [github.com/clawsouls/clawsouls](https://github.com/clawsouls/clawsouls) (Apache-2.0)
- Soul Spec: [github.com/clawsouls/soulspec](https://github.com/clawsouls/soulspec) (Apache-2.0)
- Registry souls: per-package `license` field — see [ClawSouls license guide](https://clawsouls.ai/en/licenses)

**Relationship:** SoulOS is an independent project. It is **not affiliated with or endorsed by ClawSouls**. The integration imports personas at runtime or via local conversion; it does not replace the ClawSouls registry or CLI.

**Derivatives:** When persona markdown is merged into a SoulOS soul payload, SoulOS adds HEXACO MSV and other fields. That combined payload is a derivative of the upstream soul. You must comply with the upstream license (attribution, license copy for Apache-2.0 derivatives, etc.). See [examples/clawsouls/ATTRIBUTION.md](examples/clawsouls/ATTRIBUTION.md).

**Apache License 2.0** (applies to many ClawSouls official souls): [http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0)
