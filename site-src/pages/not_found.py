"""404 page."""

from __future__ import annotations

from html import escape

from .common import page, absolute_url, safe_http_url

def render_not_found(base: str) -> str:
    body = f"""
    <section class="site-shell page-hero" style="padding-bottom:3rem">
      <h1>Page not found</h1>
      <p>That URL is not part of the SoulOS project site. Try one of these:</p>
      <div class="btn-row" style="margin-top:1.25rem">
        <a class="btn btn-primary" href="{base}">Home</a>
        <a class="btn btn-ghost" href="{base}get-started/">Get started</a>
        <a class="btn btn-ghost" href="{base}soulpacks/">SoulPacks</a>
        <a class="btn btn-ghost" href="{base}docs/">Docs</a>
        <a class="btn btn-ghost" href="{base}tutorials/">Tutorials</a>
      </div>
    </section>
"""
    return page(
        base=base,
        title="Page not found — SoulOS",
        description="The requested SoulOS project site page was not found.",
        active="",
        path="",
        body=body,
        robots="noindex,follow",
    )
