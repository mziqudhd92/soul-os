"""SoulPacks catalog pages."""

from __future__ import annotations

from html import escape

from .common import ROOT, page, absolute_url, load_pack_file, load_pack_manifest, load_soulpack_catalog

def render_soulpack_detail(base: str, entry: dict) -> str:
    pid = str(entry.get("id", "")).strip()
    manifest = load_pack_manifest(pid)
    name = escape(str(manifest.get("name") or entry.get("name") or pid))
    role = escape(str(manifest.get("role") or ""))
    ver = escape(str(manifest.get("version") or entry.get("version") or ""))
    tags = [str(t) for t in (manifest.get("tags") or entry.get("tags") or [])]
    tags_html = escape(", ".join(tags))
    soul = escape(load_pack_file(pid, "SOUL.md") or "(No SOUL.md)")
    identity = escape(load_pack_file(pid, "IDENTITY.md") or "(No IDENTITY.md)")
    style = escape(load_pack_file(pid, "STYLE.md") or "(No STYLE.md)")
    pid_esc = escape(pid)
    gh = f"https://github.com/mziqudhd92/soul-os/tree/main/packs/soulpacks/{pid}"

    body = f"""
    <section class="site-shell page-hero">
      <p class="sub"><a href="{base}soulpacks/">← All SoulPacks</a></p>
      <h1>{name}</h1>
      <p>{role}</p>
      <p class="sub" style="margin-top:0.75rem"><code>{pid_esc}</code> · v{ver} · MIT · {tags_html}</p>
      <div class="btn-row" style="margin-top:1.25rem">
        <a class="btn btn-primary" href="{base}get-started/">Use with sidecar</a>
        <a class="btn btn-ghost" href="{gh}">Source on GitHub</a>
      </div>
    </section>

    <section class="site-shell prose-block">
      <h2>What this pack is for</h2>
      <div class="pack-doc" style="white-space:pre-wrap;line-height:1.55;margin:1rem 0 2rem">{soul}</div>

      <h2>Identity</h2>
      <div class="pack-doc" style="white-space:pre-wrap;line-height:1.55;margin:1rem 0 2rem">{identity}</div>

      <h2>Style</h2>
      <div class="pack-doc" style="white-space:pre-wrap;line-height:1.55;margin:1rem 0 2rem">{style}</div>

      <h2>Import</h2>
      <pre><code>curl -s -X POST http://localhost:8000/v1/avatars/import-soulpack \\
  -H 'content-type: application/json' \\
  -d '{{"pack_id":"{pid_esc}","persist":true}}'</code></pre>
      <p>Or Studio → <strong>SoulPacks</strong> → Open / Deploy. Guide:
      <a href="https://github.com/mziqudhd92/soul-os/blob/main/docs/guides/persona-packs.md">persona-packs.md</a>.</p>
    </section>
"""
    return page(
        base=base,
        title=f"{name} — SoulPack — SoulOS",
        description=f"{name} ({pid}): {role}. First-party MIT SoulPack for SoulOS.",
        active="soulpacks",
        path=f"soulpacks/{pid}/",
        body=body,
        json_ld=[
            {
                "@context": "https://schema.org",
                "@type": "CreativeWork",
                "name": str(manifest.get("name") or entry.get("name") or pid),
                "alternateName": pid,
                "description": (
                    f"{role}. First-party MIT SoulPack for SoulOS hybrid sidecar."
                    if role
                    else f"SoulOS SoulPack {pid}"
                ),
                "license": "https://spdx.org/licenses/MIT.html",
                "url": absolute_url(base, f"soulpacks/{pid}/"),
                "isPartOf": {
                    "@type": "CollectionPage",
                    "name": "SoulOS SoulPacks",
                    "url": absolute_url(base, "soulpacks/"),
                },
                "keywords": tags,
                "codeRepository": gh,
            }
        ],
    )


