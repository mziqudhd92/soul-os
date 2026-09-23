"""Product version SSOT tests."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import versioning
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


def test_get_product_version_strips_v_and_skips_blank(tmp_path: Path):
    versioning.get_product_version.cache_clear()
    vfile = tmp_path / "VERSION"
    vfile.write_text("v2.0.0\n", encoding="utf-8")

    fake_here = MagicMock()
    # monorepo root VERSION
    root_candidate = MagicMock()
    root_candidate.is_file.return_value = True
    root_candidate.read_text.return_value = "v2.0.0\n"
    fake_here.parent.parent.__truediv__.return_value = root_candidate

    with patch("versioning.Path") as P:
        P.__file__ = "x"
        resolved = MagicMock()
        resolved.parent = fake_here
        P.return_value.resolve.return_value = resolved
        # Also used as Path(__file__)
        P.side_effect = None
        inst = MagicMock()
        inst.resolve.return_value = resolved
        P.return_value = inst
        versioning.get_product_version.cache_clear()
        assert get_product_version() == "2.0.0"

    versioning.get_product_version.cache_clear()


def test_get_product_version_falls_back_to_metadata_then_default():
    versioning.get_product_version.cache_clear()

    def all_missing(*_a, **_k):
        cand = MagicMock()
        cand.is_file.return_value = False
        return cand

    with (
        patch("versioning.Path") as P,
        patch("importlib.metadata.version", return_value="8.8.8"),
    ):
        here = MagicMock()
        here.parent.parent.__truediv__ = all_missing
        here.parent.__truediv__ = all_missing
        P.return_value.resolve.return_value.parent = here
        P.cwd.return_value.__truediv__ = all_missing
        versioning.get_product_version.cache_clear()
        assert get_product_version() == "8.8.8"

    versioning.get_product_version.cache_clear()
    with (
        patch("versioning.Path") as P,
        patch("importlib.metadata.version", side_effect=Exception("gone")),
    ):
        here = MagicMock()
        here.parent.parent.__truediv__ = all_missing
        here.parent.__truediv__ = all_missing
        P.return_value.resolve.return_value.parent = here
        P.cwd.return_value.__truediv__ = all_missing
        versioning.get_product_version.cache_clear()
        assert get_product_version() == "0.0.0"

    versioning.get_product_version.cache_clear()
