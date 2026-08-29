"""Adopters page."""

from __future__ import annotations

from html import escape

from .common import page, absolute_url, safe_http_url

def render_adopters(base: str, adopters: list[dict]) -> str:
    cards = []
    for a in adopters:
        cats = escape(", ".join(str(c) for c in (a.get("categories") or [])[:4]))
        href = escape(safe_http_url(str(a.get("url", ""))), quote=True)
        name = escape(str(a.get("name", "")))
        summary = escape(str(a.get("product_summary", "")))
        role = escape(str(a.get("soulos_role", "")))
        cards.append(
            f"""
      <article class="adopter-card">
        <h3><a href="{href}" rel="noopener">{name}</a></h3>
        <p>{summary}</p>
        <p style="margin-top:0.75rem"><strong style="color:var(--accent-2)">SoulOS role:</strong> {role}</p>
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
        description="Production adopters of SoulOS: SignalPR, Aeterna, Ved Travel, Getbyliner, and more.",
        active="adopters",
        path="adopters/",
        body=body,
    )
