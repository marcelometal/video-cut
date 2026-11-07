"""Unit tests for OverlayItem and Segment overlays data model."""

from pathlib import Path

from video_cut.models import OverlayItem, ProjectTimeline, Segment


def test_overlay_item_creation_and_defaults():
    item = OverlayItem()
    assert item.id is not None
    assert item.item_type == "text"
    assert item.x == 0.5
    assert item.y == 0.5
    assert item.width == 0.3
    assert item.height == 0.2
    assert item.rotation == 0.0
    assert item.opacity == 1.0


def test_overlay_item_cloning_and_copy():
    item = OverlayItem(
        item_type="rect",
        x=0.2,
        y=0.3,
        width=0.4,
        height=0.5,
        rotation=45.0,
        fill_color="#123456",
        border_color="#abcdef",
        border_width=4,
    )
    # copy maintains id
    cp = item.copy()
    assert cp.id == item.id
    assert cp.item_type == "rect"
    assert cp.fill_color == "#123456"

    # clone gives new id
    cl = item.clone()
    assert cl.id != item.id
    assert cl.item_type == "rect"
    assert cl.fill_color == "#123456"


def test_segment_overlays_and_undo():
    seg = Segment(source_path=Path("/tmp/fake.mp4"), source_duration=10.0)
    assert not seg.has_overlays

    item = OverlayItem(item_type="text", text="Hello VideoCut")
    seg.overlays.append(item)
    assert seg.has_overlays
    assert len(seg.overlays) == 1

    # Test clone
    seg_cloned = seg.clone()
    assert seg_cloned.has_overlays
    assert len(seg_cloned.overlays) == 1
    assert seg_cloned.overlays[0].id != item.id
    assert seg_cloned.overlays[0].text == "Hello VideoCut"

    # Test copy
    seg_copy = seg.copy()
    assert seg_copy.overlays[0].id == item.id

    # Test timeline snapshot & undo
    timeline = ProjectTimeline()
    seg1 = timeline.add_video(Path("/tmp/fake.mp4"), 10.0)
    timeline.save_state(0.0)
    seg1.overlays.append(item)
    assert seg1.has_overlays

    # Undo restores state without overlay
    assert timeline.can_undo
    timeline.undo(0.0)
    assert not timeline.segments[0].has_overlays
