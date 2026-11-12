"""Tests for capcut_draft_installer.

The module under test lives at the repository root (it is not an installed
package), so it is imported by file path with importlib.
"""

import importlib.util
import json
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parent.parent / "capcut_draft_installer.py"
spec = importlib.util.spec_from_file_location("capcut_draft_installer", MODULE_PATH)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


def make_source_draft(tmp_path: Path) -> Path:
    """Create a fake source draft folder with placeholder media paths."""
    source = tmp_path / "SharedDraft"
    (source / "images").mkdir(parents=True)
    (source / "images" / "scene1.png").write_bytes(b"fake-png")
    draft = {
        "name": "SharedDraft",
        "materials": {
            "videos": [{"path": "__MEDIA__/videos/intro.mp4"}],
            "images": [{"path": "__MEDIA__/images/scene1.png"}],
        },
        "tracks": [
            {"segments": [{"material": "__MEDIA__/audio/voice.mp3", "volume": 1.0}]}
        ],
        "duration": 42,
    }
    (source / "draft_content.json").write_text(
        json.dumps(draft, indent=2), encoding="utf-8"
    )
    return source


def test_install_copies_draft_and_rewrites_placeholders(tmp_path):
    source = make_source_draft(tmp_path)
    drafts_dir = tmp_path / "com.lveditor.draft"
    media_dir = tmp_path / "media"
    media_dir.mkdir()

    destination = installer.install_draft(
        source=source, drafts_dir=drafts_dir, media_dir=media_dir
    )

    assert destination == drafts_dir / "SharedDraft"
    assert (destination / "draft_content.json").is_file()
    assert (destination / "images" / "scene1.png").is_file()

    installed = json.loads((destination / "draft_content.json").read_text(encoding="utf-8"))
    media_prefix = str(media_dir.resolve()).replace("\\", "/") + "/"
    assert installed["materials"]["videos"][0]["path"] == media_prefix + "videos/intro.mp4"
    assert installed["materials"]["images"][0]["path"] == media_prefix + "images/scene1.png"
    assert installed["tracks"][0]["segments"][0]["material"] == media_prefix + "audio/voice.mp3"
    # Non-string values are untouched.
    assert installed["duration"] == 42
    assert "__MEDIA__" not in json.dumps(installed)


def test_source_json_is_never_modified(tmp_path):
    source = make_source_draft(tmp_path)
    original_text = (source / "draft_content.json").read_text(encoding="utf-8")

    installer.install_draft(source=source, drafts_dir=tmp_path / "drafts")

    assert (source / "draft_content.json").read_text(encoding="utf-8") == original_text
    assert "__MEDIA__/" in original_text


def test_media_dir_defaults_to_source_folder(tmp_path):
    source = make_source_draft(tmp_path)

    destination = installer.install_draft(
        source=source, drafts_dir=tmp_path / "drafts"
    )

    installed = json.loads((destination / "draft_content.json").read_text(encoding="utf-8"))
    media_prefix = str(source.resolve()).replace("\\", "/") + "/"
    assert installed["materials"]["images"][0]["path"] == media_prefix + "images/scene1.png"


def test_overwrite_is_refused_without_force(tmp_path):
    source = make_source_draft(tmp_path)
    drafts_dir = tmp_path / "drafts"

    installer.install_draft(source=source, drafts_dir=drafts_dir)

    with pytest.raises(installer.InstallerError):
        installer.install_draft(source=source, drafts_dir=drafts_dir)

    # With force=True the same call succeeds.
    destination = installer.install_draft(
        source=source, drafts_dir=drafts_dir, force=True
    )
    assert (destination / "draft_content.json").is_file()


def test_missing_draft_content_json_is_an_error(tmp_path):
    empty = tmp_path / "NotADraft"
    empty.mkdir()

    with pytest.raises(installer.InstallerError):
        installer.install_draft(source=empty, drafts_dir=tmp_path / "drafts")


def test_dry_run_copies_nothing(tmp_path):
    source = make_source_draft(tmp_path)
    drafts_dir = tmp_path / "drafts"

    destination = installer.install_draft(
        source=source, drafts_dir=drafts_dir, dry_run=True
    )

    assert destination == drafts_dir / "SharedDraft"
    assert not destination.exists()
    assert not drafts_dir.exists()


def test_rewrite_placeholders_recursion():
    data = {
        "a": "__MEDIA__/x.png",
        "b": ["keep", {"c": "__MEDIA__/y.png __MEDIA__/z.png"}],
        "n": 7,
        "flag": True,
        "none": None,
    }
    out = installer.rewrite_placeholders(data, "C:/media/")
    assert out["a"] == "C:/media/x.png"
    assert out["b"][1]["c"] == "C:/media/y.png C:/media/z.png"
    assert out["n"] == 7 and out["flag"] is True and out["none"] is None
    assert installer.count_placeholders(data) == 3


def test_cli_main_dry_run(tmp_path, capsys):
    source = make_source_draft(tmp_path)
    drafts_dir = tmp_path / "drafts"

    exit_code = installer.main(
        ["--source", str(source), "--drafts-dir", str(drafts_dir), "--dry-run"]
    )

    assert exit_code == 0
    assert not (drafts_dir / "SharedDraft").exists()
    assert "dry-run" in capsys.readouterr().out.lower()
