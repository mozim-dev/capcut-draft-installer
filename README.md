# CapCut Draft Installer

A small command-line tool that installs a CapCut draft folder into CapCut
Desktop's local projects folder on Windows, and rewrites placeholder media
paths in the draft's `draft_content.json` so CapCut can find the media files
on the machine where the draft is being installed.

## Why this exists

When people collaborate on a CapCut video, one person often builds an
editable draft and shares it with another person, who opens it in their own
CapCut Desktop to make changes. A draft contains a `draft_content.json` file
with paths to its images, video clips and audio. Those paths point at the
first person's computer, so on the second person's computer CapCut cannot
find the media.

This tool covers the manual steps of that hand-over:

1. Copy the draft folder into CapCut Desktop's local projects folder
   (`%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft`), where
   CapCut expects to find its drafts.
2. Rewrite the media paths inside the copied draft so they point at the
   media folder on this machine.

## Requirements

- Windows, with CapCut Desktop installed (and opened at least once, so its
  projects folder exists)
- Python 3.10 or newer (standard library only — nothing to pip install)
- A draft folder that contains a `draft_content.json` file

## The `__MEDIA__/` placeholder convention

Drafts shared for installation write their media paths with a placeholder
prefix instead of an absolute path:

```
__MEDIA__/images/scene1.png
__MEDIA__/audio/voice.mp3
```

At install time, every occurrence of the literal `__MEDIA__/` in string
values of `draft_content.json` is replaced with the absolute path of the
media directory, using forward slashes, for example:

```
C:/Users/Name/Videos/MyDraft/images/scene1.png
```

The rewrite happens **only in the copied draft** inside CapCut's projects
folder. The shared source folder is never modified.

## Usage

Basic install — CapCut's projects folder is auto-detected, and the media
is assumed to be inside the draft folder itself:

```bat
python capcut_draft_installer.py --source C:\Shared\MyDraft
```

Install with the media in a separate folder:

```bat
python capcut_draft_installer.py --source C:\Shared\MyDraft --media-dir D:\Media\MyDraft
```

Install into a specific projects folder (useful if auto-detection fails):

```bat
python capcut_draft_installer.py --source C:\Shared\MyDraft --drafts-dir "D:\CapCut\User Data\Projects\com.lveditor.draft"
```

See what would happen without copying anything:

```bat
python capcut_draft_installer.py --source C:\Shared\MyDraft --dry-run
```

If a draft with the same folder name is already installed, the tool refuses
to overwrite it. To replace it:

```bat
python capcut_draft_installer.py --source C:\Shared\MyDraft --force
```

After a successful install, open CapCut Desktop — the draft appears in the
project list with its media linked.

## Options

| Option | Description |
| --- | --- |
| `--source` | Draft folder to install (required). Must contain `draft_content.json`. |
| `--drafts-dir` | CapCut local projects folder. Default: auto-detected on Windows. |
| `--media-dir` | Folder the `__MEDIA__/` placeholders should point at. Default: the source folder. |
| `--dry-run` | Validate and print what would happen, without copying anything. |
| `--force` | Replace an existing draft with the same name. |

## Running the tests

```bat
python -m pytest tests/ -q
```

The tests build a fake draft in a temporary folder and check that the draft
is copied, placeholders are rewritten, the source is left unchanged, and
overwriting is refused without `--force`.

## Roadmap

Ideas for later versions, in no particular order:

- Accept a `.zip` file as input and unpack it automatically
- macOS support (CapCut Desktop's projects folder location differs)
- A check that reports media files referenced by the draft but missing
  from the media folder

## License

MIT License — see [LICENSE](LICENSE). Copyright (c) 2026 Mozim.
