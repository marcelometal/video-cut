"""Service for managing synchronized playback of overlay audio tracks and video audio in real-time."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst

from ..models import OverlayItem
from ..utils import clamp
from .probe_service import ProbeService

# Initialize GStreamer once
try:
    if not Gst.is_initialized():
        Gst.init(None)
except Exception:
    pass


class GstAudioTrack:
    """Wrapper around a GStreamer playbin pipeline dedicated to audio playback."""

    def __init__(self, media_path: Path | str) -> None:
        self.media_path = str(media_path)
        self.uri = Path(media_path).resolve().as_uri()
        self._element = Gst.ElementFactory.make("playbin", None)
        if self._element:
            self._element.set_property("uri", self.uri)
            # Set video-sink to fakesink to avoid allocating any video surfaces or crashing decodebin3
            fakesink = Gst.ElementFactory.make("fakesink", None)
            self._element.set_property("video-sink", fakesink)
            # Preroll in PAUSED state
            self._element.set_state(Gst.State.PAUSED)
            # Short wait for initial preroll
            self._element.get_state(50 * Gst.MSECOND)

    def is_prepared(self) -> bool:
        if not self._element:
            return False
        ret, state, pending = self._element.get_state(0)
        return (
            state in (Gst.State.PAUSED, Gst.State.PLAYING)
            or pending in (Gst.State.PAUSED, Gst.State.PLAYING)
        )

    def play(self) -> None:
        if self._element:
            self._element.set_state(Gst.State.PLAYING)

    def pause(self) -> None:
        if self._element:
            self._element.set_state(Gst.State.PAUSED)

    def get_playing(self) -> bool:
        if not self._element:
            return False
        ret, state, _ = self._element.get_state(0)
        return state == Gst.State.PLAYING

    def seek(self, pos_s: float) -> bool:
        if not self._element:
            return False
        ret, state, _ = self._element.get_state(0)
        if state not in (Gst.State.PAUSED, Gst.State.PLAYING):
            return False
        flags = Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE
        return bool(self._element.seek_simple(Gst.Format.TIME, flags, int(pos_s * 1_000_000_000)))

    def get_timestamp(self) -> float:
        """Return position in seconds."""
        if not self._element:
            return 0.0
        success, pos = self._element.query_position(Gst.Format.TIME)
        return pos / 1_000_000_000.0 if success else 0.0

    def get_duration(self) -> float:
        """Return duration in seconds."""
        if not self._element:
            return 0.0
        success, dur = self._element.query_duration(Gst.Format.TIME)
        return dur / 1_000_000_000.0 if success else 0.0

    def set_volume(self, vol: float) -> None:
        if self._element:
            self._element.set_property("volume", max(0.0, float(vol)))

    def get_volume(self) -> float:
        if self._element:
            return float(self._element.get_property("volume"))
        return 1.0

    def set_muted(self, muted: bool) -> None:
        if self._element:
            self._element.set_property("mute", bool(muted))

    def get_property(self, prop: str) -> Any:
        if self._element:
            return self._element.get_property(prop)
        return None

    def cleanup(self) -> None:
        if self._element:
            self._element.set_state(Gst.State.NULL)
            self._element = None


class OverlayAudioPlayer:
    """Manages audio playback for video overlays with enable_audio=True and audio track elements."""

    def __init__(self) -> None:
        self._media_files: dict[str, GstAudioTrack] = {}
        self._durations: dict[str, float] = {}
        self._last_expected_pos: dict[str, float] = {}

    def sync_items(self, items: list[OverlayItem]) -> None:
        """Keep GstAudioTrack instances alive only for active audio-producing items."""
        active_ids: set[str] = set()
        for it in items:
            has_audio = (
                (it.item_type == "audio" and it.media_path and Path(it.media_path).is_file())
                or (
                    it.item_type == "video"
                    and it.enable_audio
                    and it.media_path
                    and Path(it.media_path).is_file()
                )
            )
            if has_audio:
                active_ids.add(it.id)
                if it.id not in self._media_files:
                    path_str = str(it.media_path)
                    try:
                        track = GstAudioTrack(path_str)
                        self._media_files[it.id] = track
                    except Exception:
                        continue

                    if path_str not in self._durations:
                        dur = ProbeService.probe_duration(path_str)
                        if dur is not None and dur > 0:
                            self._durations[path_str] = dur

        # Clean up removed or disabled items
        for old_id in list(self._media_files.keys()):
            if old_id not in active_ids:
                track = self._media_files.pop(old_id, None)
                if track:
                    track.cleanup()
                self._last_expected_pos.pop(old_id, None)

    def update_playback(
        self,
        items: list[OverlayItem],
        rel_time: float,
        is_playing: bool,
        master_seeking: bool = False,
    ) -> None:
        """Synchronize audio overlay playback state, timestamp, volume, and looping."""
        self.sync_items(items)

        for it in items:
            track = self._media_files.get(it.id)
            if not track or not track.is_prepared():
                continue

            path_str = str(it.media_path) if it.media_path else ""
            file_dur = self._durations.get(path_str)
            if file_dur is None or file_dur <= 0:
                dur_s = track.get_duration()
                if dur_s > 100_000:
                    dur_s = dur_s / 1_000_000.0
                file_dur = dur_s if dur_s > 0 else 3600.0
                self._durations[path_str] = file_dur

            # Check if current time falls within overlay item's lifespan
            dt = rel_time - it.start_time
            if dt < 0.0 or (it.end_time is not None and rel_time > it.end_time):
                if track.get_playing():
                    track.pause()
                continue

            # Calculate expected position in source audio
            if it.item_type == "audio":
                track_start = max(0.0, float(it.audio_start))
                track_end = float(it.audio_end) if it.audio_end is not None else file_dur
                if track_end <= track_start:
                    track_end = file_dur
                span = max(0.05, track_end - track_start)
                if it.is_loop:
                    expected_pos = track_start + (dt % span)
                else:
                    if dt > span:
                        expected_pos = None
                    else:
                        expected_pos = track_start + dt
            else:
                # Video overlay with audio
                span = max(0.05, file_dur)
                if it.is_loop:
                    expected_pos = (dt % span) if span > 0 else 0.0
                else:
                    if dt > span:
                        expected_pos = None
                    else:
                        expected_pos = dt

            if expected_pos is None:
                if track.get_playing():
                    track.pause()
                continue

            # Set volume
            vol = clamp(float(getattr(it, "audio_volume", 1.0)), 0.0, 2.0)
            track.set_muted(vol <= 0.001)
            track.set_volume(vol)

            cur_ts = track.get_timestamp()
            if cur_ts > 100_000:
                cur_ts = cur_ts / 1_000_000.0
            drift = abs(cur_ts - expected_pos)
            prev_expected = self._last_expected_pos.get(it.id, expected_pos)
            self._last_expected_pos[it.id] = expected_pos

            # Handle looping wraparound
            is_loop_wrap = expected_pos < prev_expected - 0.2

            if not is_playing or master_seeking:
                if track.get_playing():
                    track.pause()
                if drift > 0.05 or master_seeking or is_loop_wrap:
                    track.seek(expected_pos)
            else:
                # Normal playback
                if drift > 0.25 or is_loop_wrap:
                    track.seek(expected_pos)
                if not track.get_playing():
                    track.play()

    def pause_all(self) -> None:
        """Pause all active overlay audio streams."""
        for track in self._media_files.values():
            try:
                track.pause()
            except Exception:
                pass

    def cleanup(self) -> None:
        """Pause all and clear media file instances."""
        for track in self._media_files.values():
            try:
                track.cleanup()
            except Exception:
                pass
        self._media_files.clear()
        self._durations.clear()
        self._last_expected_pos.clear()
