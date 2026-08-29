"""Get started page."""

from __future__ import annotations

from html import escape

from .common import page, absolute_url, safe_http_url

def render_docs(base: str) -> str:
    body = f"""
    <section class="site-shell page-hero">
      <h1>Documentation</h1>
      <p>Canonical docs live in the repository. Start with hybrid sidecar, then dive into reference and playbooks.</p>
    </section>
    <section class="site-shell" style="padding-bottom:3rem">
      <div class="doc-grid">
        <article class="doc-card">
          <a href="https://github.com/mziqudhd92/soul-os/blob/main/docs/README.md">
            <h3>Docs index</h3>
            <p>Full Diátaxis map — guides, reference, deployment.</p>
          </a>
        </article>
        <article class="doc-card">
          <a href="https://github.com/mziqudhd92/soul-os/blob/main/docs/guides/sidecar-integration.md">
            <h3>Sidecar integration</h3>
            <p>Bedrock/OpenAI apps: prepare → LLM → complete.</p>
          </a>
        </article>
        <article class="doc-card">
          <a href="{base}soulpacks/">
            <h3>SoulPacks</h3>
            <p>MIT persona packages — use, import, and author your own.</p>
          </a>
        </article>
        <article class="doc-card">
          <a href="https://github.com/mziqudhd92/soul-os/blob/main/docs/guides/persona-packs.md">
            <h3>SoulPacks guide (repo)</h3>
            <p>API, CLI, layout, MSV precedence, path safety.</p>
          </a>
        </article>
        <article class="doc-card">
          <a href="https://github.com/mziqudhd92/soul-os/blob/main/docs/guides/identity-model.md">
            <h3>Identity model</h3>
            <p>external_key, session_id, ensure vs register.</p>
          </a>
        </article>
        <article class="doc-card">
          <a href="https://github.com/mziqudhd92/soul-os/blob/main/docs/guides/observability.md">
            <h3>Observability</h3>
            <p>OpenTelemetry spans and hybrid duration metrics.</p>
          </a>
        </article>
        <article class="doc-card">
          <a href="https://github.com/mziqudhd92/soul-os/blob/main/docs/guides/horizontal-scale.md">
            <h3>Horizontal scale</h3>
            <p>HPA assumptions, Redis rate limits, session TTL.</p>
          </a>
        </article>
        <article class="doc-card">
          <a href="https://github.com/mziqudhd92/soul-os/blob/main/docs/guides/architecture-overview.md">
            <h3>Architecture overview</h3>
            <p>Contributor map, SDKs, explicit non-goals.</p>
          </a>
        </article>
        <article class="doc-card">
          <a href="https://github.com/mziqudhd92/soul-os/blob/main/deploy/helm/soulos/README.md">
            <h3>Helm chart</h3>
            <p>Minimal Kubernetes install for kernel + optional gateway.</p>
          </a>
        </article>
        <article class="doc-card">
          <a href="https://github.com/mziqudhd92/soul-os/blob/main/docs/reference/hybrid-api.md">
            <h3>Hybrid API</h3>
            <p>JSON shapes, session memory, RFC 7807 errors.</p>
          </a>
        </article>
        <article class="doc-card">
          <a href="https://github.com/mziqudhd92/soul-os/blob/main/docs/reference/api.md">
            <h3>REST + SSE API</h3>
            <p>Full endpoint list and chat multiplexing.</p>
          </a>
        </article>
        <article class="doc-card">
          <a href="https://github.com/mziqudhd92/soul-os/blob/main/docs/reference/openapi.kernel.json">
            <h3>OpenAPI</h3>
            <p>Locked SDK contract artifact for CI.</p>
          </a>
        </article>
        <article class="doc-card">
          <a href="https://github.com/mziqudhd92/soul-os/blob/main/docs/guides/troubleshooting.md">
            <h3>Troubleshooting</h3>
            <p>Keyed by Problem Details <code>code</code>.</p>
          </a>
        </article>
        <article class="doc-card">
          <a href="https://github.com/mziqudhd92/soul-os/blob/main/docs/testing.md">
            <h3>Testing</h3>
            <p>TDD expectations and npm test scripts.</p>
          </a>
        </article>
        <article class="doc-card">
          <a href="{base}tutorials/">
            <h3>Interactive tutorials</h3>
            <p>Browser walkthroughs without a local kernel.</p>
          </a>
        </article>
      </div>
    </section>
"""
    return page(
        base=base,
        title="Docs — SoulOS",
        description="SoulOS documentation index: sidecar, hybrid API, OpenAPI, troubleshooting.",
        active="docs",
        path="docs/",
        body=body,
    )
