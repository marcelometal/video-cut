"""Tests for overlay audio playback and volume adjustment."""

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")

from video_cut.models import OverlayItem, Segment
from video_cut.services.export_service import ExportService
from video_cut.services.overlay_audio_player import OverlayAudioPlayer
from video_cut.services.probe_service import ProbeService


def test_overlay_audio_player_lifecycle_and_volume(tmp_path: Path, monkeypatch):
    """Test OverlayAudioPlayer tracks active items, sets volume and handles cleanup."""
    audio_path = tmp_path / "sound.wav"
    audio_path.write_bytes(b"RIFFdummyWAVEfmt ")

    # Mock ProbeService.probe_duration
    monkeypatch.setattr(ProbeService, "probe_duration", lambda p: 10.0)

    audio_item = OverlayItem(
        item_type="audio",
        media_path=audio_path,
        audio_start=0.0,
        audio_end=10.0,
        audio_volume=0.75,
        is_loop=True,
    )

    player = OverlayAudioPlayer()

    # 1. Sync items creates media file
    player.sync_items([audio_item])
    assert audio_item.id in player._media_files
    mf = player._media_files[audio_item.id]
    assert mf is not None

    # 2. Update playback adjusts volume
    # Mock mf.is_prepared, get_duration, get_timestamp
    monkeypatch.setattr(mf, "is_prepared", lambda: True)
    monkeypatch.setattr(mf, "get_duration", lambda: 10_000_000)
    monkeypatch.setattr(mf, "get_timestamp", lambda: 1_000_000)

    player.update_playback([audio_item], rel_time=2.0, is_playing=True)
    assert abs(mf.get_volume() - 0.75) < 0.01

    # 3. Pause and Cleanup
    player.pause_all()
    player.cleanup()
    assert len(player._media_files) == 0


def test_overlay_video_audio_toggle(tmp_path: Path, monkeypatch):
    """Test video overlays only have active audio player when enable_audio is True."""
    video_path = tmp_path / "clip.mp4"
    video_path.write_bytes(b"dummy_video")

    vid_item = OverlayItem(
        item_type="video",
        media_path=video_path,
        enable_audio=False,
        audio_volume=1.5,
    )

    player = OverlayAudioPlayer()

    # When enable_audio is False, no media file is created
    player.sync_items([vid_item])
    assert vid_item.id not in player._media_files

    # When enable_audio is True, media file is created
    vid_item.enable_audio = True
    player.sync_items([vid_item])
    assert vid_item.id in player._media_files

    # Disabling cleans it up
    vid_item.enable_audio = False
    player.sync_items([vid_item])
    assert vid_item.id not in player._media_files
    player.cleanup()


def test_export_with_custom_audio_volume(tmp_path: Path, monkeypatch):
    """Test export filter_complex applies volume=X filter when audio_volume is set."""
    monkeypatch.setattr(ProbeService, "has_audio", lambda p: True)
    src_video = tmp_path / "base.mp4"
    src_video.write_bytes(b"dummy")
    sub_video = tmp_path / "sub.mp4"
    sub_video.write_bytes(b"dummy_sub")
    audio_track = tmp_path / "music.mp3"
    audio_track.write_bytes(b"dummy_music")

    seg = Segment(
        id="seg_vol",
        source_path=src_video,
        start_time=0.0,
        end_time=5.0,
        source_duration=5.0,
        overlays=[
            OverlayItem(item_type="video", media_path=sub_video, enable_audio=True, audio_volume=0.6),
            OverlayItem(item_type="audio", media_path=audio_track, audio_volume=1.4),
        ],
    )

    service = ExportService()
    cmd = service.build_ffmpeg_command(
        segments=[seg],
        output_path=tmp_path / "vol_out.mp4",
        target_width=640,
        target_height=360,
        overlay_temp_dir=tmp_path / "tmp_vol",
    )

    fc_idx = cmd.index("-filter_complex")
    fc_str = cmd[fc_idx + 1]

    # Video overlay audio has volume=0.60
    assert "volume=0.60" in fc_str
    # Audio overlay has volume=1.40
    assert "volume=1.40" in fc_str
