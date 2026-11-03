"""Tests for centralized FFmpegService and flag constants."""

import tempfile
from pathlib import Path

from video_cut.services.ffmpeg_service import (
    FLAG_AUDIO_BITRATE,
    FLAG_CODEC_AUDIO,
    FLAG_CODEC_VIDEO,
    FLAG_CRF,
    FLAG_DURATION,
    FLAG_FILTER_COMPLEX,
    FLAG_FILTER_VIDEO,
    FLAG_INPUT,
    FLAG_MAP,
    FLAG_NO_AUDIO,
    FLAG_OVERWRITE,
    FLAG_PRESET,
    FLAG_SEEK,
    FFmpegService,
)


def test_ffmpeg_constants_values():
    assert FLAG_OVERWRITE == "-y"
    assert FLAG_SEEK == "-ss"
    assert FLAG_INPUT == "-i"
    assert FLAG_DURATION == "-t"
    assert FLAG_NO_AUDIO == "-an"
    assert FLAG_CODEC_VIDEO == "-c:v"
    assert FLAG_CODEC_AUDIO == "-c:a"
    assert FLAG_FILTER_VIDEO == "-vf"
    assert FLAG_FILTER_COMPLEX == "-filter_complex"
    assert FLAG_MAP == "-map"
    assert FLAG_AUDIO_BITRATE == "-b:a"
    assert FLAG_CRF == "-crf"
    assert FLAG_PRESET == "-preset"


def test_ffmpeg_service_query_capabilities():
    encoders = FFmpegService.query_available_encoders()
    assert isinstance(encoders, set)
    assert len(encoders) > 0
    assert "libx264" in encoders

    muxers = FFmpegService.query_available_muxers()
    assert isinstance(muxers, set)
    assert len(muxers) > 0
    assert "mp4" in muxers


def test_ffmpeg_service_create_solid_color_image():
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_p = Path(tmp_dir) / "test_color.png"
        FFmpegService.create_solid_color_image(
            output_path=out_p,
            color="red",
            width=320,
            height=240,
            duration=1.0,
        )
        assert out_p.exists()
        assert out_p.stat().st_size > 0
