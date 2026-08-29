"""FAQ content for homepage AEO."""

from __future__ import annotations

from html import escape

from .common import ROOT, load_soulpack_catalog, page, absolute_url

def faq_items() -> list[tuple[str, str]]:
    pack_count = len(load_soulpack_catalog())
    return [
        (
            "What is SoulOS?",
            "SoulOS is an open-source identity and episodic memory sidecar for AI agents. "
            "It provides HEXACO MSV personality, pgvector memory, and a hybrid prepare/complete "
            "API so your existing LLM keeps generation.",
        ),
        (
            "When should I use SoulOS?",
            "Use SoulOS when you need persistent persona beyond a static system prompt, "
            "episodic memory across sessions, a hybrid sidecar next to Bedrock/OpenAI/LiteLLM, "
            "MCP tools for memory and identity in Cursor or Claude, or ready MIT SoulPack personas "
            "(travel, sales, tutor, support, and more).",
        ),
        (
            "What is the primary integration path?",
            "ensure_avatar → POST /hybrid/prepare → your LLM → POST /hybrid/complete. "
            "See the sidecar integration guide and npm run smoke:hybrid.",
        ),
        (
            "Is SoulOS free and open source?",
            "Yes. The kernel, SDK, Studio, SoulPacks, and examples are MIT-licensed. "
            "The project site is free on GitHub Pages and synced from the same repository.",
        ),
        (
            "What are SoulPacks?",
            f"SoulPacks are {pack_count} first-party MIT persona packages in packs/soulpacks/ "
            "(travel, SDR, tutor, tech support, developer coach, exec assistant, research, "
            "customer success, security, PM, data, recruiter, content, and more). "
            "List with GET /v1/soulpacks, import with POST /v1/avatars/import-soulpack, "
            "or use the Studio SoulPacks tab.",
        ),
        (
            "Where can I browse SoulPacks?",
            "On the GitHub Pages catalog at /soulpacks/ — search by name, role, or tag, "
            "then open a detail page for SOUL, identity, style, and a copy-paste import example. "
            "Each pack is also listed in the site sitemap for crawlers.",
        ),
    ]


def faq_html() -> str:
    items = []
    for question, answer in faq_items():
        items.append(
            f"""
          <details class="faq-item">
            <summary>{escape(question)}</summary>
            <p>{escape(answer)}</p>
          </details>"""
        )
    return "\n".join(items)


def faq_json_ld() -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": question,
                "acceptedAnswer": {"@type": "Answer", "text": answer},
            }
            for question, answer in faq_items()
        ],
    }
