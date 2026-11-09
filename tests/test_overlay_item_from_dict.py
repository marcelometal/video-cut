"""OverlayItem.from_dict() must only build items from well-formed clipboard payloads."""

import json
from dataclasses import asdict
from pathlib import Path

from video_cut.models import OverlayItem


def _payload(item: OverlayItem) -> dict:
    data = asdict(item)
    if data.get("media_path") is not None:
        data["media_path"] = str(data["media_path"])
    return json.loads(json.dumps(data))


def test_round_trip_keeps_every_field_but_the_id() -> None:
    original = OverlayItem(item_type="image", media_path="/media/clip.png", x=0.2, y=0.7, text="hi", bold=True)

    rebuilt = OverlayItem.from_dict(_payload(original))

    assert rebuilt is not None
    assert rebuilt.id != original.id
    assert rebuilt.media_path == Path("/media/clip.png")
    expected = {k: v for k, v in asdict(original).items() if k != "id"}
    assert {k: v for k, v in asdict(rebuilt).items() if k != "id"} == expected


def test_id_from_the_payload_is_never_reused() -> None:
    rebuilt = OverlayItem.from_dict({"id": "fixed", "item_type": "text", "text": "a"})

    assert rebuilt is not None
    assert rebuilt.id != "fixed"


def test_unknown_keys_are_dropped() -> None:
    rebuilt = OverlayItem.from_dict({"item_type": "text", "text": "a", "__class__": "x", "callback": 1})

    assert rebuilt is not None
    assert rebuilt.text == "a"


def test_wrong_types_reject_the_item() -> None:
    assert OverlayItem.from_dict({"item_type": "text", "x": "0.5"}) is None
    assert OverlayItem.from_dict({"item_type": "text", "font_size": 1.5}) is None
    assert OverlayItem.from_dict({"item_type": "text", "bold": 1}) is None
    assert OverlayItem.from_dict({"item_type": "text", "x": float("nan")}) is None
    assert OverlayItem.from_dict({"item_type": "text", "end_time": "3"}) is None
    assert OverlayItem.from_dict({"item_type": "text", "media_path": {"path": "x"}}) is None


def test_optional_fields_accept_none() -> None:
    rebuilt = OverlayItem.from_dict({"item_type": "text", "bg_color": None, "end_time": None, "audio_end": None})

    assert rebuilt is not None
    assert rebuilt.bg_color is None and rebuilt.end_time is None


def test_unknown_item_type_and_non_mappings_are_rejected() -> None:
    assert OverlayItem.from_dict({"item_type": "script"}) is None
    assert OverlayItem.from_dict(["item_type", "text"]) is None
    assert OverlayItem.from_dict("text") is None
    assert OverlayItem.from_dict(None) is None
