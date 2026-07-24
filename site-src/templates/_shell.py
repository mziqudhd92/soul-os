"""Shared HTML shell helpers for the SoulOS GitHub Pages site."""

from __future__ import annotations

import json
from html import escape

SITE_ORIGIN = "https://mziqudhd92.github.io"
# Path prefix including trailing slash, e.g. /soul-os/
DEFAULT_BASE = "/soul-os/"

NAV_ITEMS = [
    ("get-started/", "Get started"),
    ("docs/", "Docs"),
    ("tutorials/", "Tutorials"),
    ("adopters/", "Adopters"),
    ("agents/", "Agents"),
    ("community/", "Community"),
]


def absolute_url(base: str, path: str = "") -> str:
    """Build absolute URL for OG/canonical (path relative to site root)."""
    root = f"{SITE_ORIGIN}{base}"
    if not path:
        return root
    return f"{root}{path.lstrip('/')}"


def nav_html(base: str, active: str = "") -> str:
    parts: list[str] = []
    for href, label in NAV_ITEMS:
        current = ' aria-current="page"' if active == href.rstrip("/") else ""
        hide = ' class="hide-sm"' if label in ("Adopters", "Community", "Agents") else ""
        parts.append(f'<a href="{base}{href}"{current}{hide}>{label}</a>')
    parts.append(
        f'<a class="btn btn-ghost" style="padding:0.4rem 0.85rem" '
        f'href="https://github.com/mziqudhd92/soul-os" rel="noopener">GitHub</a>'
    )
    return "\n        ".join(parts)


def page(
    *,
    base: str,
    title: str,
    description: str,
    active: str,
    body: str,
    extra_head: str = "",
    path: str = "",
    json_ld: list[dict] | None = None,
    robots: str = "index,follow,max-image-preview:large",
) -> str:
    canonical = absolute_url(base, path)
    desc = escape(description, quote=True)
    title_esc = escape(title, quote=True)
    robots_esc = escape(robots, quote=True)
    ld_blocks = ""
    for obj in json_ld or []:
        payload = json.dumps(obj, ensure_ascii=True, indent=2)
        ld_blocks += (
            f'\n  <script type="application/ld+json">\n{payload}\n  </script>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title_esc}</title>
  <meta name="description" content="{desc}" />
  <meta name="robots" content="{robots_esc}" />
  <link rel="canonical" href="{canonical}" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="SoulOS" />
  <meta property="og:title" content="{title_esc}" />
  <meta property="og:description" content="{desc}" />
  <meta property="og:url" content="{canonical}" />
  <meta name="twitter:card" content="summary" />
  <meta name="twitter:title" content="{title_esc}" />
  <meta name="twitter:description" content="{desc}" />
  <link rel="alternate" type="text/plain" title="llms.txt" href="{absolute_url(base, 'llms.txt')}" />
  <link rel="alternate" type="text/plain" title="llms-full.txt" href="{absolute_url(base, 'llms-full.txt')}" />
  <link rel="describedby" href="{absolute_url(base, 'schema/project.json')}" />
  <base href="{base}" />
  <link rel="stylesheet" href="static/site.css" />
  {extra_head}{ld_blocks}
</head>
<body>
  <header class="site-header">
    <div class="site-shell site-header-inner">
      <a class="brand" href="{base}">
        <span class="brand-mark">S</span>
        SoulOS
      </a>
      <nav class="nav" aria-label="Primary">
        {nav_html(base, active)}
      </nav>
    </div>
  </header>

  <main>
{body}
  </main>

  <footer class="site-footer">
    <div class="site-shell site-footer-inner">
      <div>SoulOS — MIT · Identity + memory sidecar for agents you already run</div>
      <div class="footer-links">
        <a href="{base}docs/">Docs</a>
        <a href="{base}tutorials/">Tutorials</a>
        <a href="{base}agents/">Agents / GEO</a>
        <a href="{base}llms.txt">llms.txt</a>
        <a href="{base}sitemap.xml">Sitemap</a>
        <a href="https://github.com/mziqudhd92/soul-os/blob/main/CHANGELOG.md">Changelog</a>
        <a href="https://github.com/mziqudhd92/soul-os/blob/main/CODE_OF_CONDUCT.md">Code of Conduct</a>
        <a href="https://github.com/mziqudhd92/soul-os">GitHub</a>
      </div>
    </div>
  </footer>
</body>
</html>
"""
