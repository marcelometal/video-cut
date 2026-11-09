# Contributing to Video Cut

Thank you for taking the time to contribute. Video Cut is a GTK 4 and
Libadwaita desktop application written in Python and licensed under the
GPL-3.0-or-later. Bug reports, feature ideas, translations, packaging fixes
and code are all welcome.

This guide covers how to set up a development environment, run the same
checks as CI, work on translations and open a pull request. The
[README](README.md) has the user-facing documentation and, under
*Development*, an overview of the code layout.

## Reporting bugs and requesting features

Open an issue on the
[GitHub issue tracker](https://github.com/thor27/video-cut/issues). For a
bug, include:

- The Video Cut version (shown in the *About Video Cut* dialog) and how it was
  installed: Flatpak, AppImage, Debian package, Snap or from source.
- Your Linux distribution and desktop environment, and the output of
  `ffmpeg -version`.
- Steps to reproduce, what you expected and what happened instead.
- The terminal output when the problem reproduces with the app started from a
  terminal (`video-cut`, or `flatpak run io.github.thor27.video-cut`).
- If the problem depends on a specific media file, its `ffprobe` output and,
  when you can share one, a short sample that reproduces it.

**Security issues must not be reported through public issues.** Follow
[SECURITY.md](SECURITY.md) instead.

For a new feature or a larger change, open an issue first to discuss the
approach before investing time in an implementation.

## Development setup

### System packages

Video Cut uses the system GTK 4, Libadwaita and GStreamer bindings through
PyGObject, so those come from the distribution, not from pip. `ffmpeg` and
`ffprobe` are called as external programs. The last line of each command
installs the tools used by the checks described below: Xvfb for headless
tests, the desktop metadata validators and gettext for translations.

Debian / Ubuntu:

```bash
sudo apt install python3-venv python3-gi python3-cairo python3-pil \
    gir1.2-gtk-4.0 gir1.2-adw-1 gir1.2-gstreamer-1.0 gstreamer1.0-gtk4 \
    gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-libav \
    ffmpeg \
    xvfb appstream desktop-file-utils gettext
```

Fedora:

```bash
sudo dnf install python3-gobject python3-cairo python3-pillow \
    gtk4 libadwaita gstreamer1 gstreamer1-plugin-gtk4 \
    gstreamer1-plugins-base gstreamer1-plugins-good gstreamer1-plugin-libav \
    ffmpeg \
    xorg-x11-server-Xvfb appstream desktop-file-utils gettext
```

The `ffmpeg` package above comes from [RPM Fusion](https://rpmfusion.org/),
which must be enabled first (see its
[multimedia guide](https://rpmfusion.org/Howto/Multimedia)). Fedora's own
`ffmpeg-free` is built without the `libx264` encoder, and the test suite
encodes its sample clips with it.

Arch Linux:

```bash
sudo pacman -S --needed python python-gobject python-cairo python-pillow \
    gtk4 libadwaita gstreamer gst-plugin-gtk4 \
    gst-plugins-base gst-plugins-good gst-libav \
    ffmpeg \
    xorg-server-xvfb appstream desktop-file-utils gettext
```

Optional: NumPy (`python3-numpy` on Debian, Ubuntu and Fedora, `python-numpy`
on Arch) speeds up the crop and rotate preview. Without it the app falls back
to a slower PNG conversion.

### Python environment

Python 3.10 or newer is required.

```bash
git clone https://github.com/thor27/video-cut.git
cd video-cut
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -e ".[dev]"
video-cut
```

`--system-site-packages` lets the virtual environment see the PyGObject,
cairo and Pillow packages installed by the distribution. The `dev` extra adds
`pytest`, `pytest-benchmark` and `ruff`.

To try the UI in another language, set `LANGUAGE`, for example
`LANGUAGE=pt_BR video-cut`.

## Running the checks

CI (`.github/workflows/ci.yml`) runs the following on every pull request.
Run them locally before pushing, with the virtual environment active:

```bash
ruff check .
desktop-file-validate src/video_cut/resources/io.github.thor27.video-cut.desktop
appstreamcli validate --no-net io.github.thor27.video-cut.metainfo.xml
xvfb-run -a python -m pytest -q
```

Notes on the test suite:

- It is self-contained. The clips the tests need are generated on the fly by
  `ffmpeg` from the `sample_video` and `sample_video2` fixtures in
  `tests/conftest.py` (a synthetic test pattern with a sine tone), so there
  are no media files in the repository.
- Many tests build real GTK widgets. On a desktop session you can run
  `pytest` directly; on a server or in CI, run it under `xvfb-run`.
  `tests/conftest.py` sets `GSK_RENDERER=cairo` because GTK's GL renderer
  aborts on displays without GL, such as Xvfb.
- `tests/test_benchmarks.py` uses `pytest-benchmark` and is skipped when the
  plugin is not installed. Pass `--benchmark-skip` to leave the benchmarks
  out of a run, or `--benchmark-only` to run only them.
- The whole suite takes about half a minute. To iterate on one area, pass
  the file: `pytest tests/test_export_service.py -q`.

## Coding guidelines

- Target Python 3.10 (`requires-python` in `pyproject.toml`). Ruff's
  `pyupgrade` rules are enabled, so use modern syntax such as `X | None`.
- `ruff check .` must pass. The rule set and the 100-column line length are
  configured in `pyproject.toml`. Ruff's formatter is not enforced, so do not
  reformat files you are not otherwise changing; keep the diff focused on
  the change.
- Call `gi.require_version(...)` before importing from `gi.repository`, as
  the existing modules do. This is why `E402` is disabled.
- Every user-visible string goes through `_()` from `video_cut.i18n`
  (`from .i18n import _`) so it can be translated. Update the translation
  template afterwards (see below).
- Resolve the `ffmpeg` and `ffprobe` binaries with `get_ffmpeg_path()` and
  `get_ffprobe_path()` from `video_cut.utils` instead of hard-coding the
  names, and pass `SUBPROCESS_FLAGS` from the same module to `subprocess`.
- `models.py` has no GObject dependencies, and `services/` uses only GLib,
  GdkPixbuf, Gdk textures and GStreamer, never widgets. That keeps them
  testable without a window; keep it that way and put UI code in the widget
  and dialog modules.
- Add or update tests under `tests/` for behaviour changes. Pure logic tests
  (models, export filter graph, probing) need no display; for widget tests,
  follow the pattern in `tests/test_ui_smoke.py`, which drives a real
  `MainWindow` inside an `Adw.Application`.

## Translations

Video Cut uses gettext. The template and the catalogs live under
`src/video_cut/locale/`:

| Path | Purpose |
| :--- | :--- |
| `video-cut.pot` | Template extracted from the sources |
| `<lang>/LC_MESSAGES/video-cut.po` | Editable catalog for one language |
| `<lang>/LC_MESSAGES/video-cut.mo` | Compiled catalog loaded at runtime |

The supported languages are listed in `SUPPORTED_LOCALES` in
`src/video_cut/i18n.py`: `en_US`, `es`, `fr` and `pt_BR`.

After adding or changing strings in the source:

```bash
# 1. Regenerate the template from the sources
xgettext --from-code=UTF-8 --language=Python \
    --keyword=_ --keyword=ngettext:1,2 --package-name=video-cut \
    --output=src/video_cut/locale/video-cut.pot \
    $(find src/video_cut -name '*.py' | sort)

# 2. Merge the new strings into every catalog
for po in src/video_cut/locale/*/LC_MESSAGES/video-cut.po; do
    msgmerge --quiet --update --backup=none "$po" \
        src/video_cut/locale/video-cut.pot
done

# 3. Translate the new and fuzzy entries (Poedit, Gtranslator or a text editor)

# 4. Compile and check each catalog
for po in src/video_cut/locale/*/LC_MESSAGES/video-cut.po; do
    msgfmt --check --statistics -o "${po%.po}.mo" "$po"
done
```

Commit the `.pot`, `.po` and `.mo` files together. The compiled `.mo` files
are shipped as package data (see `pyproject.toml` and `MANIFEST.in`); nothing
compiles them at build time.

To add a language:

1. Create the directory and the catalog from the template, for example for
   German:
   `msginit --no-translator --locale=de --input=src/video_cut/locale/video-cut.pot --output-file=src/video_cut/locale/de/LC_MESSAGES/video-cut.po`
   (`--no-translator` skips the interactive e-mail prompt).
2. Add the code to `SUPPORTED_LOCALES` and to `_normalize_lang()` in
   `src/video_cut/i18n.py`.
3. Add a test alongside the per-language tests in `tests/test_i18n.py`.
4. Update the language list in the README *Features* section.

## Packaging

The README *Packaging & Distribution* section covers the build scripts under
`scripts/`, and [FLATHUB_PUBLISHING.md](FLATHUB_PUBLISHING.md) covers the
Flathub submission. When a change adds or removes a runtime dependency,
update every place that lists them: `pyproject.toml`, the `Depends` line in
`scripts/build_deb.sh`, `snap/snapcraft.yaml`, the Flatpak manifest
`io.github.thor27.video-cut.yaml`, `scripts/build_appimage.sh` with the
`packaging/appimage/requirements-*.txt` files, and the package lists in the
README and in this file.

`io.github.thor27.video-cut.metainfo.xml` in the repository root and its copy
in `src/video_cut/resources/` must stay identical.

Do not bump the version or edit `CHANGELOG.md` in a feature or fix pull
request. The maintainer does both at release time with
`scripts/set_version.sh`, which updates `src/video_cut/__init__.py`, the
single source of truth that the Python package, the AppStream metadata and
the packaging scripts read the version from.

## Commits and pull requests

- Branch off `main` and open the pull request against `main`.
- Commit messages follow
  [Conventional Commits](https://www.conventionalcommits.org/):
  `type(scope): summary`, in lowercase and the imperative mood. The types in
  use are `feat`, `fix`, `docs`, `build`, `ci`, `perf`, `refactor`, `test`
  and `chore`; the scope is optional, for example `fix(export): ...` or
  `build(flatpak): ...`.
- Keep a pull request to one logical change, and explain in the description
  what was wrong and why the change is the right fix.
- Run the checks above before pushing. CI runs them again on every pull
  request and must be green before merging.
- For user interface changes, add a screenshot or a short recording to the
  pull request.

## License

By contributing you agree that your contributions are licensed under the GNU
General Public License v3.0 or later, the same license as the project. See
[LICENSE](LICENSE).
