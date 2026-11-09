"""private_dir() must only ever hand back a directory owned by the current user with mode 0700."""

import os
import stat
from pathlib import Path

import pytest

from video_cut.services import private_dir as private_dir_module
from video_cut.services.private_dir import private_dir


@pytest.fixture
def temp_root(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.setattr(private_dir_module.tempfile, "gettempdir", lambda: str(tmp_path))
    return tmp_path


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def test_creates_a_private_directory_named_after_the_user(temp_root: Path) -> None:
    path = private_dir("video_cut_cache")

    assert path == temp_root / f"video_cut_cache-{os.getuid()}"
    assert _mode(path) == 0o700
    assert private_dir("video_cut_cache") == path


def test_tightens_an_existing_directory_with_loose_permissions(temp_root: Path) -> None:
    existing = temp_root / f"video_cut_cache-{os.getuid()}"
    existing.mkdir(mode=0o755)

    assert private_dir("video_cut_cache") == existing
    assert _mode(existing) == 0o700


def test_does_not_follow_a_symlink_planted_at_the_expected_path(temp_root: Path, tmp_path: Path) -> None:
    target = tmp_path / "elsewhere"
    target.mkdir()
    planted = temp_root / f"video_cut_cache-{os.getuid()}"
    planted.symlink_to(target)

    path = private_dir("video_cut_cache")

    assert path != planted
    assert path.is_dir() and not path.is_symlink()
    assert _mode(path) == 0o700
    assert list(target.iterdir()) == []


def test_does_not_use_a_regular_file_at_the_expected_path(temp_root: Path) -> None:
    planted = temp_root / f"video_cut_cache-{os.getuid()}"
    planted.write_bytes(b"")

    path = private_dir("video_cut_cache")

    assert path != planted
    assert path.is_dir()
    assert _mode(path) == 0o700
