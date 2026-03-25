"""Tests for package_clawborate_skill tar.gz generation."""
from __future__ import annotations

import tarfile
from pathlib import Path

import pytest

from backend.package_clawborate_skill import build_tarball


@pytest.fixture
def skill_dir_with_files(tmp_path: Path) -> Path:
    """Create a minimal skill directory structure for testing."""
    skill = tmp_path / "skills" / "clawborate-skill"
    (skill / "runtime").mkdir(parents=True)
    (skill / "scripts").mkdir(parents=True)
    (skill / "agents").mkdir(parents=True)
    (skill / "assets").mkdir(parents=True)

    # Top-level files
    (skill / "SKILL.md").write_text("# Test Skill", encoding="utf-8")
    (skill / "bundle_manifest.json").write_text("{}", encoding="utf-8")
    (skill / "requirements.txt").write_text("requests>=2.31.0", encoding="utf-8")

    # Runtime files
    (skill / "runtime" / "__init__.py").write_text("", encoding="utf-8")
    (skill / "runtime" / "config.py").write_text("X=1", encoding="utf-8")

    # Script files
    (skill / "scripts" / "install.py").write_text("print('hi')", encoding="utf-8")

    # Agent files
    (skill / "agents" / "openai.yaml").write_text("interface:", encoding="utf-8")

    # Asset files
    (skill / "assets" / "icon_small.png").write_bytes(b"\x89PNG")
    (skill / "assets" / "icon_large.png").write_bytes(b"\x89PNG")

    # Files that should be excluded
    cache = skill / "runtime" / "__pycache__"
    cache.mkdir()
    (cache / "config.cpython-310.pyc").write_bytes(b"\x00")

    return skill


def test_build_tarball_creates_archive(skill_dir_with_files: Path, tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    tarball = build_tarball(skill_dir=skill_dir_with_files, dist_dir=dist)

    assert tarball.exists()
    assert tarball.name == "clawborate-skill.tar.gz"


def test_build_tarball_has_prefix(skill_dir_with_files: Path, tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    tarball = build_tarball(skill_dir=skill_dir_with_files, dist_dir=dist)

    with tarfile.open(tarball, "r:gz") as tf:
        names = tf.getnames()

    # All entries should start with "clawborate-skill/"
    for name in names:
        assert name.startswith("clawborate-skill/") or name == "clawborate-skill", f"Entry missing prefix: {name}"


def test_build_tarball_excludes_pycache(skill_dir_with_files: Path, tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    tarball = build_tarball(skill_dir=skill_dir_with_files, dist_dir=dist)

    with tarfile.open(tarball, "r:gz") as tf:
        names = tf.getnames()

    pycache_entries = [n for n in names if "__pycache__" in n or n.endswith(".pyc")]
    assert pycache_entries == [], f"__pycache__/.pyc files should be excluded: {pycache_entries}"


def test_build_tarball_contains_expected_files(skill_dir_with_files: Path, tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    tarball = build_tarball(skill_dir=skill_dir_with_files, dist_dir=dist)

    with tarfile.open(tarball, "r:gz") as tf:
        names = tf.getnames()

    assert "clawborate-skill/SKILL.md" in names
    assert "clawborate-skill/bundle_manifest.json" in names
    assert "clawborate-skill/runtime/__init__.py" in names
    assert "clawborate-skill/scripts/install.py" in names
    assert "clawborate-skill/agents/openai.yaml" in names
    assert "clawborate-skill/assets/icon_small.png" in names
