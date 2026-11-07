"""Tests for overlay export via FFmpeg filter_complex."""

import subprocess
from pathlib import Path

from video_cut.models import ExportSettings, OverlayItem, Segment
from video_cut.services.export_service import ExportService
from video_cut.services.probe_service import ProbeService


def test_build_ffmpeg_command_with_static_overlay(tmp_path: Path):
    """Test that static overlays generate PNG inputs and overlay filter in filter_complex."""
    video_path = tmp_path / "dummy.mp4"
    video_path.write_bytes(b"dummy")

    seg = Segment(
        id="seg1",
        source_path=video_path,
        start_time=0.0,
        end_time=5.0,
        source_duration=5.0,
        overlays=[
            OverlayItem(item_type="text", text="Watermark", font_size=36, x=0.5, y=0.5),
            OverlayItem(item_type="rect", fill_color="#ff0000", x=0.2, y=0.2, width=0.1, height=0.1),
        ],
    )
    assert seg.has_overlays

    service = ExportService()
    out_file = tmp_path / "output.mp4"
    overlay_dir = tmp_path / "overlays"

    cmd = service.build_ffmpeg_command(
        segments=[seg],
        output_path=out_file,
        target_width=1280,
        target_height=720,
        overlay_temp_dir=overlay_dir,
    )

    # Verify -loop 1 -i <png> input was generated
    assert "-loop" in cmd
    png_path = overlay_dir / "overlay_seg_0.png"
    assert str(png_path) in cmd
    assert png_path.exists()

    # Verify filter_complex contains overlay filter applied to v0_base before scale/pad
    fc_idx = cmd.index("-filter_complex")
    fc_str = cmd[fc_idx + 1]
    assert "[v0_base][1:v]overlay=0:0:shortest=1:eof_action=repeat[v0_overlaid]" in fc_str
    assert "[v0_overlaid]scale=1280:720" in fc_str


def test_build_ffmpeg_command_with_cropped_overlay(tmp_path: Path):
    """Test that overlays on cropped segments are rendered at cropped dimensions and composited before scale/pad."""
    video_path = tmp_path / "dummy.mp4"
    video_path.write_bytes(b"dummy")

    seg = Segment(
        id="seg_crop_ovl",
        source_path=video_path,
        start_time=0.0,
        end_time=5.0,
        source_duration=5.0,
        crop=(0.25, 0.25, 0.5, 0.5),  # 50% crop
        overlays=[
            OverlayItem(item_type="text", text="Center", x=0.5, y=0.5),
        ],
    )

    service = ExportService()
    out_file = tmp_path / "output.mp4"
    overlay_dir = tmp_path / "overlays_crop"

    cmd = service.build_ffmpeg_command(
        segments=[seg],
        output_path=out_file,
        target_width=1280,
        target_height=720,
        overlay_temp_dir=overlay_dir,
    )

    # Output PNG should be rendered at the cropped dimensions (0.5 * 1280 = 640, 0.5 * 720 = 360)
    png_path = overlay_dir / "overlay_seg_0.png"
    assert png_path.exists()
    from PIL import Image
    with Image.open(png_path) as im:
        assert im.width == 640
        assert im.height == 360

    fc_idx = cmd.index("-filter_complex")
    fc_str = cmd[fc_idx + 1]
    # Verify crop is in v0_base and overlay is applied directly to v0_base
    assert "crop=" in fc_str
    assert "[v0_base][1:v]overlay=0:0:shortest=1:eof_action=repeat[v0_overlaid]" in fc_str
    assert "[v0_overlaid]scale=1280:720" in fc_str


