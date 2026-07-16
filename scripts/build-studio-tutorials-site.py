#!/usr/bin/env python3
"""Build the SoulOS GitHub Pages site (landing + docs index + tutorials)."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE_SRC = ROOT / "site-src"
TEMPLATES = SITE_SRC / "templates"
sys.path.insert(0, str(TEMPLATES))

from _shell import page  # noqa: E402


def _ensure_base(base: str) -> str:
    if not base:
        return "/"
    if not base.startswith("/"):
        base = f"/{base}"
    if not base.endswith("/"):
        base = f"{base}/"
    return base


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _home(base: str, adopters: list[dict]) -> str:
    adopter_cards = []
    for a in adopters:
        adopter_cards.append(
            f"""
        <article class="adopter-card">
          <a href="{a["url"]}" rel="noopener">
            <h3>{a["name"]}</h3>
            <p>{a["product_summary"]}</p>
          </a>
        </article>"""
        )
    adopters_html = "\n".join(adopter_cards) or "<p class='sub'>No adopters listed yet.</p>"

    body = f"""
    <section class="site-shell hero">
      <h1>SoulOS</h1>
      <p class="lede">Identity + memory sidecar for agents you already run — validated personality, episodic recall, and a hybrid API so your LLM keeps generation.</p>
      <div class="btn-row">
        <a class="btn btn-primary" href="{base}get-started/">Get started</a>
        <a class="btn btn-ghost" href="{base}docs/">View docs</a>
        <a class="btn btn-ghost" href="https://github.com/mziqudhd92/soul-os">GitHub</a>
      </div>
      <div class="hero-flow" aria-label="Primary integration path">
        <code>ensure</code> → <code>prepare</code> → <span>your LLM</span> → <code>complete</code>
      </div>
    </section>

    <section class="section">
      <div class="site-shell">
        <h2>How it works</h2>
        <p class="sub">SoulOS owns persona, memory, and MSV drift. Your app keeps Bedrock, OpenAI, LiteLLM, or any chat stack.</p>
        <div class="path-grid">
          <div class="path-tile">
            <h3>1. Ensure avatar</h3>
            <p>Idempotent bootstrap with <code>external_key</code> and a <code>.soul.json</code>.</p>
          </div>
          <div class="path-tile">
            <h3>2. Prepare turn</h3>
            <p><code>POST /hybrid/prepare</code> returns a ready <code>system_prompt</code> + memories.</p>
          </div>
          <div class="path-tile">
            <h3>3. Your LLM</h3>
            <p>Stream tokens with your existing client — SoulOS stays on embeddings when you want.</p>
          </div>
          <div class="path-tile">
            <h3>4. Complete</h3>
            <p>Ingest the turn and optionally reflect MSV with <code>POST /hybrid/complete</code>.</p>
          </div>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="site-shell">
        <h2>Start here</h2>
        <p class="sub">Pick the path that matches your stack.</p>
        <div class="path-grid">
          <article class="path-tile">
            <a href="{base}get-started/">
              <h3>Hybrid sidecar</h3>
              <p>Recommended — add SoulOS beside an existing LLM app (~15 min).</p>
            </a>
          </article>
          <article class="path-tile">
            <a href="{base}tutorials/?tutorial=python-bot">
              <h3>Full-chat Python bot</h3>
              <p>Let SoulOS stream chat end-to-end with SSE.</p>
            </a>
          </article>
          <article class="path-tile">
            <a href="https://github.com/mziqudhd92/soul-os/blob/main/docs/guides/mcp.md">
              <h3>MCP in Cursor</h3>
              <p>Memory and identity tools at <code>/mcp/sse</code>.</p>
            </a>
          </article>
          <article class="path-tile">
            <a href="{base}tutorials/">
              <h3>Interactive tutorials</h3>
              <p>Offline walkthroughs for Studio, quickstart, and more.</p>
            </a>
          </article>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="site-shell">
        <h2>Used in production</h2>
        <p class="sub">Independent products use SoulOS for persistent persona and episodic memory. Listing is factual, not endorsement.</p>
        <div class="adopter-grid">
{adopters_html}
        </div>
        <p style="margin-top:1.25rem"><a href="{base}adopters/">All adopters →</a></p>
      </div>
    </section>

    <section class="section">
      <div class="site-shell">
        <h2>Trust</h2>
        <p class="sub">Open-source MIT kernel you can inspect, fork, and self-host.</p>
        <div class="trust-grid">
          <div class="trust-tile"><strong>License</strong><p>MIT</p></div>
          <div class="trust-tile"><strong>CI</strong><p><a href="https://github.com/mziqudhd92/soul-os/actions/workflows/ci.yml">Tests on every push</a></p></div>
          <div class="trust-tile"><strong>Security</strong><p><a href="https://github.com/mziqudhd92/soul-os/blob/main/SECURITY.md">SECURITY.md</a></p></div>
          <div class="trust-tile"><strong>Conduct</strong><p><a href="https://github.com/mziqudhd92/soul-os/blob/main/CODE_OF_CONDUCT.md">Contributor Covenant</a></p></div>
          <div class="trust-tile"><strong>Agents</strong><p><a href="https://github.com/mziqudhd92/soul-os/blob/main/llms.txt">llms.txt</a></p></div>
          <div class="trust-tile"><strong>API</strong><p><a href="https://github.com/mziqudhd92/soul-os/blob/main/docs/reference/openapi.kernel.json">OpenAPI artifact</a></p></div>
        </div>
      </div>
    </section>
