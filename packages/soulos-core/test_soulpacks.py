"""TDD tests for SoulPacks compile / catalog / export."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runtime.soulpacks import (
    SoulPackError,
    SoulPackLicenseError,
    SoulPackNotFoundError,
    compile_pack,
    default_external_key,
    export_pack,
    list_packs,
    load_pack,
    packs_root,
)
from soul_validation import validate_soul_payload

REPO = Path(__file__).resolve().parents[2]
PACKS = REPO / "packs" / "soulpacks"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "soulpacks"


def test_packs_root_defaults_to_repo_packs():
    assert packs_root() == PACKS.resolve()


def test_load_catalog_lists_support_agent():
    packs = list_packs(root=PACKS)
    ids = {p["id"] for p in packs}
    assert "support-agent" in ids
    support = next(p for p in packs if p["id"] == "support-agent")
    assert support["version"] == "1.0.0"
    assert "support" in support.get("tags", [])


def test_compile_merges_markdown_order():
    soul, _runtime, _warnings = compile_pack("support-agent", root=PACKS)
    assert "billing" in soul["description"]
    assert "Site Support" in soul["description"]
    assert "concise and empathetic" in soul["description"]
    # SOUL.md before IDENTITY before STYLE
    assert soul["description"].index("billing") < soul["description"].index("# Identity")
    assert soul["description"].index("# Identity") < soul["description"].index("# Style")


def test_compile_applies_baseline_msv_from_pack():
    soul, _, _ = compile_pack("companion", root=PACKS)
    hexaco = soul["baseline_msv"]["hexaco"]
    for key in "HEXACO":
        assert key in hexaco
        assert -1.0 <= hexaco[key] <= 1.0
    assert soul["baseline_msv"]["hexaco"]["A"] == pytest.approx(0.9)


def test_compile_applies_named_preset():
    soul, _, warnings = compile_pack("support-agent", root=PACKS)
    assert any("preset" in w.lower() for w in warnings)
    assert soul["baseline_msv"]["hexaco"]["H"] == pytest.approx(0.95)


def test_compile_rejects_non_mit_license(tmp_path: Path):
    pack = tmp_path / "bad"
    pack.mkdir()
    (pack / "SOUL.md").write_text("Hello.", encoding="utf-8")
    (pack / "pack.json").write_text(
        json.dumps(
            {
                "id": "bad",
                "name": "Bad",
                "version": "1.0.0",
                "license": "Apache-2.0",
                "role": "X",
                "attachment_style": "Secure",
                "files": ["SOUL.md"],
                "baseline_msv": {
                    "hexaco": {k: 0.0 for k in "HEXACO"},
                    "moral_foundations": {
                        "care_harm": 0.5,
                        "fairness_cheating": 0.5,
                        "loyalty_betrayal": 0.5,
                        "authority_subversion": 0.5,
                        "sanctity_degradation": 0.5,
                    },
                    "drives": {
                        "curiosity": 0.5,
                        "autonomy": 0.5,
                        "social_approval": 0.5,
                    },
                    "epistemic_uncertainty": 0.1,
                    "inner_monologue": "x",
                },
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "catalog.json").write_text(
        json.dumps({"packs": [{"id": "bad", "path": "bad"}]}), encoding="utf-8"
    )
    with pytest.raises(SoulPackLicenseError):
        compile_pack("bad", root=tmp_path)


def test_compile_rejects_missing_soul_fields(tmp_path: Path):
    pack = tmp_path / "broken"
    pack.mkdir()
    (pack / "SOUL.md").write_text("Hi.", encoding="utf-8")
    (pack / "pack.json").write_text(
        json.dumps(
            {
                "id": "broken",
                "name": "Broken",
                "version": "1.0.0",
                "license": "MIT",
                "role": "X",
                "attachment_style": "NotARealStyle",
                "files": ["SOUL.md"],
                "baseline_msv": {
                    "hexaco": {k: 0.0 for k in "HEXACO"},
                    "moral_foundations": {
                        "care_harm": 0.5,
                        "fairness_cheating": 0.5,
                        "loyalty_betrayal": 0.5,
                        "authority_subversion": 0.5,
                        "sanctity_degradation": 0.5,
                    },
                    "drives": {
                        "curiosity": 0.5,
                        "autonomy": 0.5,
                        "social_approval": 0.5,
                    },
                    "epistemic_uncertainty": 0.1,
                    "inner_monologue": "x",
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(SoulPackError):
        compile_pack("broken", root=tmp_path)


def test_default_external_key():
    assert default_external_key("support-agent", "1.0.0") == "soulos:support-agent@1.0.0"


def test_fixture_pack_roundtrip_validate():
    soul, runtime, _ = compile_pack("minimal", root=FIXTURES)
    validate_soul_payload(soul)
    assert runtime["source"]["type"] == "soulpack"
    assert runtime["source"]["license"] == "MIT"


def test_catalog_has_at_least_three_mit_packs():
    packs = list_packs(root=PACKS)
    assert len(packs) >= 3
    for p in packs:
        # license on catalog entry or load pack
        _, manifest = load_pack(p["id"], root=PACKS)
        assert manifest["license"] == "MIT"


def test_catalog_includes_new_vertical_packs():
    ids = {p["id"] for p in list_packs(root=PACKS)}
    for expected in (
        "travel-agent",
        "sales-sdr",
        "tutor",
        "tech-support",
        "developer",
        "friendly-friend",
        "warrior",
        "exec-assistant",
        "research-analyst",
        "customer-success",
        "security-coach",
        "product-manager",
        "data-analyst",
        "recruiter",
        "content-marketer",
        "onboarding-coach",
        "accessibility-editor",
        "meeting-notes",
    ):
        assert expected in ids


@pytest.mark.parametrize(
    "pack_id",
    [p["id"] for p in list_packs(root=PACKS)],
)
def test_each_catalog_pack_compiles(pack_id: str):
    soul, runtime, _ = compile_pack(pack_id, root=PACKS)
    validate_soul_payload(soul)
    assert runtime["source"]["id"] == pack_id


def test_export_soul_to_pack_dir(tmp_path: Path):
    soul, _, _ = compile_pack("companion", root=PACKS)
    out = export_pack(soul, tmp_path / "luna")
    assert (out / "pack.json").is_file()
    assert (out / "SOUL.md").is_file()
    manifest = json.loads((out / "pack.json").read_text(encoding="utf-8"))
    assert manifest["license"] == "MIT"
    # out_dir is the pack directory; parent is SOULPACKS_ROOT
    soul2, _, _ = compile_pack(out.name, root=tmp_path)
    assert soul2["name"] == soul["name"]
    assert "warm" in soul2["description"].lower() or "attuned" in soul2["description"].lower()


def test_export_rejects_if_license_not_mit(tmp_path: Path):
    """export_pack always stamps MIT — cannot export a non-MIT license field."""
    soul, _, _ = compile_pack("dev-twin", root=PACKS)
    out = export_pack(soul, tmp_path / "dev-twin")
    manifest = json.loads((out / "pack.json").read_text(encoding="utf-8"))
    assert manifest["license"] == "MIT"


def test_load_pack_missing():
    with pytest.raises(SoulPackNotFoundError):
        load_pack("does-not-exist", root=PACKS)


def _valid_msv(**hexaco_overrides: float) -> dict:
    hexaco = {k: 0.0 for k in "HEXACO"}
    hexaco.update(hexaco_overrides)
    return {
        "hexaco": hexaco,
        "moral_foundations": {
            "care_harm": 0.5,
            "fairness_cheating": 0.5,
            "loyalty_betrayal": 0.5,
            "authority_subversion": 0.5,
            "sanctity_degradation": 0.5,
        },
        "drives": {"curiosity": 0.5, "autonomy": 0.5, "social_approval": 0.5},
        "epistemic_uncertainty": 0.1,
        "inner_monologue": "test",
    }


def test_compile_rejects_path_traversal_in_files(tmp_path: Path):
    secret = tmp_path / "secret.txt"
    secret.write_text("SHOULD_NOT_READ", encoding="utf-8")
    pack = tmp_path / "evil"
    pack.mkdir()
    (pack / "SOUL.md").write_text("ok", encoding="utf-8")
    (pack / "pack.json").write_text(
        json.dumps(
            {
                "id": "evil",
                "name": "Evil",
                "version": "1.0.0",
                "license": "MIT",
                "role": "X",
                "attachment_style": "Secure",
                "files": ["../secret.txt"],
                "baseline_msv": _valid_msv(),
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(SoulPackError, match="Invalid pack file path|escapes"):
        compile_pack("evil", root=tmp_path)


def test_compile_rejects_path_traversal_pack_id(tmp_path: Path):
    with pytest.raises(SoulPackError, match="Invalid pack_id"):
        compile_pack("../etc", root=tmp_path)


def test_msv_precedence_baseline_beats_preset(tmp_path: Path):
    """Explicit baseline_msv >> msv_preset >> default_msv_dict()."""
    (tmp_path / "_presets.yaml").write_text(
        "presets:\n  loud:\n    hexaco: { H: 0.1, E: 0.1, X: 0.1, A: 0.1, C: 0.1, O: 0.1 }\n"
        "    inner_monologue: from-preset\n",
        encoding="utf-8",
    )
    pack = tmp_path / "pref"
    pack.mkdir()
    (pack / "SOUL.md").write_text("Hello.", encoding="utf-8")
    (pack / "pack.json").write_text(
        json.dumps(
            {
                "id": "pref",
                "name": "Pref",
                "version": "1.0.0",
                "license": "MIT",
                "role": "X",
                "attachment_style": "Secure",
                "files": ["SOUL.md"],
                "msv_preset": "loud",
                "baseline_msv": _valid_msv(H=0.99),
            }
        ),
        encoding="utf-8",
    )
    soul, _, warnings = compile_pack("pref", root=tmp_path, msv_preset="loud")
    assert soul["baseline_msv"]["hexaco"]["H"] == pytest.approx(0.99)
    assert not any("preset" in w.lower() for w in warnings)


def test_msv_precedence_preset_when_no_baseline(tmp_path: Path):
    (tmp_path / "_presets.yaml").write_text(
        "presets:\n  loud:\n    hexaco: { H: 0.11, E: 0.5, X: 0.5, A: 0.5, C: 0.5, O: 0.5 }\n"
        "    moral_foundations:\n"
        "      care_harm: 0.5\n"
        "      fairness_cheating: 0.5\n"
        "      loyalty_betrayal: 0.5\n"
        "      authority_subversion: 0.5\n"
        "      sanctity_degradation: 0.5\n"
        "    drives: { curiosity: 0.5, autonomy: 0.5, social_approval: 0.5 }\n"
        "    epistemic_uncertainty: 0.1\n"
        "    inner_monologue: from-preset\n",
        encoding="utf-8",
    )
    pack = tmp_path / "preset-only"
    pack.mkdir()
    (pack / "SOUL.md").write_text("Hello.", encoding="utf-8")
    (pack / "pack.json").write_text(
        json.dumps(
            {
                "id": "preset-only",
                "name": "Preset Only",
                "version": "1.0.0",
                "license": "MIT",
                "role": "X",
                "attachment_style": "Secure",
                "files": ["SOUL.md"],
                "msv_preset": "loud",
            }
        ),
        encoding="utf-8",
    )
    soul, _, warnings = compile_pack("preset-only", root=tmp_path)
    assert soul["baseline_msv"]["hexaco"]["H"] == pytest.approx(0.11)
    assert any("preset" in w.lower() for w in warnings)
