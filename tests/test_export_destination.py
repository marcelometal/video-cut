"""Export destination safety: never overwrite a source and leave no partial files behind."""

import time
from pathlib import Path

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GLib

from video_cut.models import ExportSettings, ProjectTimeline
from video_cut.services.export_service import ExportService

REFUSED = "Destination is one of the source files"


def _run_export(source: Path, destination: Path, settings: ExportSettings | None = None) -> tuple[bool, str | None]:
    timeline = ProjectTimeline()
    seg = timeline.add_video(source, 5.0)
    seg.start_time = 0.0
    seg.end_time = 1.0

    result: dict[str, object] = {}

    def on_done(success: bool, error: str | None) -> None:
        result["success"] = success
        result["error"] = error

    ExportService().export_async(
        segments=timeline.segments,
        output_path=destination,
        on_progress=lambda fraction, cur_s: None,
        on_done=on_done,
        settings=settings,
    )

    ctx = GLib.MainContext.default()
    deadline = time.monotonic() + 60.0
    while "success" not in result and time.monotonic() < deadline:
        while ctx.pending():
            ctx.iteration(False)
        time.sleep(0.02)
    assert "success" in result, "export did not finish"
    return bool(result["success"]), result["error"]  # type: ignore[return-value]


def _other_files(directory: Path, known: set[Path]) -> list[Path]:
    return sorted(p for p in directory.iterdir() if p not in known)


def test_source_opened_through_symlink_is_not_overwritten(tmp_path: Path, sample_video: Path) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(sample_video.read_bytes())
    link = tmp_path / "link.mp4"
    link.symlink_to(source)
    original = source.read_bytes()

    success, error = _run_export(link, source)

    assert success is False
    assert error == REFUSED
    assert source.read_bytes() == original
    assert _other_files(tmp_path, {source, link}) == []


def test_destination_symlink_to_source_is_refused(tmp_path: Path, sample_video: Path) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(sample_video.read_bytes())
    link = tmp_path / "link.mp4"
    link.symlink_to(source)
    original = source.read_bytes()

    success, error = _run_export(source, link)

    assert success is False
    assert error == REFUSED
    assert source.read_bytes() == original
    assert link.is_symlink()


def test_failed_export_leaves_no_partial_file(tmp_path: Path, sample_video: Path) -> None:
    destination = tmp_path / "out.mp4"

    success, error = _run_export(sample_video, destination, ExportSettings(audio_codec="no_such_encoder"))

    assert success is False
    assert error is not None and error.startswith("FFmpeg failed")
    assert not destination.exists()
    assert _other_files(tmp_path, set()) == []


def test_successful_export_replaces_destination(tmp_path: Path, sample_video: Path) -> None:
    destination = tmp_path / "out.mp4"
    destination.write_bytes(b"stale")

    success, error = _run_export(sample_video, destination)

    assert success is True, error
    assert destination.stat().st_size > 1000
    assert _other_files(tmp_path, {destination}) == []