"""
    return page(
        base=base,
        title="SoulOS — identity + memory sidecar for agents",
        description="SoulOS is an open-source identity and episodic memory sidecar: HEXACO MSV, hybrid prepare/complete API, MCP, and Soul Studio.",
        active="",
        body=body,
        extra_head="""
  <script>
    (function () {
      var q = new URLSearchParams(location.search).get("tutorial");
      if (q) {
        var base = document.querySelector("base");
        var root = base ? base.href : "/";
        location.replace(root + "tutorials/?tutorial=" + encodeURIComponent(q));
      }
    })();
  </script>""",
    )


def _get_started(base: str) -> str:
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
      <p>Kernel listens on <code>http://localhost:8001</code>.</p>

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

      <h2>Secondary paths</h2>
      <ul>
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
        body=body,
    )


def _docs(base: str) -> str:
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
          <a href="https://github.com/mziqudhd92/soul-os/blob/main/docs/guides/identity-model.md">
            <h3>Identity model</h3>
            <p>external_key, session_id, ensure vs register.</p>
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
        body=body,
    )


def _adopters(base: str, adopters: list[dict]) -> str:
    cards = []
    for a in adopters:
        cats = ", ".join(a.get("categories", [])[:4])
        cards.append(
            f"""
      <article class="adopter-card">
        <h3><a href="{a["url"]}" rel="noopener">{a["name"]}</a></h3>
        <p>{a["product_summary"]}</p>
        <p style="margin-top:0.75rem"><strong style="color:var(--accent-2)">SoulOS role:</strong> {a["soulos_role"]}</p>
        <p style="margin-top:0.5rem;font-size:0.85rem;color:var(--muted)">{cats}</p>
      </article>"""
        )
    body = f"""
    <section class="site-shell page-hero">
      <h1>Production adopters</h1>
      <p>Independent products using SoulOS for persistent persona and memory. Not mutual endorsement.</p>
    </section>
    <section class="site-shell" style="padding-bottom:3rem">
      <div class="adopter-grid">
{"".join(cards)}
      </div>
      <p style="margin-top:1.5rem;color:var(--muted)">
        Source: <a href="https://github.com/mziqudhd92/soul-os/blob/main/docs/adopters.md">docs/adopters.md</a>
        · <a href="https://github.com/mziqudhd92/soul-os/blob/main/docs/adopters.json">adopters.json</a>
      </p>
    </section>
"""
    return page(
        base=base,
        title="Adopters — SoulOS",
        description="Production adopters of SoulOS: SignalPR, Aeterna, Ved Travel, and more.",
        active="adopters",
        body=body,
    )


def _community(base: str) -> str:
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
          <a href="https://github.com/mziqudhd92/soul-os/blob/main/CHANGELOG.md">
            <h3>Changelog</h3>
            <p>What shipped in v0.2.0 and how to migrate.</p>
          </a>
        </article>
      </div>
      <p style="margin-top:2rem">Prefer repo issues for bugs. For AI agents, start with
      <a href="https://github.com/mziqudhd92/soul-os/blob/main/llms.txt">llms.txt</a> and
      <a href="https://github.com/mziqudhd92/soul-os/blob/main/docs/SOULOS_AGENT_CONTEXT.md">SOULOS_AGENT_CONTEXT.md</a>.</p>
    </section>
"""
    return page(
        base=base,
        title="Community — SoulOS",
        description="Contribute to SoulOS, get support, and read the code of conduct.",
        active="community",
        body=body,
    )


