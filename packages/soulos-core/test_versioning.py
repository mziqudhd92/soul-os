"""Product version SSOT tests."""

from pathlib import Path

from versioning import get_product_version

ROOT = Path(__file__).resolve().parents[2]


def test_product_version_matches_version_file():
    expected = (ROOT / "VERSION").read_text(encoding="utf-8").strip().splitlines()[0]
    if expected.startswith("v"):
        expected = expected[1:]
    assert get_product_version() == expected


def test_version_mirrors_in_sync():
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    from soulos_version import collect_mismatches

    assert collect_mismatches(ROOT) == []