def test_build_ffmpeg_command_with_animated_overlay(tmp_path: Path):
    """Test that animated overlays (e.g. GIF or video) are passed directly to FFmpeg with looping."""
    video_path = tmp_path / "dummy.mp4"
    video_path.write_bytes(b"dummy")

    gif_path = tmp_path / "anim.gif"
    gif_path.write_bytes(b"dummy_gif")

    seg = Segment(
        id="seg1",
        source_path=video_path,
        start_time=0.0,
        end_time=1.0,
        source_duration=1.0,
        overlays=[
            OverlayItem(item_type="gif", media_path=gif_path, x=0.5, y=0.5, is_loop=True),
        ],
    )
    assert seg.has_overlays

    service = ExportService()
    out_file = tmp_path / "output.mp4"
    overlay_dir = tmp_path / "overlays"

    settings = ExportSettings(fps=10.0)
    cmd = service.build_ffmpeg_command(
        segments=[seg],
        output_path=out_file,
        target_width=640,
        target_height=360,
        settings=settings,
        overlay_temp_dir=overlay_dir,
    )

    # Verify animated overlay is passed directly to FFmpeg with stream_loop
    assert "-stream_loop" in cmd
    assert str(gif_path) in cmd
    fc_idx = cmd.index("-filter_complex")
    fc_str = cmd[fc_idx + 1]
    assert "[1:v]setpts=PTS-STARTPTS,scale=192:72,format=yuva420p[anim_0_0]" in fc_str
    assert "overlay=x='320.00-w/2':y='180.00-h/2':shortest=1:eof_action=repeat" in fc_str


def test_e2e_overlay_export_integration(tmp_path: Path):
    """Generate a real synthetic video clip, add text and shape overlays, and export to MP4."""
    src_video = tmp_path / "source.mp4"
    # Generate 2s video using lavfi
    gen_cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=25",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
        "-c:v", "libx264", "-c:a", "aac",
        str(src_video)
    ]
    res = subprocess.run(gen_cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"FFmpeg source generation failed: {res.stderr}"

    seg = Segment(
        id="seg_e2e",
        source_path=src_video,
        start_time=0.0,
        end_time=2.0,
        source_duration=2.0,
        overlays=[
            OverlayItem(
                item_type="text",
                text="Title Test",
                font_size=28,
                font_color="#ffff00",
                bold=True,
                x=0.5,
                y=0.3,
                width=0.6,
                height=0.2,
            ),
            OverlayItem(
                item_type="circle",
                fill_color="#ff0000",
                border_color="#ffffff",
                border_width=2,
                opacity=0.8,
                x=0.5,
                y=0.7,
                width=0.2,
                height=0.2,
            ),
        ],
    )

    out_video = tmp_path / "final_export.mp4"
    service = ExportService()
    cmd = service.build_ffmpeg_command(
        segments=[seg],
        output_path=out_video,
        target_width=320,
        target_height=240,
        overlay_temp_dir=tmp_path / "ovl_tmp",
    )

    run_res = subprocess.run(cmd, capture_output=True, text=True)
    assert run_res.returncode == 0, f"Export failed: {run_res.stderr}"
    assert out_video.exists()
    assert out_video.stat().st_size > 1000

    meta = ProbeService.probe(out_video)
    assert meta is not None
    assert meta.width == 320
    assert meta.height == 240
    assert meta.duration > 1.8


def test_e2e_cropped_overlay_export_integration(tmp_path: Path):
    """Test full export pipeline with video crop and overlay items simultaneously."""
    src_video = tmp_path / "src_crop.mp4"
    gen_cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=1:size=640x480:rate=25",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
        "-c:v", "libx264", "-c:a", "aac",
        str(src_video)
    ]
    res = subprocess.run(gen_cmd, capture_output=True, text=True)
    assert res.returncode == 0

    seg = Segment(
        id="seg_crop_e2e",
        source_path=src_video,
        start_time=0.0,
        end_time=1.0,
        source_duration=1.0,
        crop=(0.25, 0.25, 0.5, 0.5),  # 320x240 center crop
        overlays=[
            OverlayItem(item_type="text", text="Cropped Watermark", x=0.5, y=0.5, width=0.4, height=0.2),
        ],
    )

    out_video = tmp_path / "cropped_export.mp4"
    service = ExportService()
    cmd = service.build_ffmpeg_command(
        segments=[seg],
        output_path=out_video,
        overlay_temp_dir=tmp_path / "crop_ovl_tmp",
    )

    run_res = subprocess.run(cmd, capture_output=True, text=True)
    assert run_res.returncode == 0, f"Cropped overlay export failed: {run_res.stderr}"
    assert out_video.exists()

    meta = ProbeService.probe(out_video)
    assert meta is not None
    # Default target dimensions matched the 320x240 cropped aspect ratio without black bars
    assert meta.width == 320
    assert meta.height == 240


