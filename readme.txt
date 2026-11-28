RegexPad
========
Release: 1.0.0 (Stable)
Release date: October 25, 2026

Portable text editing and regular expression search/replace for Windows 11,
with HTML/CSS/WordPress article preparation tools and local WordPress Preview.

START
1. Extract the entire ZIP into a writable folder.
2. Keep regex-pad.exe, module_cleaner.exe, and _internal together.
3. Run regex-pad.exe. Use Language to select English or Japanese.
4. Open a document with Ctrl+O and save with Ctrl+S.

The complete bundle needs no separate Python, WordPress, PHP, MySQL, or Node
installation. Ordinary editing works offline. A lightweight build prepares
missing preview components on the first explicit Preview action and needs
internet access for that preparation. External article assets need their URLs.

MAIN OPERATIONS
- Ctrl+F: Find/Replace, regex, exclusions, replacement preview.
- F7: HTML/CSS/WordPress Grammar Check for the active tab.
- Ctrl+Shift+T: Tag/snippet insertion.
- Right-click the document: CSS, text colors, and Markdown table/list tools.
- Ctrl+Alt+P: Simple WordPress Preview with the neutral theme and HTML export.
- Ctrl+Alt+Shift+P: Live Twenty Twenty-Five theme preview.
- Ctrl+,: Options, including display and backup settings.
- F1: Built-in help.

Grammar Check and Preview do not automatically repair the source. Replace,
Regex Rewrite, insertion, and conversions are explicit text-changing actions.
JSON checking in Grammar Check concerns WordPress block-comment attributes.
Keep the source copy when transferring content to a real WordPress site.

PREVIEW
Run Preview again after editing: each request uses current unsaved text.
Refreshing a browser page does not submit changes from the editor.
Simple mode stops its WordPress process after export; live mode stays running
until Exit WordPress or its editor window closes. Simple export does not stop
a separate live preview. The prepared simple environment starts in the
background after about ten seconds; readiness may take longer, and automatic
prestart does not download missing components. Watch the WP status at right.

DOCUMENTATION
The following files are beside this EXE:
- readme_jp.txt: Japanese quick start.
- LICENSE.txt: Project license notice.
- README.md / README_jp.md: English/Japanese feature and setup overview.
- docs/HOW_TO_USE.md: English user guide.
- docs_jp/HOW_TO_USE_jp.md: Japanese user guide.
- docs/images/: Screenshots used by the guides.
- SCRIPT_STEPS.md: Development and verification record.

Markdown documents are readable as text; use a Markdown viewer for formatted
tables, links, and images. The complete distribution keeps their relative
paths intact.

SETTINGS AND RECOVERY
Settings: config.json beside the EXE.
Editable colors: color_presets.json beside the EXE.
Default saved-file backups: _internal/backup/.
Unsaved recovery data: _internal/autosave/.
Use File > Restore from Backup to load a recovery copy, inspect it, then save.
Automatic recovery copies do not update the original document. Save explicitly
before closing a modified tab.

CLEANUP
Close RegexPad and its previews. In this folder, inspect candidates first:
    .\module_cleaner.exe --dry-run
Then, if appropriate:
    .\module_cleaner.exe --clean

Clean asks for DELETE and includes WordPress runtime folders and exported
pages under Temp/WordPressPreview/. Keep needed documents, exports, and
backups elsewhere before removing them.

The EXE generates actual paths in _internal/DELET_ITEMS_LIST.md and
install_records/DELET_ITEMS_LIST.md. Save a copy before removing the folder.
Potentially shared references are grouped in the final warning section and
are not automatic cleanup targets. No persistent app-created system
environment variables or registry keys need removal.

LICENSE
RegexPad original application code: GNU GPL version 3 only (GPL-3.0-only).
Read the complete LICENSE and explanatory LICENSE.txt beside this file.
Use, modification and redistribution, including distribution for a fee,
are permitted under GPL terms. Separate third-party notices remain applicable.

Public source: https://github.com/Flopbrane/regex-mini-pad
SOURCE_CODE.md explains how a binary release must identify its actual source
revision/tag. The planned v1.0.0 tag is not asserted to be published or to
match the existing EXE. Qt/library corresponding source is a separate item.
THIRD_PARTY_NOTICES.md and LICENSES/ preserve upstream terms, including
Qt Virtual Keyboard's GPLv3 route and its third-party notices.

I got help from Chat-GPT and Codex.
