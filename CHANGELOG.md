# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] - 2026-11-12

### Added

- Initial release of the CapCut Draft Installer command-line tool.
- Installs a draft folder into CapCut Desktop's local projects folder on
  Windows, with auto-detection of
  `%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft`.
- Rewrites `__MEDIA__/` placeholder paths in the copied draft's
  `draft_content.json` to the absolute media path (forward slashes); the
  source folder is never modified.
- `--source`, `--drafts-dir`, `--media-dir`, `--dry-run` and `--force`
  command-line options; existing drafts are not overwritten unless
  `--force` is given.
- Test suite covering installation, placeholder rewriting, source
  immutability, overwrite refusal and dry-run behaviour.
