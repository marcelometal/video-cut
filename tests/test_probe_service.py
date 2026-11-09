"""ProbeService caching and timeout behaviour."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from video_cut.services import probe_service
from video_cut.services.probe_service import PROBE_TIMEOUT, ProbeService


@pytest.fixture(autouse=True)
def clear_probe_cache():
    ProbeService.clear_cache()
    yield
    ProbeService.clear_cache()


@pytest.fixture
def ffprobe_calls(monkeypatch) -> list[dict]:
    calls: list[dict] = []
    real_run = subprocess.run

    def counting_run(cmd, **kwargs):
        calls.append(kwargs)
        return real_run(cmd, **kwargs)

    monkeypatch.setattr(probe_service.subprocess, "run", counting_run)
    return calls


def test_repeated_probes_spawn_ffprobe_once(sample_video: Path, ffprobe_calls: list[dict]) -> None:
    first = ProbeService.probe(sample_video)
    assert first is not None and first.width == 640 and first.height == 360
    assert ProbeService.probe(sample_video) is first
    assert ProbeService.has_audio(sample_video) is True
    assert ProbeService.has_audio(sample_video) is True
    assert ProbeService.probe_duration(sample_video) == pytest.approx(5.0, abs=0.1)
    assert ProbeService.probe_duration(sample_video) == pytest.approx(5.0, abs=0.1)

    assert len(ffprobe_calls) == 3
    assert all(call["timeout"] == PROBE_TIMEOUT for call in ffprobe_calls)


def test_cache_is_keyed_on_resolved_path_size_and_mtime(tmp_path: Path, sample_video: Path, ffprobe_calls: list[dict]) -> None:
    clip = tmp_path / "clip.mp4"
    shutil.copyfile(sample_video, clip)
    ProbeService.probe(clip)
    ProbeService.probe(clip)
    assert len(ffprobe_calls) == 1

    link = tmp_path / "link.mp4"
    link.symlink_to(clip)
    ProbeService.probe(link)
    assert len(ffprobe_calls) == 1

    st = clip.stat()
    os.utime(clip, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))
    ProbeService.probe(clip)
    assert len(ffprobe_calls) == 2


def test_timeout_is_a_failure_and_is_not_cached(sample_video: Path, monkeypatch) -> None:
    attempts: list[list[str]] = []

    def hanging_run(cmd, **kwargs):
        attempts.append(cmd)
        raise subprocess.TimeoutExpired(cmd, kwargs["timeout"])

    monkeypatch.setattr(probe_service.subprocess, "run", hanging_run)

    assert ProbeService.probe(sample_video) is None
    assert ProbeService.probe(sample_video) is None
    assert ProbeService.probe_duration(sample_video) is None
    assert ProbeService.has_audio(sample_video) is False
    assert len(attempts) == 4


def test_missing_file_is_not_probed(tmp_path: Path, ffprobe_calls: list[dict]) -> None:
    missing = tmp_path / "missing.mp4"
    assert ProbeService.probe(missing) is None
    assert ProbeService.probe_duration(missing) is None
    assert ProbeService.has_audio(missing) is False
    assert ffprobe_calls == []
