"""Community page."""

from __future__ import annotations

from html import escape

from .common import page, absolute_url, safe_http_url

def render_community(base: str) -> str:
    body = f"""
    <section class="site-shell page-hero">
      <h1>Community</h1>
      <p>How to contribute, get support, and report security issues.</p>
    </section>
    <section class="site-shell prose-block">
      <div class="doc-grid">
        <article class="doc-card">
          <a href="https://github.com/mziqudhd92/soul-os/blob/main/CONTRIBUTING.md">
            <h3>Contributing</h3>
            <p>Dev setup, tests, documentation checklist.</p>
          </a>
        </article>
        <article class="doc-card">
          <a href="https://github.com/mziqudhd92/soul-os/blob/main/SUPPORT.md">
            <h3>Support</h3>
            <p>Where to ask questions and what to include.</p>
          </a>
        </article>
        <article class="doc-card">
          <a href="https://github.com/mziqudhd92/soul-os/blob/main/CODE_OF_CONDUCT.md">
            <h3>Code of Conduct</h3>
            <p>Contributor Covenant — expected behavior.</p>
          </a>
        </article>
        <article class="doc-card">
          <a href="https://github.com/mziqudhd92/soul-os/blob/main/SECURITY.md">
            <h3>Security</h3>
            <p>Private vulnerability reporting and MCP blast radius.</p>
          </a>
        </article>
        <article class="doc-card">
          <a href="https://github.com/mziqudhd92/soul-os/issues">
            <h3>Issues</h3>
            <p>Bugs and features — use the templates.</p>
          </a>
        </article>
        <article class="doc-card">
          <a href="https://github.com/mziqudhd92/soul-os/blob/main/docs/guides/architecture-overview.md">
            <h3>Architecture overview</h3>
            <p>Contributor map, scale assumptions, non-goals.</p>
          </a>
        </article>
        <article class="doc-card">
          <a href="https://github.com/mziqudhd92/soul-os/blob/main/CHANGELOG.md">
            <h3>Changelog</h3>
            <p>What shipped in v0.2.0 and how to migrate.</p>
          </a>
        </article>
      </div>
      <p style="margin-top:2rem">Prefer repo issues for bugs. For AI agents, start with
      <a href="{base}llms.txt">llms.txt</a>,
      <a href="{base}agents/">Agents / GEO</a>, and
      <a href="https://raw.githubusercontent.com/mziqudhd92/soul-os/main/docs/SOULOS_AGENT_CONTEXT.md">SOULOS_AGENT_CONTEXT.md</a>.</p>
    </section>
"""
    return page(
        base=base,
        title="Community — SoulOS",
        description="Contribute to SoulOS, get support, and read the code of conduct.",
        active="community",
        path="community/",
        body=body,
    )