def _tutorials_page(base: str) -> str:
    """Tutorials SPA shell — keeps existing interactive tutorial JS."""
    return f"""<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Tutorials — SoulOS</title>
  <base href="{base}" />
  <link rel="stylesheet" href="static/site.css" />
  <link rel="stylesheet" href="static/studio.css" />
  <meta name="description" content="Interactive SoulOS tutorials — sidecar, Python bot, quickstart, Soul Builder, MCP." />
</head>
<body class="tutorials-site">
  <header class="site-header">
    <div class="site-shell site-header-inner">
      <a class="brand" href="{base}">
        <span class="brand-mark">S</span>
        SoulOS
      </a>
      <nav class="nav" aria-label="Primary">
        <a href="{base}get-started/">Get started</a>
        <a href="{base}docs/">Docs</a>
        <a href="{base}tutorials/" aria-current="page">Tutorials</a>
        <a class="hide-sm" href="{base}adopters/">Adopters</a>
        <a class="hide-sm" href="{base}community/">Community</a>
        <a class="btn btn-ghost" style="padding:0.4rem 0.85rem" href="https://github.com/mziqudhd92/soul-os" rel="noopener">GitHub</a>
        <button type="button" id="btn-theme" class="btn btn-ghost" style="padding:0.4rem 0.7rem" title="Toggle theme" aria-label="Toggle theme">☾</button>
      </nav>
    </div>
  </header>

  <div class="page-shell site-shell" style="padding:1.5rem 0 3rem">
    <div id="view-tutorial" class="view view-active">
      <div class="tutorial-wrap">
        <div id="tutorial-list-view">
          <header class="page-intro page-hero" style="padding-top:0.5rem">
            <h1>Tutorials</h1>
            <p>Step-by-step guides for hybrid sidecar, Studio, and deployment. Interactive walkthroughs work offline; run Docker locally for live kernel checks.</p>
          </header>
          <div id="tutorial-grid" class="tutorial-grid"></div>
        </div>
        <div id="tutorial-detail-view" class="hidden">
          <button type="button" id="tutorial-back" class="btn btn-ghost" style="padding:0.4rem 0.85rem">← All tutorials</button>
          <article class="panel prose-panel flat">
            <div id="tutorial-meta" class="tutorial-meta"></div>
            <div id="tutorial-content" class="prose"></div>
          </article>
        </div>
      </div>
    </div>
  </div>

  <script src="static/tutorial-python-bot.js"></script>
  <script src="static/tutorial-terminal.js"></script>
  <script src="static/tutorial-soul-builder.js"></script>
  <script>
    window.STUDIO_STATIC = true;
    window.STUDIO_BASE = "{base}";
  </script>
  <script src="static/tutorials-static.js"></script>
</body>
</html>
"""


def build(out: Path, base: str) -> None:
    os.environ["SOULOS_DOCS_ROOT"] = str(ROOT / "docs")

    from soulos_studio.tutorials import TUTORIALS
    from soulos_studio.docs_reader import get_tutorial_content, get_tutorials_catalog

    base = _ensure_base(base)
    static_studio = ROOT / "packages/soulos-studio/soulos_studio/static"
    static_out = out / "static"
    data_tutorials = out / "data" / "tutorials"

    if out.exists():
        shutil.rmtree(out)
    static_out.mkdir(parents=True)
    data_tutorials.mkdir(parents=True)

    shutil.copy2(SITE_SRC / "static" / "site.css", static_out / "site.css")
    for name in (
        "studio.css",
        "tutorial-python-bot.js",
        "tutorial-terminal.js",
        "tutorial-soul-builder.js",
        "tutorials-static.js",
    ):
        shutil.copy2(static_studio / name, static_out / name)

    adopters_path = ROOT / "docs" / "adopters.json"
    adopters_data = json.loads(adopters_path.read_text(encoding="utf-8"))
    adopters = adopters_data.get("adopters", [])
    shutil.copy2(adopters_path, out / "data" / "adopters.json")

    catalog_path = out / "data" / "tutorials.json"
    catalog_path.write_text(
        json.dumps({"tutorials": get_tutorials_catalog()}, indent=2),
        encoding="utf-8",
    )
    for tutorial in TUTORIALS:
        tid = tutorial["id"]
        doc = get_tutorial_content(tid)
        (data_tutorials / f"{tid}.json").write_text(
            json.dumps(doc, indent=2),
            encoding="utf-8",
        )

    _write(out / "index.html", _home(base, adopters))
    _write(out / "get-started" / "index.html", _get_started(base))
    _write(out / "docs" / "index.html", _docs(base))
    _write(out / "adopters" / "index.html", _adopters(base, adopters))
    _write(out / "community" / "index.html", _community(base))
    _write(out / "tutorials" / "index.html", _tutorials_page(base))

    # SPA-style fallback for unknown paths on project pages
    shutil.copy2(out / "index.html", out / "404.html")
    (out / ".nojekyll").touch()

    print(f"Built SoulOS site → {out.resolve()}")
    print(f"  base URL path: {base}")
    print(f"  pages: home, get-started, docs, tutorials, adopters, community")
    print(f"  tutorials: {len(TUTORIALS)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build SoulOS GitHub Pages site")
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "site",
        help="Output directory (default: site/)",
    )
    parser.add_argument(
        "--base",
        default="/soul-os/",
        help="GitHub Pages base path (default: /soul-os/)",
    )
    args = parser.parse_args(argv)

    try:
        build(args.out, args.base)
    except Exception as exc:
        print(f"build failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