def render_soulpacks(base: str) -> str:
    catalog = load_soulpack_catalog()
    pack_cards = []
    for p in catalog:
        pid = str(p.get("id", ""))
        pid_esc = escape(pid)
        name = escape(str(p.get("name", pid)))
        ver = escape(str(p.get("version", "")))
        tags = [str(t) for t in (p.get("tags") or [])]
        tags_esc = escape(", ".join(tags[:6]))
        role = escape(str(load_pack_manifest(pid).get("role") or ""))
        search_blob = escape(
            " ".join([pid, str(p.get("name", "")), role, " ".join(tags)]).lower()
        )
        pack_cards.append(
            f"""
        <article class="path-tile pack-card" data-search="{search_blob}">
          <h3><a href="{base}soulpacks/{pid_esc}/">{name}</a></h3>
          <p>{role}</p>
          <p style="margin-top:0.5rem"><code>{pid_esc}</code> · v{ver} · MIT</p>
          <p style="margin-top:0.5rem;font-size:0.9rem;color:var(--muted)">{tags_esc}</p>
          <p style="margin-top:0.75rem"><a href="{base}soulpacks/{pid_esc}/">View details →</a></p>
        </article>"""
        )
    packs_html = "\n".join(pack_cards) or "<p class='sub'>No packs in catalog yet.</p>"
    count = len(catalog)

    body = f"""
    <section class="site-shell page-hero">
      <h1>SoulPacks</h1>
      <p>First-party, MIT-licensed persona packages. Browse {count} packs, open a detail page to read the soul, then import via API, CLI, or Soul Studio.</p>
      <div class="btn-row" style="margin-top:1.25rem">
        <a class="btn btn-primary" href="#catalog">Browse catalog</a>
        <a class="btn btn-ghost" href="https://github.com/mziqudhd92/soul-os/blob/main/docs/guides/persona-packs.md">Full guide</a>
        <a class="btn btn-ghost" href="{base}get-started/">Get started</a>
      </div>
    </section>

    <section class="section">
      <div class="site-shell">
        <h2>What is a SoulPack?</h2>
        <p class="sub">A SoulPack is a small directory under <code>packs/soulpacks/</code>: markdown persona slices plus a <code>pack.json</code> manifest (always <code>license: MIT</code>). The kernel compiles it into a validated <code>.soul.json</code> with HEXACO MSV, then optionally <code>ensure</code>s an avatar.</p>
        <div class="path-grid" style="margin-top:1.25rem">
          <div class="path-tile">
            <h3>MIT only</h3>
            <p>Import rejects any non-MIT pack. Content stays first-party and redistributable with SoulOS.</p>
          </div>
          <div class="path-tile">
            <h3>Browse &amp; understand</h3>
            <p>Each pack has a detail page with role, SOUL, identity, style, and copy-paste import.</p>
          </div>
          <div class="path-tile">
            <h3>Safe paths</h3>
            <p>Manifest <code>files</code> must stay inside the pack directory — traversal is rejected.</p>
          </div>
          <div class="path-tile">
            <h3>MSV precedence</h3>
            <p><code>baseline_msv</code> in pack.json ≫ named preset ≫ schema defaults.</p>
          </div>
        </div>
      </div>
    </section>

    <section class="section" id="catalog">
      <div class="site-shell">
        <h2>Catalog ({count})</h2>
        <p class="sub">Filter by name, id, role, or tag. Click a pack to read how it thinks and how to import it.</p>
        <p style="margin:1rem 0 1.25rem">
          <label for="pack-filter" class="sub">Search</label><br>
          <input id="pack-filter" type="search" placeholder="e.g. tutor, sales, security…"
            style="width:min(100%,28rem);margin-top:0.35rem;padding:0.65rem 0.85rem;border:1px solid var(--border, #ccc);border-radius:6px;background:var(--bg, #fff);color:inherit;font:inherit">
        </p>
        <p id="pack-filter-empty" class="sub" hidden>No packs match that filter.</p>
        <div class="path-grid" id="pack-grid">
{packs_html}
        </div>
      </div>
    </section>

    <section class="site-shell prose-block">
      <h2>How to use</h2>
      <h3>1. API</h3>
      <pre><code># List
curl -s http://localhost:8000/v1/soulpacks

# Convert only (no DB write)
curl -s -X POST http://localhost:8000/v1/avatars/import-soulpack \\
  -H 'content-type: application/json' \\
  -d '{{"pack_id":"support-agent","persist":false}}'

# Ensure avatar
curl -s -X POST http://localhost:8000/v1/avatars/import-soulpack \\
  -H 'content-type: application/json' \\
  -d '{{"pack_id":"companion","persist":true}}'</code></pre>
      <p>Errors use RFC 7807 codes: <code>SOULPACK_NOT_FOUND</code>, <code>SOULPACK_LICENSE_REJECTED</code>, <code>SOULPACK_INVALID</code>.</p>

      <h3>2. CLI</h3>
      <pre><code>cd packages/soulos-core
.venv/bin/python -m cli pack list
.venv/bin/python -m cli pack import support-agent --persist false
.venv/bin/python -m cli pack export companion -o /tmp/my-companion</code></pre>

      <h3>3. Soul Studio</h3>
      <p>Run Studio locally (<code>soulos-studio</code> on :8765), open the <strong>SoulPacks</strong> tab, then <em>Open in Studio</em> or <em>Deploy to kernel</em>.</p>

      <h3>4. Sidecar seed</h3>
      <pre><code>python3 examples/soulpack-sidecar/seed_soulpack.py \\
  --pack-id support-agent --persist true \\
  --kernel http://localhost:8000</code></pre>
      <p>Then continue with hybrid <code>prepare → your LLM → complete</code>.</p>

      <h2>How to improve / author packs</h2>
      <ol>
        <li>Copy an existing pack under <code>packs/soulpacks/</code> or export one with <code>soulos pack export</code>.</li>
        <li>Edit <code>SOUL.md</code> (and optional <code>IDENTITY.md</code> / <code>STYLE.md</code>) — keep prose MIT-authored.</li>
        <li>Update <code>pack.json</code>: <code>id</code>, <code>name</code>, <code>version</code>, <code>license: "MIT"</code>, <code>files</code>, and either <code>baseline_msv</code> or <code>msv_preset</code>.</li>
        <li>Register the pack in <code>packs/soulpacks/catalog.json</code>.</li>
        <li>Add or extend tests in <code>packages/soulos-core/test_soulpacks.py</code> (compile + MIT checks).</li>
        <li>Open a PR — CI runs kernel tests and the license copyleft gate.</li>
      </ol>
      <pre><code>packs/soulpacks/
  catalog.json
  _presets.yaml
  my-pack/
    pack.json      # license must be MIT
    SOUL.md
    IDENTITY.md    # optional
    STYLE.md       # optional</code></pre>

      <h2>Docs &amp; plan</h2>
      <ul>
        <li><a href="https://github.com/mziqudhd92/soul-os/blob/main/docs/guides/persona-packs.md">SoulPacks guide</a></li>
        <li><a href="https://github.com/mziqudhd92/soul-os/blob/main/docs/design/soulpacks-tdd-plan.md">TDD delivery plan (M1–M5)</a></li>
        <li><a href="https://github.com/mziqudhd92/soul-os/blob/main/docs/reference/hybrid-api.md">Hybrid API (import-soulpack)</a></li>
        <li><a href="https://github.com/mziqudhd92/soul-os/tree/main/examples/soulpack-sidecar">examples/soulpack-sidecar</a></li>
      </ul>
    </section>
    <script>
    (function () {{
      var input = document.getElementById("pack-filter");
      var grid = document.getElementById("pack-grid");
      var empty = document.getElementById("pack-filter-empty");
      if (!input || !grid) return;
      var cards = Array.prototype.slice.call(grid.querySelectorAll(".pack-card"));
      function apply() {{
        var q = (input.value || "").trim().toLowerCase();
        var shown = 0;
        cards.forEach(function (card) {{
          var hay = card.getAttribute("data-search") || "";
          var ok = !q || hay.indexOf(q) !== -1;
          card.hidden = !ok;
          if (ok) shown += 1;
        }});
        if (empty) empty.hidden = shown !== 0;
      }}
      input.addEventListener("input", apply);
    }})();
    </script>
"""
    return page(
        base=base,
        title="SoulPacks — MIT persona packages — SoulOS",
        description=(
            f"Browse and understand {count} SoulOS SoulPacks: first-party MIT personas "
            "with search, detail pages, and import examples for hybrid sidecar agents."
        ),
        active="soulpacks",
        path="soulpacks/",
        body=body,
        json_ld=[
            {
                "@context": "https://schema.org",
                "@type": "CollectionPage",
                "name": "SoulOS SoulPacks",
                "description": (
                    f"{count} first-party MIT persona packages for SoulOS — "
                    "browse, search, and import ready agent roles."
                ),
                "url": absolute_url(base, "soulpacks/"),
                "isPartOf": {
                    "@type": "WebSite",
                    "name": "SoulOS",
                    "url": absolute_url(base, ""),
                },
                "mainEntity": {
                    "@type": "ItemList",
                    "numberOfItems": count,
                    "itemListElement": [
                        {
                            "@type": "ListItem",
                            "position": i + 1,
                            "name": str(p.get("name") or p.get("id")),
                            "url": absolute_url(
                                base, f"soulpacks/{str(p.get('id', '')).strip()}/"
                            ),
                        }
                        for i, p in enumerate(catalog)
                        if str(p.get("id", "")).strip()
                    ],
                },
            }
        ],
    )
