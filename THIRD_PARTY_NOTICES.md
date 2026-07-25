# Third-party notices

SoulOS source code is **MIT** — see [LICENSE](LICENSE).

## Dependency license inventory

A generated inventory of installed third-party Python and npm packages (name, version, declared license) lives in:

- [docs/dependency-licenses.generated.md](docs/dependency-licenses.generated.md)

Regenerate after changing dependencies:

```bash
python3 scripts/generate-dependency-licenses.py
```

CI regenerates the inventory and fails the build if any package declares a high-risk license (GPL / AGPL / SSPL / BUSL / Commons Clause / CC-BY-NC). Refresh the committed snapshot after dependency bumps with `npm run licenses:gen`.

## First-party persona content (SoulPacks)

Planned **SoulPacks** (in-repo persona packages) are authored under the same **MIT** license as SoulOS. Do not vendor third-party persona prose into the tree unless it is MIT (or equivalently permissive with no attribution-derivative burden) and reviewed. See [docs/guides/persona-packs.md](docs/guides/persona-packs.md).

## Web fonts (GitHub Pages / Studio CSS)

The project site CSS may load **Figtree** and **Fraunces** from Google Fonts under the **SIL Open Font License 1.1 (OFL-1.1)**.

- CDN use for rendering HTML pages does not require vendoring font binaries into this repository.
- **If font files are ever vendored** under `site-src/`, `packages/soulos-studio/`, or elsewhere in-tree, ship the OFL copyright notice and license text next to those files (do not relicense the fonts as MIT).

## Runtime images (Docker Compose)

Compose stacks may pull images such as `pgvector/pgvector` and `ollama/ollama`. Those are **runtime dependencies**, not linked into the MIT source tree. Model weights pulled by Ollama are licensed separately by their publishers.
