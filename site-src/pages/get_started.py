"""Site page renderer."""

from __future__ import annotations

from html import escape

from .common import page, absolute_url, safe_http_url

def render_get_started(base: str) -> str:
    body = f"""
    <section class="site-shell page-hero">
      <h1>Get started</h1>
      <p>Primary path: hybrid sidecar. Your LLM keeps generation; SoulOS owns persona and memory.</p>
    </section>
    <section class="site-shell prose-block">
      <h2>1. Start the sidecar stack</h2>
      <pre><code>git clone https://github.com/mziqudhd92/soul-os.git
cd soul-os
docker compose -f docker-compose.sidecar.yml --profile bridge-mock up -d</code></pre>
      <p>Kernel listens on <code>http://localhost:8001</code> in the sidecar compose file (or :8000 for full stack).</p>

      <h2>2. Smoke test</h2>
      <pre><code>npm run smoke:hybrid</code></pre>
      <p>Runs ensure → doctor → prepare and prints the system prompt.</p>

      <h2>3. Wire your app</h2>
      <ul>
        <li><a href="{base}tutorials/?tutorial=my-first-sidecar">Tutorial: My first sidecar</a> (15 min)</li>
        <li><a href="https://github.com/mziqudhd92/soul-os/blob/main/docs/guides/sidecar-integration.md">Sidecar integration guide</a></li>
        <li><a href="https://github.com/mziqudhd92/soul-os/tree/main/examples/fastapi-hybrid">examples/fastapi-hybrid</a></li>
        <li><a href="https://github.com/mziqudhd92/soul-os/blob/main/docs/reference/hybrid-api.md">Hybrid API reference</a></li>
      </ul>

      <h2>4. Optional — start from a SoulPack</h2>
      <p>Import a first-party MIT persona, then run hybrid turns.</p>
      <pre><code>curl -s -X POST http://localhost:8000/v1/avatars/import-soulpack \\
  -H 'content-type: application/json' \\
  -d '{{"pack_id":"support-agent","persist":true}}'</code></pre>
      <p>Details: <a href="{base}soulpacks/">SoulPacks</a> · <a href="https://github.com/mziqudhd92/soul-os/blob/main/docs/guides/persona-packs.md">guide</a>.</p>

      <h2>Secondary paths</h2>
      <ul>
        <li><a href="{base}soulpacks/">SoulPacks</a> — MIT persona packages</li>
        <li><a href="{base}tutorials/?tutorial=python-bot">Full-chat Python bot</a> — SoulOS streams SSE</li>
        <li><a href="https://github.com/mziqudhd92/soul-os/blob/main/docs/guides/mcp.md">MCP for Cursor / Claude</a></li>
        <li><a href="https://github.com/mziqudhd92/soul-os#quickstart">Run Soul Studio locally</a> on :8765</li>
      </ul>
    </section>
"""
    return page(
        base=base,
        title="Get started — SoulOS",
        description="Start SoulOS as a hybrid sidecar in about 15 minutes.",
        active="get-started",
        path="get-started/",
        body=body,
    )