def test_e2e_video_and_emoji_overlay_export_integration(tmp_path: Path):
    """Test end-to-end export of video with both emoji and subvideo overlay in loop."""
    src_video = tmp_path / "base.mp4"
    sub_video = tmp_path / "sub.mp4"

    # Generate 2s base video
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=25",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
        "-c:v", "libx264", "-c:a", "aac",
        str(src_video)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Generate 1s subvideo
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=1:size=160x120:rate=25",
        "-pix_fmt", "yuv420p",
        str(sub_video)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    seg = Segment(
        id="seg_combo",
        source_path=src_video,
        start_time=0.0,
        end_time=2.0,
        source_duration=2.0,
        overlays=[
            OverlayItem(item_type="video", media_path=sub_video, x=0.5, y=0.5, width=0.4, height=0.4, is_loop=True, z_index=0),
            OverlayItem(item_type="emoji", text="🏀", x=0.2, y=0.2, width=0.15, height=0.15, z_index=1),
        ],
    )

    out_video = tmp_path / "combo_out.mp4"
    service = ExportService()
    cmd = service.build_ffmpeg_command(
        segments=[seg],
        output_path=out_video,
        target_width=320,
        target_height=240,
        overlay_temp_dir=tmp_path / "combo_tmp",
    )

    run_res = subprocess.run(cmd, capture_output=True, text=True)
    assert run_res.returncode == 0, f"Export failed: {run_res.stderr}"
    assert out_video.exists()
    assert out_video.stat().st_size > 1000

    meta = ProbeService.probe(out_video)
    assert meta is not None
    assert meta.width == 320
    assert meta.height == 240
    assert meta.duration > 1.8


def test_e2e_audio_overlay_and_video_audio_export(tmp_path: Path):
    """Test export mixing audio overlays and video overlays with enable_audio=True."""
    src_video = tmp_path / "base.mp4"
    sub_video = tmp_path / "sub_with_audio.mp4"
    audio_track = tmp_path / "overlay_music.mp3"

    # Generate 2s base video with audio
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=25",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
        "-c:v", "libx264", "-c:a", "aac",
        str(src_video)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Generate 1s subvideo with 880Hz audio
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=1:size=160x120:rate=25",
        "-f", "lavfi", "-i", "sine=frequency=880:duration=1",
        "-c:v", "libx264", "-c:a", "aac",
        str(sub_video)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Generate 1s audio track with 660Hz
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "sine=frequency=660:duration=1",
        "-c:a", "mp3",
        str(audio_track)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    seg = Segment(
        id="seg_audio_mix",
        source_path=src_video,
        start_time=0.0,
        end_time=2.0,
        source_duration=2.0,
        overlays=[
            OverlayItem(item_type="video", media_path=sub_video, x=0.5, y=0.5, enable_audio=True, is_loop=True),
            OverlayItem(item_type="audio", media_path=audio_track, audio_start=0.0, audio_end=1.0, is_loop=True),
        ],
    )

    out_video = tmp_path / "audio_mix_out.mp4"
    service = ExportService()
    cmd = service.build_ffmpeg_command(
        segments=[seg],
        output_path=out_video,
        target_width=320,
        target_height=240,
        overlay_temp_dir=tmp_path / "audio_mix_tmp",
    )

    # Verify amix in command
    fc_idx = cmd.index("-filter_complex")
    fc_str = cmd[fc_idx + 1]
    assert "amix=" in fc_str

    run_res = subprocess.run(cmd, capture_output=True, text=True)
    assert run_res.returncode == 0, f"Export failed: {run_res.stderr}"
    assert out_video.exists()

    # Verify output has audio stream
    assert ProbeService.has_audio(out_video) is True



