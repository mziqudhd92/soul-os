"""Shared HTML shell helpers for the SoulOS GitHub Pages site."""

from __future__ import annotations

NAV_ITEMS = [
    ("get-started/", "Get started"),
    ("docs/", "Docs"),
    ("tutorials/", "Tutorials"),
    ("adopters/", "Adopters"),
    ("community/", "Community"),
]


def nav_html(base: str, active: str = "") -> str:
    parts: list[str] = []
    for href, label in NAV_ITEMS:
        current = ' aria-current="page"' if active == href.rstrip("/") else ""
        hide = ' class="hide-sm"' if label in ("Adopters", "Community") else ""
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
) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <meta name="description" content="{description}" />
  <base href="{base}" />
  <link rel="stylesheet" href="static/site.css" />
  {extra_head}
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
        <a href="https://github.com/mziqudhd92/soul-os/blob/main/llms.txt">llms.txt</a>
        <a href="https://github.com/mziqudhd92/soul-os/blob/main/CHANGELOG.md">Changelog</a>
        <a href="https://github.com/mziqudhd92/soul-os/blob/main/CODE_OF_CONDUCT.md">Code of Conduct</a>
        <a href="https://github.com/mziqudhd92/soul-os">GitHub</a>
      </div>
    </div>
  </footer>
</body>
</html>
"""
