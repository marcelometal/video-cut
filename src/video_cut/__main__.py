"""CLI entrypoint for Video Cut."""

import argparse
import os
import sys
from pathlib import Path


def _init_windows_environment() -> None:
    """Configure runtime environment variables for GTK 4, Libadwaita, and GStreamer on Windows."""
    if sys.platform != "win32":
        return

    if os.environ.get("GDK_BACKEND") in ("wayland", "x11", None):
        os.environ["GDK_BACKEND"] = "win32"
    if "WAYLAND_DISPLAY" in os.environ:
        del os.environ["WAYLAND_DISPLAY"]

    if getattr(sys, "frozen", False):
        base_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base_dir = Path(__file__).resolve().parent.parent.parent

    roots = [
        base_dir,
        Path(sys.prefix),
        Path(sys.executable).parent.parent,
        Path(sys.executable).parent,
    ]

    # 1. Typelibs path
    if "GI_TYPELIB_PATH" not in os.environ:
        for r in roots:
            for t_dir in [r / "lib" / "girepository-1.0", r / "girepository-1.0"]:
                if t_dir.is_dir():
                    os.environ["GI_TYPELIB_PATH"] = str(t_dir)
                    break
            if "GI_TYPELIB_PATH" in os.environ:
                break

    # 2. GLib Schemas (crucial for Adw / GTK themes & settings)
    if "GSETTINGS_SCHEMA_DIR" not in os.environ:
        for r in roots:
            for s_dir in [r / "share" / "glib-2.0" / "schemas", r / "glib-2.0" / "schemas"]:
                if s_dir.is_dir() and (s_dir / "gschemas.compiled").is_file():
                    os.environ["GSETTINGS_SCHEMA_DIR"] = str(s_dir)
                    break
            if "GSETTINGS_SCHEMA_DIR" in os.environ:
                break

    # 3. GdkPixbuf loaders
    if "GDK_PIXBUF_MODULE_FILE" not in os.environ:
        for r in roots:
            for p_cache in [
                r / "lib" / "gdk-pixbuf-2.0" / "2.10.0" / "loaders.cache",
                r / "gdk-pixbuf-2.0" / "loaders.cache",
            ]:
                if p_cache.is_file():
                    os.environ["GDK_PIXBUF_MODULE_FILE"] = str(p_cache)
                    break
            if "GDK_PIXBUF_MODULE_FILE" in os.environ:
                break

    # 4. GStreamer plugins
    if "GST_PLUGIN_PATH" not in os.environ:
        for r in roots:
            for gst_dir in [r / "lib" / "gstreamer-1.0", r / "gstreamer-1.0"]:
                if gst_dir.is_dir():
                    os.environ["GST_PLUGIN_PATH"] = str(gst_dir)
                    os.environ["GST_PLUGIN_SYSTEM_PATH"] = str(gst_dir)
                    break
            if "GST_PLUGIN_PATH" in os.environ:
                break

    # 5. GStreamer registry in user APPDATA to avoid read-only or temp collisions
    appdata = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
    registry_dir = Path(appdata) / "VideoCut"
    try:
        registry_dir.mkdir(parents=True, exist_ok=True)
        os.environ["GST_REGISTRY"] = str(registry_dir / "gstreamer_registry.bin")
    except OSError:
        pass


_init_windows_environment()

from gi.repository import GLib  # noqa: E402

try:
    from . import __version__  # noqa: E402
    from .app import VideoCutApplication  # noqa: E402
    from .paths import APP_ID, APP_NAME  # noqa: E402
except ImportError:
    from video_cut import __version__  # noqa: E402
    from video_cut.app import VideoCutApplication  # noqa: E402
    from video_cut.paths import APP_ID, APP_NAME  # noqa: E402


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="video-cut",
        description="Fast, simple video and image editor for Linux.",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="One or more video or image files to open in the timeline.",
    )
    return parser.parse_args(args)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv

    GLib.set_prgname(APP_ID)
    GLib.set_application_name(APP_NAME)

    parsed = parse_args(argv[1:])

    app = VideoCutApplication(initial_files=parsed.files)
    return app.run([argv[0]])


if __name__ == "__main__":
    sys.exit(main())

