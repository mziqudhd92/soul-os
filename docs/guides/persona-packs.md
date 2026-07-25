# SoulPacks (planned)

SoulOS will ship **SoulPacks**: first-party, MIT-licensed persona packages in this repository (`packs/soulpacks/`), with kernel list/import APIs and a Studio gallery.

**Licensing note:** Switched from ClawSouls to SoulPacks because of licensing issues — see [CHANGELOG](../../CHANGELOG.md) and the delivery plan below.

Until SoulPacks land:

- Author souls in Soul Studio or hand-write `.soul.json` ([soul schema](../../spec/soul.schema.json))
- Register with `POST /v1/avatars` or `POST /v1/avatars/ensure`
- Use the [hybrid sidecar](sidecar-integration.md) path for apps that already have an LLM

**Delivery plan + detailed todo list (TDD, M1–M5):** [SoulPacks TDD plan](../design/soulpacks-tdd-plan.md)

See [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md) for dependency licenses. SoulPacks content will be MIT, same as the SoulOS codebase.
