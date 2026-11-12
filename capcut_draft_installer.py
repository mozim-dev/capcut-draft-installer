#!/usr/bin/env python3
"""CapCut Draft Installer.

A small command-line tool that installs a CapCut draft folder (shared by a
collaborator as a plain folder) into CapCut Desktop's local projects folder
on Windows, rewriting placeholder media paths in ``draft_content.json`` so
CapCut can find the media files on this machine.

Placeholder convention
-----------------------
Drafts are shared with media paths written as ``__MEDIA__/relative/path``.
During installation every occurrence of the literal ``__MEDIA__/`` inside
string values of ``draft_content.json`` is replaced with the absolute path
of the media directory (using forward slashes), but only in the *copied*
draft. The source folder is never modified.

Requires Python 3.10+. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

PLACEHOLDER = "__MEDIA__/"
DRAFT_JSON_NAME = "draft_content.json"


class InstallerError(Exception):
    """Raised for expected, user-facing installation errors."""


def default_drafts_dir() -> Path | None:
    """Return CapCut Desktop's local projects folder, if it can be found.

    On Windows this is::

        %LOCALAPPDATA%/CapCut/User Data/Projects/com.lveditor.draft

    Returns ``None`` when the folder cannot be located (for example when
    not running on Windows, ``LOCALAPPDATA`` is unset, or CapCut Desktop
    has never created its projects folder).
    """
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        return None
    candidate = (
        Path(local_app_data) / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
    )
    return candidate if candidate.is_dir() else None


def rewrite_placeholders(value, media_prefix: str):
    """Return a copy of *value* with ``__MEDIA__/`` replaced in all strings.

    Works recursively over the JSON data model: dicts, lists, strings and
    scalar values. Only string values (and string dict keys are left alone)
    are changed; other types are returned unchanged.
    """
    if isinstance(value, str):
        return value.replace(PLACEHOLDER, media_prefix)
    if isinstance(value, list):
        return [rewrite_placeholders(item, media_prefix) for item in value]
    if isinstance(value, dict):
        return {key: rewrite_placeholders(item, media_prefix) for key, item in value.items()}
    return value


def count_placeholders(value) -> int:
    """Count how many ``__MEDIA__/`` placeholders occur in string values."""
    if isinstance(value, str):
        return value.count(PLACEHOLDER)
    if isinstance(value, list):
        return sum(count_placeholders(item) for item in value)
    if isinstance(value, dict):
        return sum(count_placeholders(item) for item in value.values())
    return 0


def load_draft_json(source: Path) -> object:
    """Load and return the parsed ``draft_content.json`` inside *source*.

    Raises :class:`InstallerError` if the file is missing or invalid JSON.
    """
    draft_json = source / DRAFT_JSON_NAME
    if not draft_json.is_file():
        raise InstallerError(
            f"Source folder does not contain {DRAFT_JSON_NAME}: {source}"
        )
    try:
        return json.loads(draft_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InstallerError(f"{draft_json} is not valid JSON: {exc}") from exc


def install_draft(
    source: Path,
    drafts_dir: Path,
    media_dir: Path | None = None,
    dry_run: bool = False,
    force: bool = False,
) -> Path:
    """Install the draft at *source* into *drafts_dir*.

    Parameters
    ----------
    source:
        Folder containing the draft to install (must contain
        ``draft_content.json``).
    drafts_dir:
        CapCut's local projects folder. Created if it does not exist
        (unless ``dry_run`` is set).
    media_dir:
        Folder the ``__MEDIA__/`` placeholders should point at. Defaults
        to *source* itself.
    dry_run:
        When true, validate and report what would happen without copying
        or writing anything.
    force:
        When true, an existing draft with the same folder name in
        *drafts_dir* is replaced. Otherwise its presence is an error.

    Returns the destination path of the installed draft.
    """
    source = Path(source)
    drafts_dir = Path(drafts_dir)
    if not source.is_dir():
        raise InstallerError(f"Source folder not found: {source}")

    data = load_draft_json(source)

    media_dir = Path(media_dir) if media_dir is not None else source
    media_prefix = str(media_dir.resolve()).replace(os.sep, "/") + "/"
    replacements = count_placeholders(data)

    destination = drafts_dir / source.resolve().name
    if destination.exists() and not force:
        raise InstallerError(
            f"A draft named '{destination.name}' already exists in {drafts_dir}. "
            "Refusing to overwrite it (use --force to replace it)."
        )

    if dry_run:
        print(f"[dry-run] Would copy: {source} -> {destination}")
        print(f"[dry-run] Would rewrite {replacements} '{PLACEHOLDER}' "
              f"placeholder(s) to '{media_prefix}' in the copied {DRAFT_JSON_NAME}.")
        return destination

    drafts_dir.mkdir(parents=True, exist_ok=True)
    if destination.exists():  # force=True case
        shutil.rmtree(destination)
    shutil.copytree(source, destination)

    rewritten = rewrite_placeholders(data, media_prefix)
    (destination / DRAFT_JSON_NAME).write_text(
        json.dumps(rewritten, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Installed draft: {destination}")
    print(f"Media path set to: {media_prefix}")
    print(f"Placeholders rewritten: {replacements}")
    return destination


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Install a shared CapCut draft folder into CapCut Desktop's "
            "local projects folder, rewriting __MEDIA__/ placeholder paths "
            "in draft_content.json to point at the media on this machine."
        )
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Path to the draft folder to install (must contain draft_content.json).",
    )
    parser.add_argument(
        "--drafts-dir",
        default=None,
        help=(
            "CapCut local projects folder. Default: auto-detect "
            r"%LOCALAPPDATA%/CapCut/User Data/Projects/com.lveditor.draft on Windows."
        ),
    )
    parser.add_argument(
        "--media-dir",
        default=None,
        help="Folder containing the draft's media files. Default: the source folder.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print what would happen, without copying anything.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing draft with the same name in the drafts folder.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a process exit code."""
    args = build_parser().parse_args(argv)

    if args.drafts_dir:
        drafts_dir = Path(args.drafts_dir)
    else:
        drafts_dir = default_drafts_dir()
        if drafts_dir is None:
            print(
                "Error: could not find CapCut Desktop's projects folder "
                r"(%LOCALAPPDATA%/CapCut/User Data/Projects/com.lveditor.draft). "
                "Is CapCut Desktop installed and has it been opened at least once? "
                "You can pass the folder explicitly with --drafts-dir.",
                file=sys.stderr,
            )
            return 1

    try:
        destination = install_draft(
            source=Path(args.source),
            drafts_dir=drafts_dir,
            media_dir=Path(args.media_dir) if args.media_dir else None,
            dry_run=args.dry_run,
            force=args.force,
        )
    except InstallerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"[dry-run] Nothing was copied. Destination would be: {destination}")
    else:
        print("Done. Open CapCut Desktop — the draft should appear in your projects.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
