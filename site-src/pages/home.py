"""Homepage renderer."""

from __future__ import annotations

import json
from html import escape

from .common import ROOT, load_soulpack_catalog, load_hero_svg, page, absolute_url, safe_http_url
from .faq import faq_html, faq_json_ld

def render_home(base: str, adopters: list[dict]) -> str:
    adopter_cards = []
    pack_count = len(load_soulpack_catalog())
    for a in adopters:
        href = escape(safe_http_url(str(a.get("url", ""))), quote=True)
        name = escape(str(a.get("name", "")))
        summary = escape(str(a.get("product_summary", "")))
        adopter_cards.append(
            f"""
        <article class="adopter-card">
          <a href="{href}" rel="noopener">
            <h3>{name}</h3>
            <p>{summary}</p>
          </a>
        </article>"""
        )
    adopters_html = "\n".join(adopter_cards) or "<p class='sub'>No adopters listed yet.</p>"
    faq_body = faq_html()
    hero_svg = load_hero_svg()

    body = f"""
    <section class="site-shell hero">
      <div class="hero-stage">
        <div class="hero-copy">
          <h1>SoulOS</h1>
          <p class="lede">Give your bot a soul — identity and memory beside the LLM you already run.</p>
          <div class="btn-row">
            <a class="btn btn-primary" href="{base}get-started/">Get started</a>
            <a class="btn btn-ghost" href="{base}soulpacks/">Browse SoulPacks</a>
          </div>
          <div class="hero-flow" aria-label="Primary integration path">
            <code>ensure</code> → <code>prepare</code> → <span>your LLM</span> → <code>complete</code>
          </div>
        </div>
        <div class="hero-visual" aria-hidden="false">
          {hero_svg}
        </div>
      </div>
    </section>

    <section class="section">
      <div class="site-shell">
        <h2>How it works</h2>
        <p class="sub">SoulOS owns persona, memory, and MSV drift. Your app keeps Bedrock, OpenAI, LiteLLM, or any chat stack.</p>
        <div class="path-grid">
          <div class="path-tile">
            <span class="path-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3l7 4v5c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V7l7-4z"/><path d="M9 12l2 2 4-4"/></svg>
            </span>
            <h3>1. Ensure avatar</h3>
            <p>Idempotent bootstrap with <code>external_key</code> and a <code>.soul.json</code>.</p>
          </div>
          <div class="path-tile">
            <span class="path-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 7h16M4 12h10M4 17h14"/><circle cx="18" cy="12" r="2"/></svg>
            </span>
            <h3>2. Prepare turn</h3>
            <p><code>POST /hybrid/prepare</code> returns a ready <code>system_prompt</code> + memories.</p>
          </div>
          <div class="path-tile">
            <span class="path-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3v10"/><path d="M8 9l4 4 4-4"/><rect x="4" y="15" width="16" height="6" rx="2"/></svg>
            </span>
            <h3>3. Your LLM</h3>
            <p>Stream tokens with your existing client — SoulOS stays on embeddings when you want.</p>
          </div>
          <div class="path-tile">
            <span class="path-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14"/><path d="M13 6l6 6-6 6"/><circle cx="6" cy="12" r="2"/></svg>
            </span>
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
            <a href="{base}soulpacks/">
              <h3>SoulPacks</h3>
              <p>{pack_count} first-party MIT personas — browse, search, and import ready roles.</p>
            </a>
          </article>
          <article class="path-tile">
            <a href="{base}tutorials/?tutorial=python-bot">
              <h3>Full-chat Python bot</h3>
              <p>Let SoulOS stream chat end-to-end with SSE.</p>
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

    <section class="section" id="faq" aria-labelledby="faq-heading">
      <div class="site-shell">
        <h2 id="faq-heading">FAQ</h2>
        <p class="sub">Common questions for humans and answer engines — same content as the FAQPage structured data.</p>
        <div class="faq-list">
{faq_body}
        </div>
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
          <div class="trust-tile"><strong>Agents</strong><p><a href="{base}llms.txt">llms.txt</a> · <a href="{base}agents/">GEO guide</a></p></div>
          <div class="trust-tile"><strong>API</strong><p><a href="https://github.com/mziqudhd92/soul-os/blob/main/docs/reference/openapi.kernel.json">OpenAPI artifact</a></p></div>
        </div>
      </div>
    </section>
"""
    project_ld = json.loads((ROOT / "schema" / "project.json").read_text(encoding="utf-8"))
    faq_ld = faq_json_ld()
    website_ld = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "SoulOS",
        "url": absolute_url(base),
        "description": "Identity + memory sidecar for agents you already run.",
        "publisher": {"@type": "Organization", "name": "SoulOS", "url": absolute_url(base)},
    }
    return page(
        base=base,
        title="SoulOS — identity + memory sidecar for agents",
        description="SoulOS is an open-source identity and episodic memory sidecar: HEXACO MSV, hybrid prepare/complete API, MCP, and Soul Studio.",
        active="",
        path="",
        body=body,
        json_ld=[project_ld, website_ld, faq_ld],
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
