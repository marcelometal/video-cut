"""Centralized service for interacting with the FFmpeg multimedia binary."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from ..utils import SUBPROCESS_FLAGS, get_ffmpeg_path

# Standard FFmpeg CLI Flags and Options
FLAG_OVERWRITE = "-y"
FLAG_NO_STDIN = "-nostdin"
FLAG_SEEK = "-ss"
FLAG_INPUT = "-i"
FLAG_DURATION = "-t"
FLAG_FORMAT = "-f"
FLAG_CODEC_VIDEO = "-c:v"
FLAG_CODEC_AUDIO = "-c:a"
FLAG_NO_AUDIO = "-an"
FLAG_NO_VIDEO = "-vn"
FLAG_FILTER_VIDEO = "-vf"
FLAG_FILTER_COMPLEX = "-filter_complex"
FLAG_MAP = "-map"
FLAG_AUDIO_BITRATE = "-b:a"
FLAG_AUDIO_CHANNELS = "-ac"
FLAG_AUDIO_SAMPLE_RATE = "-ar"
FLAG_LOOP = "-loop"
FLAG_SHORTEST = "-shortest"
FLAG_CRF = "-crf"
FLAG_PRESET = "-preset"
FLAG_PIX_FMT = "-pix_fmt"
FLAG_FRAMES_VIDEO = "-frames:v"
FLAG_FPS = "-r"
FLAG_FRAMERATE = "-framerate"
FLAG_NO_SUBTITLES = "-sn"
FLAG_NO_DATA = "-dn"
FLAG_QUALITY_VIDEO = "-q:v"
FLAG_AUDIO_FILTER = "-af"
FLAG_SKIP_FRAME = "-skip_frame"
FLAG_PROGRESS = "-progress"
FLAG_VIDEO_BITRATE = "-b:v"
FLAG_VIDEO_TAG = "-tag:v"
FLAG_ENCODERS = "-encoders"
FLAG_MUXERS = "-muxers"


class FFmpegService:
    """Service wrapping ffmpeg CLI execution with structured parameters and error handling."""

    @staticmethod
    def get_binary_path() -> str:
        """Return the absolute path or command name for the ffmpeg executable."""
        return get_ffmpeg_path()

    @classmethod
    def extract_frame_to_bytes(
        cls,
        video_path: Path,
        timestamp: float,
        width: int | None = None,
        height: int | None = None,
        image_format: str = "png",
    ) -> bytes | None:
        """Extract a single frame from a video file at a given timestamp into raw image bytes."""
        cmd = [
            cls.get_binary_path(),
            FLAG_OVERWRITE,
            FLAG_NO_STDIN,
            FLAG_SEEK,
            str(max(0.0, timestamp)),
            FLAG_INPUT,
            str(video_path),
            FLAG_FRAMES_VIDEO,
            "1",
        ]

        if width is not None and height is not None:
            cmd.extend([FLAG_FILTER_VIDEO, f"scale={width}:{height}"])

        cmd.extend([
            FLAG_FORMAT,
            "image2",
            FLAG_CODEC_VIDEO,
            image_format,
            "pipe:1",
        ])

        try:
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                creationflags=SUBPROCESS_FLAGS,
            )
            return res.stdout if res.stdout else None
        except Exception:
            return None

    @classmethod
    def extract_frame_to_file(
        cls,
        video_path: Path,
        timestamp: float,
        output_path: Path,
        width: int | None = None,
        height: int | None = None,
    ) -> bool:
        """Extract a single frame from a video file at timestamp and write to output_path."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            cls.get_binary_path(),
            FLAG_OVERWRITE,
            FLAG_NO_STDIN,
            FLAG_SEEK,
            str(max(0.0, timestamp)),
            FLAG_INPUT,
            str(video_path),
            FLAG_FRAMES_VIDEO,
            "1",
        ]

        if width is not None and height is not None:
            cmd.extend([FLAG_FILTER_VIDEO, f"scale={width}:{height}"])

        cmd.append(str(output_path))

        try:
            subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                creationflags=SUBPROCESS_FLAGS,
            )
            return output_path.exists()
        except Exception:
            return False

    @classmethod
    def create_solid_color_image(
        cls,
        output_path: Path,
        color: str,
        width: int,
        height: int,
        duration: float = 1.0,
        fps: int = 30,
    ) -> None:
        """Generate a solid color test image using the lavfi color source."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            cls.get_binary_path(),
            FLAG_OVERWRITE,
            FLAG_NO_STDIN,
            FLAG_FORMAT,
            "lavfi",
            FLAG_INPUT,
            f"color=c={color}:s={width}x{height}:d={duration}:r={fps}",
            FLAG_FRAMES_VIDEO,
            "1",
            str(output_path),
        ]
        subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            creationflags=SUBPROCESS_FLAGS,
        )

    @classmethod
    def create_video_from_image(
        cls,
        image_path: Path,
        output_path: Path,
        duration: float,
        fps: int = 30,
        audio_path: Path | None = None,
        audio_start: float = 0.0,
    ) -> None:
        """Create a video clip by looping an image with optional synchronized audio."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            cls.get_binary_path(),
            FLAG_OVERWRITE,
            FLAG_NO_STDIN,
            FLAG_LOOP,
            "1",
            FLAG_DURATION,
            str(duration),
            FLAG_INPUT,
            str(image_path),
        ]

        if audio_path and audio_path.exists():
            cmd.extend([
                FLAG_SEEK,
                str(max(0.0, audio_start)),
                FLAG_INPUT,
                str(audio_path),
                FLAG_CODEC_VIDEO,
                "libx264",
                FLAG_PIX_FMT,
                "yuv420p",
                FLAG_FPS,
                str(fps),
                FLAG_CODEC_AUDIO,
                "aac",
                FLAG_AUDIO_BITRATE,
                "192k",
                FLAG_DURATION,
                str(duration),
                FLAG_SHORTEST,
            ])
        else:
            cmd.extend([
                FLAG_CODEC_VIDEO,
                "libx264",
                FLAG_PIX_FMT,
                "yuv420p",
                FLAG_FPS,
                str(fps),
                FLAG_DURATION,
                str(duration),
                FLAG_NO_AUDIO,
            ])

        cmd.append(str(output_path))
        subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            creationflags=SUBPROCESS_FLAGS,
        )

    @classmethod
    def query_available_encoders(cls) -> set[str]:
        """Query FFmpeg binary for supported encoder identifiers."""
        encoders: set[str] = set()
        try:
            res = subprocess.run(
                [cls.get_binary_path(), FLAG_ENCODERS],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
                creationflags=SUBPROCESS_FLAGS,
            )
            for line in res.stdout.splitlines():
                line = line.strip()
                if line.startswith("V") or line.startswith("A"):
                    parts = line.split()
                    if len(parts) >= 2:
                        encoders.add(parts[1])
        except Exception:
            pass
        return encoders

    @classmethod
    def query_available_muxers(cls) -> set[str]:
        """Query FFmpeg binary for supported muxer format identifiers."""
        muxers: set[str] = set()
        try:
            res = subprocess.run(
                [cls.get_binary_path(), FLAG_MUXERS],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
                creationflags=SUBPROCESS_FLAGS,
            )
            for line in res.stdout.splitlines():
                line = line.strip()
                if line.startswith("E") or line.startswith("DE"):
                    parts = line.split()
                    if len(parts) >= 2:
                        names = parts[1].split(",")
                        for n in names:
                            muxers.add(n.strip())
        except Exception:
            pass
        return muxers
