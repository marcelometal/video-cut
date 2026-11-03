"""Tests for centralized paths and resource loading."""

from pathlib import Path

from video_cut import paths


def test_paths_constants():
    assert paths.APP_ID == "io.github.thor27.video-cut"
    assert paths.APP_NAME == "Video Cut"
    assert paths.PACKAGE_DIR.is_dir()
    assert paths.RESOURCES_DIR.is_dir()
    assert paths.STYLE_CSS_PATH.is_file()


def test_load_application_css_and_icons():
    # Should not raise exception
    paths.load_application_css()
    paths.register_resource_icons()
