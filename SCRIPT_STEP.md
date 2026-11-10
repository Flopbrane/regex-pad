# SCRIPT_STEP.md

## Python environment

D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe

## Development Steps

This file records the planned build order for `mini_editor_project`.

## Completed

1. Main window
   - PySide6 `QMainWindow` entry point.
   - File, Edit, Search, View, and Language menus.

2. Basic text editor
   - `QPlainTextEdit` based editor.
   - Monospace font and basic tab width.

3. File open/save
   - New, Open, Save, Save As, and Exit.
   - Safe save through a temporary file.
   - Local settings file only.

4. Undo/Redo
   - Standard editor undo and redo actions.

5. Line numbers
   - Left-side line number area.
   - View menu toggle.

6. Find and Replace
   - Modeless Find / Replace dialog.
   - Find, Replace, Replace All, and Close.

7. Regular expression support
   - Python `re` based search and replace.
   - Regex replacement groups such as `\1` and `\2`.
   - Invalid regex handling without modifying source text.

8. Search options
   - Case-sensitive search.
   - Whole-word search.
   - Search only selected text.
   - Search only visible text.

9. Regex assistance
   - Regex insertion popup.
   - Regex lint warnings.
   - English and Japanese regex help.
   - Practical examples and replacement recipes.

10. App localization
    - English and Japanese application UI text.
    - Language menu.
    - Local language setting.

11. Encoding support
    - Open with Encoding.
    - Reload.
    - Reload with Encoding.
    - Save As encoding selector.
    - Preserve selected encoding when saving.

12. Saved-file generation backups
    - Save / Save As keeps the current on-disk file as a per-file backup before overwriting it.
    - Default backup retention count is 20 generations.
    - Unsaved backup remains a temporary crash-recovery file, separate from saved-file generations.

13. Snippet dictionary expansion
    - Added extra HTML, Markdown, and WordPress HTML snippets.
    - Kept dictionary entries backed by Japanese and English labels and hints.

## Next Recommended Steps

Progress on 2026-09-27:

- Regex rewrite / `normalise.py` workflow validation completed.
  - Full pytest passed: `207 passed`.
  - Ruff passed: `All checks passed!`.
  - Pyright passed: `0 errors, 0 warnings, 0 informations`.
  - JSON validation passed for app text resources and `wordpress_html_dict.json`.
  - Added a cancel-path test for the regex rewrite operation picker.
- Regex preview / replacement safety progressed.
  - Replace All from the Find / Replace dialog now fills the preview table and asks for confirmation before changing text.
  - Direct internal `replace_all()` calls remain usable for focused tests and non-dialog code paths.
- Save-time HTML / WordPress grammar safety progressed.
  - When HTML/WP typo lint is enabled, Save / Save As now runs the grammar check before writing.
  - If paragraph-split-related tag or WordPress block issues are found, the first issue line is selected and the user can cancel saving.
- Settings, dictionary, and file backup safety progressed.
  - Settings loading now falls back safely when individual values have invalid types.
  - Settings saving now uses a temporary file before replacing `settings.json`.
  - Saved-file generation backup now runs before overwriting an existing file.
  - Backup retention count / days now prune saved-file backup generations.
  - Unsaved backup stays scoped as temporary crash-recovery data for tabs/windows.
  - Snippet dictionaries were expanded with small practical HTML, Markdown, and WordPress entries.

1. Regex preview
   - Show match count before replacement.
   - Show target text snippets.
   - Make it clear what will be changed before Replace All.

2. Match highlighting
   - Highlight all current matches in the editor.
   - Keep current selected match visually distinct.
   - Show match markers beside the vertical scroll area.

3. Find Previous
   - Add previous-match navigation.
   - Keep wrap-around behavior predictable.

4. Replacement preview
   - Show before/after rows for regex replacement.
   - Allow users to confirm large replacements.

5. Newline handling
   - Detect CRLF / LF / CR.
   - Preserve newline style on save.
   - Add newline conversion if needed.

6. Character information
   - Total character count.
   - Space count.
   - Tab count.
   - Newline count.

7. Whitespace display
   - Visible spaces.
   - Visible tabs.
   - Visible newlines.

8. Ruler
   - Column ruler above the editor.
   - Toggle from View menu.

9. Rectangular selection
   - Rectangular selection mode.
   - Copy rectangular selection. Initial normal-selection-to-rectangle copy is implemented in `Step13-section1`.

10. Distribution
    - Review PyInstaller spec.
    - Verify resources load next to the executable.
    - Confirm portable folder behavior.

11. Tag insertion assistance
    - Continue from `Step11-section1`.
    - Refine tag insertion menus and dictionary-backed snippets.
    - Show file-format-specific tag snippets from the editor context menu.
    - Support mouse selection and keyboard selection with arrow keys plus Enter.
    - Consider automatic snippet set switching by extension, such as `.html`, `.md`, and `.wp.html`.

## Step11-section1 Tag Insertion Entry

Completed:

- Added the `Edit` menu entry `Insert Tag` / `タグ挿入`.
- Added tag insertion groups:
  - HTML
  - Markdown
  - WordPress HTML
- Added insertion templates that support:
  - `{selection}` for wrapping selected text.
  - `{cursor}` for placing the cursor after insertion.
- Added parameter hints through menu action `statusTip` and `toolTip`.
- Moved snippet data to local JSON dictionaries:
  - `dictionaries/html_dict.json`
  - `dictionaries/markdown_dict.json`
  - `dictionaries/wordpress_html_dict.json`
- Added common Markdown snippets:
  - headings, bold, italic, links, images, inline code, fenced code blocks, quote, lists, horizontal rule.
  - language-specific fenced code blocks for Python, HTML, CSS, JavaScript, JSON, PowerShell, Bash, and SQL.
- Added commonly used WordPress HTML snippets:
  - paragraph, headings, list, quote, code, preformatted, custom HTML code box, separator, spacer, and button.
  - `wp:code` uses `<pre class="wp-block-code"><code>...</code></pre>`.
  - `wp:html` custom code box uses a styled multi-line `<pre>` wrapper and keeps text immediately after `<code>`.
- Added common HTML snippets:
  - paragraph, headings, links, image, figure, div, span, lists, inline code, and pre/code block.
  - HTML hints describe common parameters such as `href`, `src`, `alt`, `class`, `id`, `data-*`, `target`, `rel`, `start`, `reversed`, and `type`.
- Added right-click tag insertion:
  - The editor context menu now includes `タグ挿入`.
  - It reuses the same snippet groups and insertion behavior as the menu bar.
- Added menu hierarchy refinement:
  - HTML is split into Basic, Link / Image, Layout, Lists, and Code.
  - Markdown is split into Text, Link / Image, Code, Lists, and Utility.
  - WordPress HTML is split into Text, Code, and Layout.
- Added file extension based ordering:
  - `.md` and `.markdown` prefer Markdown first.
  - `.html` and `.htm` prefer HTML first.
  - `.wp.html` prefers WordPress HTML first.
  - All snippet groups remain available even when one group is prioritized.
- Added keyboard tag insertion picker:
  - `Ctrl+Shift+T` opens the tag insertion picker.
  - The picker supports filtering snippets by text.
  - `Tab` or arrow keys move from the filter field to the candidate list.
  - `Enter` inserts the selected snippet.
- Confirmed Undo/Redo behavior:
  - Existing `Ctrl+Z` and `Ctrl+Y` shortcuts remain available.
  - Inserted snippets can be undone and redone as a single edit operation.

Follow-up candidates:

1. Dictionary JSON validation
   - Validate required keys: `label_key`, `hint_key`, and `template`.
   - Detect missing translation keys.
   - Detect missing or duplicated `{cursor}` when cursor placement is expected.
   - Detect unknown placeholders.
   - Detect empty labels, hints, or templates.

2. Richer parameter hints
   - Consider adding structured `parameters` arrays to JSON.
   - Generate hover text from structured parameter definitions.
   - This can later support linting or inline assistance for tag attributes.

3. Snippet search / keyboard picker
   - Add a small searchable popup for users who prefer typing tag names.
   - Support arrow keys plus Enter.
   - Keep menu insertion and popup insertion backed by the same JSON data.

4. Attribute-aware insertion
   - For common attributes such as `class`, `id`, `href`, `src`, and `alt`, consider optional prompt or placeholder navigation.
   - Keep the current direct insertion as the fast path.

## Step11-section2 Dictionary Validation

Completed:

- Added dictionary validation while loading tag snippet JSON.
- Required fields are checked:
  - `label_key`
  - `hint_key`
  - `template`
- Empty `label_key`, `hint_key`, and `template` values are rejected.
- Duplicated `{cursor}` placeholders are rejected.
- Unknown `{...}` placeholders are rejected.
  - Valid placeholders are `{selection}` and `{cursor}`.
- Added tests that confirm all tag snippet `label_key` and `hint_key` values exist in both:
  - `resources/app_text_en.json`
  - `resources/app_text_ja.json`

Follow-up candidates:

1. Structured parameters
   - Add optional `parameters` arrays to snippet JSON.
   - Store names such as `href`, `src`, `alt`, `class`, `id`, and `rel`.
   - Generate hint text from structured parameter metadata.

2. Duplicate snippet key detection
   - Detect duplicate `label_key` values within one dictionary.
   - Consider detecting duplicates across all dictionaries if cross-group uniqueness becomes important.

3. JSON schema documentation
   - Completed in `dictionaries/README.md`.
   - The note documents required snippet keys, supported placeholders, validation rules, and the typo lint reference JSON.

## Step11-section3 User Help Entry

Completed:

- Added an application help dialog.
- Added the `Help` / `ヘルプ` menu.
- Added the `Help...` / `使い方...` menu action.
- Added the `F1` shortcut for opening help.
- Help content covers:
  - File operations.
  - Undo / Redo.
  - Search / Replace.
  - Regex Help.
  - Tag insertion.
  - View options.
  - Language switching.
- Help content follows the current application display language.

Follow-up candidates:

1. Expand help topics as features grow
   - Character count.
   - Whitespace display.
   - Ruler.
   - Rectangular selection.

2. Add dedicated help pages
   - Basic editing.
   - Search and replace.
   - Regular expressions.
   - Tag insertion.

3. Add in-dialog navigation
   - Topic list on the left.
   - Search inside help text.
   - Links from feature dialogs to the relevant help topic.

## Step11-section4 User Help Navigation

Completed:

- Split the help dialog into dedicated topic pages.
- Added a topic list on the left side of the help dialog.
- Added separate help topics for:
  - File.
  - Edit.
  - Search / Replace.
  - Tag Insertion.
  - View.
  - Language.
- Preserved language switching for the currently open help dialog.
- Added View help text for the existing status bar character count.

Follow-up candidates:

1. Search inside help
   - Add a small filter field for help topics.
   - Highlight or jump to matching help text.

2. Direct links from feature dialogs
   - Open Search / Replace help from the Find / Replace dialog.
   - Open Tag Insertion help from the tag picker.

3. Externalize help content
   - Move help content from Python constants to JSON or Markdown files.
   - Keep Japanese and English help structures aligned by tests.

## Step11-section5 Search Navigation And Marked Replace

Completed:

- Added explicit previous / next search buttons beside the search text field.
  - Previous uses the `↑` button.
  - Next uses the `↓` button.
- Added previous-match navigation.
  - Uses the same search options as normal search.
  - Wraps around when there is no previous match before the cursor.
- Added `Replace Marked` / `マーカー部分を全て置換`.
  - Replaces the currently highlighted search marker ranges.
  - Applies replacements from the end of the document to avoid position shifts.
  - Supports regex replacement groups.
- Updated help text for search navigation and marked replacement.

Follow-up candidates:

1. Button icon polish
   - Consider compact icon-only styling for the arrow buttons.
   - Keep tooltips for clarity.

2. Marker replacement preview
   - Reuse the preview table to show only currently marked ranges.
   - Make the difference between all matches and marked matches clearer.

## Step11-section6 Tabbed Documents

Completed:

- Converted the editor surface to a tabbed document interface.
- `New` now creates a new untitled tab without discarding existing text.
- Untitled tab names use the first line of the document as a temporary title.
  - Empty tabs still use `Untitled` / `無題`.
- Added tab right-click commands:
  - `Close` / `閉じる`.
  - `Duplicate This Tab` / `このタブの複製`.
  - `Open in New Window` / `新規ウィンドウで開く`.
- Closing an unsaved tab asks whether to save, discard, or cancel.
- Duplicating a tab copies the current text into a new unsaved tab.
- Moving a tab to a new window transfers the text and file state, then removes it from the source window.
- Each window now has a UUID-based `window_id`.
- Parent windows keep child windows in `child_windows` by `window_id`.
- Updated the user help text with basic tab behavior.

Follow-up candidates:

1. Multi-tab autosave
   - Extend the current single unsaved backup to store multiple tabs.
   - Restore all unsaved tabs on launch.

2. Tab UI polish
   - Add close buttons on tabs after behavior stabilizes.
   - Add keyboard shortcuts for next / previous tab.
   - Consider middle-click close.

## Step11-section7 Options Window Entry

Completed:

- Added the `Options` / `設定` menu.
- Added the `Options...` / `オプション...` action.
- Added the `Ctrl+,` shortcut for opening the options window.
- Built the options window as a tabbed dialog.
- Grouped future and current settings by topic:
  - General
  - View
  - Tag Insert
  - Backup
  - Font
  - Search
- Connected the currently usable options:
  - Default WordPress HTML mode.
  - Hover hint visibility.
  - Backup folder.
  - Editor font family.
  - Editor font size.
- Kept not-yet-implemented options visible as disabled placeholders so the planned categories are clear.
- The backup folder option uses local files only.
- The application must not change environment variables from options.
- Settings that might otherwise require Registry usage should be stored in a local settings file instead.

Follow-up candidates:

1. Complete visible whitespace rendering
   - Draw half-width spaces.
   - Draw tabs.
   - Draw newline marks.
   - Use the saved `visible_spaces_enabled`, `visible_tabs_enabled`, and `visible_newlines_enabled` flags.

2. Backup detail options
   - Completed:
     - Backup retention count is editable and is used for saved-file generation backups.
     - Backup retention days is editable and is used for saved-file generation backups.
     - Unsaved backup remains temporary crash-recovery storage, not long-term history.
   - Remaining:
     - Backup interval.
     - Multi-tab temporary backup restore behavior.

3. Search option expansion
   - Regex lint display behavior.
   - Consider free color selection later if presets are not enough.

## Step11-section8 View And Search Options

Completed:

- Moved existing View toggles into the Options window:
  - Line numbers.
  - Word wrap.
- Added `Ruler` / `文字数ルーラー` as both:
  - A View menu toggle.
  - An Options > View setting.
- Implemented the lightweight character ruler:
  - `editor/ruler.py` now draws character-position ticks.
  - It follows the current editor font.
  - It follows horizontal scroll position.
  - It aligns with the line-number margin.
- Added Search color options:
  - Search marker color.
  - Current match marker color.
  - Preset colors are used first to keep the setting simple and stable.
- Stored the new settings in local `settings.json` through `EditorSettings`:
  - `ruler_enabled`
  - `search_marker_color`
  - `current_match_marker_color`
- Applied View and Search settings to all open tabs.
- Implemented visible whitespace rendering:
  - Options > View now has separate checkboxes for spaces, TABs, and newlines.
  - `EditorSettings` persists:
    - `visible_spaces_enabled`
    - `visible_tabs_enabled`
    - `visible_newlines_enabled`
  - `TextEditor.set_visible_whitespace_options()` stores those flags and requests a viewport update.
  - `TextEditor.paintEvent()` overlays visible marks without changing document text.
  - Half-width spaces use `␣`.
  - Full-width spaces use `□`.
  - TABs use `→`.
  - Newlines use `↵`.
  - Only visible blocks are painted.
- Fixed the main-window action initialization so Undo / Redo / Select All call the current editor lazily instead of reading `self.editor` before the first tab exists.
- Updated Japanese and English Options text for the new visible whitespace checkboxes.
- Updated tests for the new Options values, saved settings, visible whitespace mark detection, and the offscreen paint path.
- Moved the character ruler into each editor tab:
  - The ruler now appears below the tab bar and above the editor area.
  - Each tab owns its own `EditorTab` container with a `Ruler` and `TextEditor`.
  - Existing tab operations still address the underlying `TextEditor`.
- Added fixed-column wrap support:
  - Options > View now has `Wrap at ruler column` / `設定文字数で折り返す`.
  - Clicking the ruler stores the selected wrap column.
  - When fixed-column wrap is enabled, the editor wraps at the selected ruler column.
  - A thin green guide line marks the selected wrap column.
  - The source text is not modified; wrapping is display-only.
  - `EditorSettings` persists:
    - `fixed_column_wrap_enabled`
    - `fixed_column_wrap_column`
- Added `editor/editor_tab.py` for the per-tab ruler/editor layout.
- Updated tests for fixed-column wrap settings and editor behavior.
- Continued Options wiring:
  - General > Startup restore is now an editable checkbox.
  - Font > TAB width is now an editable spin box.
  - View > Wrap column is now an editable spin box.
  - TAB width is applied to existing and newly created tabs.
  - Startup restore controls whether the unsaved-backup restore prompt appears on launch.
  - The wrap-column spin box and ruler-click behavior share the same saved column value.
  - `EditorSettings` persists:
    - `startup_restore_enabled`
    - `tab_width`
- Updated tests for startup-restore opt-out, TAB width application, saved settings, and Options values.

Validation:

```powershell
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m ruff check .
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pyright
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool resources\app_text_en.json
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool resources\app_text_ja.json
```

Latest result:

```text
pytest: 113 passed
ruff: All checks passed
pyright: 0 errors, 0 warnings, 0 informations
JSON validation: app_text_en.json OK, app_text_ja.json OK
```

Follow-up candidates:

1. Visible whitespace polish
   - Tune marker color if it feels too strong or too faint.
   - Review behavior with very large files.
   - Review behavior with wrapped lines and proportional fonts.

2. Ruler polish
   - Review visual feel of the green wrap-column guide.
   - Review behavior with narrow windows and very large wrap columns.

3. Search / display interaction checks
   - Confirm visible whitespace markers remain readable when search highlights are active.
   - Consider user-facing presets if more display colors are added later.

4. Backup generation history
   - The retention count / days values are stored in Options.
   - Saved-file backups now rotate and prune by retention count / days.
   - The unsaved-backup implementation intentionally remains a temporary single crash-recovery file.
   - Add a restore UI for saved-file backup generations if users need in-app recovery.

## Step11-section9 General, Search, Backup, And Dictionary Options

Implementation order:

1. General > Display language
2. General > Default encoding
3. General > Newline code
4. Search > Regex lint
5. Backup > Retention count / retention days
6. Tag Insert > User dictionary folder / Dict validation

Changes:

- Made General > Display language editable from the Options window.
  - The selected language is applied immediately through the existing localization flow.
  - The value is persisted in the local settings file.
- Added General > Default encoding.
  - New tabs and fallback file state now use the configured default encoding.
  - Open-file encoding selection falls back to this setting.
  - Save still uses the current tab encoding after a file is opened.
- Added General > Newline code.
  - Save output can now be normalized to LF, CRLF, or CR.
  - The editor text itself is not rewritten when the option is changed.
- Added Search > Regex lint.
  - Regex lint warnings can be enabled or disabled from Options.
  - The setting is applied to the Find / Replace dialog when it is open or newly created.
- Added Backup > Retention count and Retention days.
  - The settings are persisted for the backup feature.
  - These values are now used to prune saved-file generation backups.
  - Unsaved backup remains a separate temporary recovery file and does not use generation pruning.
- Added Tag Insert > User dictionary folder.
  - User dictionaries can be loaded in addition to bundled dictionaries.
  - The Insert Tag menu and dialog use the configured user dictionary folder.
- Added Tag Insert > Dict validation.
  - When enabled, the selected user dictionary folder is validated before Options are applied.
  - Validation errors are shown with a localized message and the setting change is stopped.
- Updated Japanese and English option text for the new controls.
- Updated tests for settings persistence, option values, file newline output, regex lint disabling, and main-window option wiring.

Validation:

```powershell
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m ruff check .
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pyright
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool resources\app_text_en.json
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool resources\app_text_ja.json
```

Latest result:

```text
pytest: 113 passed
ruff: All checks passed
pyright: 0 errors, 0 warnings, 0 informations
JSON validation: app_text_en.json OK, app_text_ja.json OK
```

Follow-up candidates:

1. Backup restore UI
   - Saved-file generation backups are now created and pruned.
   - Add an in-app restore / compare UI if users should recover from backups without opening the backup folder manually.

2. User dictionary folder integration
   - Load user-provided dictionaries separately from bundled dictionaries.
   - Keep bundled dictionaries read-only in normal use.

## Step11-section10 HTML Transform Helpers

Changes:

- Added context-menu HTML transform commands:
  - HTML Escape
  - HTML Unescape
  - WordPress Code Block
- The commands only transform the selected text.
  - If there is no selection, they leave the document unchanged and show a status-bar message.
- HTML Escape uses Python's standard HTML escaping with quote characters preserved.
  - `<` becomes `&lt;`
  - `>` becomes `&gt;`
  - `&` becomes `&amp;`
  - quotes stay readable.
- HTML Unescape converts escaped HTML entities back to literal HTML.
- WordPress Code Block wraps the selected text in:
  - `<!-- wp:html -->`
  - Multi-line `<pre ...>` attributes for easier editing.
  - `><code>...</code></pre>`
  - `<!-- /wp:html -->`
- The WordPress code-block helper does not add extra newlines immediately after `<code>` or before `</code>`.
- The WordPress HTML custom code-box snippet uses the same multi-line `<pre>` style.
- Added a WordPress HTML link block snippet:
  - The selected text becomes the link text.
  - The cursor is placed inside `href=""`.
  - The snippet is available in Normal, Business / Office, and Hi-security modes.

Validation:

```powershell
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m ruff check .
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pyright
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest
```

Latest result:

```text
pytest: 125 passed
ruff: All checks passed
pyright: 0 errors, 0 warnings, 0 informations
JSON validation: app_text_en.json OK, app_text_ja.json OK, wordpress_html_dict.json OK
```

## Step11-section11 Dictionary Safety Validation

Changes:

- Strengthened dictionary JSON validation at load time.
- Error messages now include the dictionary file and item number where possible.
- Added detection for:
  - Missing required keys: `label_key`, `hint_key`, `template`.
  - Empty required values.
  - Duplicate `label_key` values inside one dictionary file.
  - Duplicate `{cursor}` placeholders.
  - Broken `{selection}` / `{cursor}` placeholders.
  - Unknown placeholders such as `{selected_text}`.
  - Missing dictionary label / hint translation keys in both Japanese and English resources.

Validation:

```powershell
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest tests\test_tag_insert.py
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m ruff check editor\tag_insert.py tests\test_tag_insert.py
```

Latest result:

```text
pytest tests\test_tag_insert.py: 33 passed
ruff targeted: All checks passed
```

## Step11-section12 Future Multi-language Dictionary Plugins

Lightweight placeholder only. Do not start the heavy implementation until the current editor display work, color work, and WordPress HTML refinements are stable.

Goal:

- Allow RegexPad to behave as a lightweight multi-language editing helper by loading additional user dictionary files.
- Example future user dictionaries:
  - `javascript.json`
  - `textscript.json`
  - `css.json`
  - `php.json`
  - Other language or workflow-specific snippet packs.

Proposed future shape:

- Keep bundled dictionaries read-only and stable.
- Treat user dictionaries as plugin-like optional snippet packs.
- A user dictionary should be able to declare:
  - Display group name or translation key.
  - Target extensions such as `.js`, `.css`, or custom text formats.
  - Snippets with `label`, `hint`, `template`, and optional `category`.
  - Optional language id for later linting or coloring.
- The current dictionary safety validation should remain the first gate before a user dictionary is accepted.

Future lint files:

- Added a lightweight `json_lint.py` for validating JSON structure and readable error output.
- Added placeholder `multi_lang_lint.py` as the future coordinator for language-specific standards.
- Added standard reference files only as data, not executable code.
  - Example names:
    - `standard_javascript.json`
    - `standard_textscript.json`
    - `standard_css.json`
- These standard files can define allowed snippet fields, placeholder rules, recommended categories, and later language-specific constraints.

Deferred on purpose:

- Syntax coloring for each language.
- Heavy multi-language parsing.
- Full plugin manager UI.
- Automatic linting while typing.
- Complex standard-file enforcement beyond dictionary validation.

First small implementation entry, when ready:

1. Expand standard JSON files only when the user dictionary plugin format is finalized.
2. Decide whether direct `label` / `hint` text is allowed in addition to translation keys.
3. Only after that, wire the lint result into Options `Dict validation`.

Validation:

```powershell
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest tests\test_multi_lang_lint.py
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m ruff check json_lint.py multi_lang_lint.py tests\test_multi_lang_lint.py
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool dictionaries\standards\standard_javascript.json
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool dictionaries\standards\standard_textscript.json
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool dictionaries\standards\standard_css.json
```

Latest result:

```text
pytest tests\test_multi_lang_lint.py: 5 passed
ruff targeted: All checks passed
standard JSON validation: OK
```

## Step11-section15 HTML / WordPress Typo Lint Reference Cache

Changes:

- Added `dictionaries/lint_reference.json` as the HTML / WordPress typo lint reference file.
- Added `search/html_typo_lint.py`.
- The lint reference is loaded once at module startup into `LintReferenceCache`.
- Repeated lint calls use cached sets and tuples instead of reading JSON files again.
- Typo lint can now report:
  - Unknown HTML tags against `html_tags`.
  - Unknown HTML attributes against `html_attributes`.
  - Unknown WordPress core block names against `wordpress_core_blocks`.
- `aria-*` and `data-*` are accepted through `allowed_attribute_prefixes`.
- Added tests for tag typo, attribute typo, WordPress block typo, allowed prefixes, and no JSON reread during lint calls.
- Added a manual grammar-check action:
  - The Search menu now includes `Grammar Check` / `文法チェック`.
  - Shortcut: `F7`.
  - The action runs the current document through the HTML / WordPress typo lint.
  - Results are shown with line numbers in a dialog.
  - When issues are found, the cursor moves to the first reported line.
  - When no issues are found, a no-issues message is shown.
- Added WordPress paragraph block structure checks:
  - Detect missing `<p>` inside `<!-- wp:paragraph --> ... <!-- /wp:paragraph -->`.
  - Detect missing `</p>` inside `<!-- wp:paragraph --> ... <!-- /wp:paragraph -->`.
  - Detect `<!-- /wp:paragraph -->` without a matching opening block.
  - Detect mismatched or unclosed WordPress block comments.
  - Show a dedicated warning when `<!-- wp:html -->` is missing `<!-- /wp:html -->`, because later text may be treated as part of the HTML block.

Warning 2026-09-24:

- The first Grammar Check implementation only checked tag names, attribute names, and WordPress block names.
- It did not validate the internal structure of `wp:paragraph`, so WordPress paragraph errors could be missed even when WordPress reported them after paste/save.
- Current behavior is a practical pre-save guard for the reported cases, not a complete Gutenberg validator.
- `wp:html` closing-block omissions are high-risk because WordPress may treat following paragraph text and block comments as part of the HTML block after draft save.
- If WordPress reports another paragraph/block restriction, add the exact rejected snippet and WordPress error text as a regression case before broadening the checker.

Validation:

```powershell
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest tests\test_html_typo_lint.py
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest tests\test_main_window_search.py tests\test_html_typo_lint.py tests\test_app_translation.py
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m ruff check .
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pyright
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool dictionaries\lint_reference.json
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool resources\app_text_ja.json
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool resources\app_text_en.json
```

Latest result:

```text
pytest targeted: 38 passed
pytest: 160 passed
ruff: All checks passed
pyright: 0 errors, 0 warnings, 0 informations
JSON validation: lint_reference.json OK, app_text_ja.json OK, app_text_en.json OK
```

## Step11-section17 Regex Replacement Dollar Groups

Changes:

- Added support for `$1`, `$2`, and other dollar-style regex replacement groups in Regex-Pad replacement text.
- Added support for named dollar groups such as `${name}`.
- Existing Python-style replacement groups such as `\1`, `\2`, and `\g<name>` remain supported.
- In regex mode, `$$` now inserts a literal `$`, so `$$1` produces literal `$1`.
- Replacement preview, Replace, Replace All, and Replace Marked all share the same search engine conversion.
- Regex replacement lint now validates dollar-style replacement groups too.
- Clarification:
  - The presence or absence of `\n` in the search pattern does not decide whether replacement is regex-based.
  - Regex-Pad uses regex behavior when the Regular expression checkbox is ON.
  - The issue was that Python `re.sub()` does not treat `$1` as a capture-group reference unless Regex-Pad converts it first.

Validation:

```powershell
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest tests\test_search_engine.py tests\test_regex_lint.py tests\test_main_window_search.py
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m ruff check search\search_engine.py search\regex_lint.py tests\test_search_engine.py tests\test_regex_lint.py
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pyright search\search_engine.py search\regex_lint.py tests\test_search_engine.py tests\test_regex_lint.py
```

Latest result:

```text
targeted pytest: 49 passed
targeted ruff: All checks passed
targeted pyright: 0 errors, 0 warnings, 0 informations
```

## Step11-section18 Regex Token Highlighting

Changes:

- Added regex-token highlighting to the Find / Replace dialog.
- When the Regular expression checkbox is ON, regex tokens in the Find and Replace inputs are shown in brown.
- Escaped literal HTML/WP text such as `\{` and `\}` remains unhighlighted where possible.
- The initial practical token coverage includes:
  - capture groups such as `(.*?)`
  - character classes by escape such as `\s*`, `\d+`, and `\w+`
  - anchors and alternation such as `^`, `$`, and `|`
  - replacement references such as `\1`, `$1`, and `${name}`
- When the checkbox is OFF, regex highlighting is disabled.
- The color is a UI hint only; regex execution is still controlled by the checkbox state.
- If inline highlighting is not readable enough in the actual GUI, add a one-line parsed-token preview between the Find and Replace inputs.

Validation:

```powershell
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest tests\test_find_replace_dialog.py
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m ruff check dialogs\find_replace_dialog.py dialogs\regex_input_edit.py tests\test_find_replace_dialog.py
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pyright dialogs\find_replace_dialog.py dialogs\regex_input_edit.py tests\test_find_replace_dialog.py
```

Latest result:

```text
targeted pytest: 9 passed
targeted ruff: All checks passed
targeted pyright: 0 errors, 0 warnings, 0 informations
```

## Step11-section16 Visible Whitespace Marker Colors

Changes:

- Added separate color settings for visible whitespace markers:
  - `visible_space_marker_color`
  - `visible_tab_marker_color`
  - `visible_newline_marker_color`
- Added View-tab Options controls for space, TAB, and newline marker colors.
- Existing tabs and new tabs now receive the configured marker colors.
- Visible whitespace painting now selects marker color by character type instead of using one shared color.

Validation:

```powershell
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest tests\test_text_editor_visible_whitespace.py tests\test_settings_manager.py tests\test_options_dialog.py -q
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m ruff check editor\text_editor.py settings\settings_manager.py dialogs\options_dialog.py main.py tests\test_text_editor_visible_whitespace.py tests\test_settings_manager.py tests\test_options_dialog.py
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pyright editor\text_editor.py settings\settings_manager.py dialogs\options_dialog.py main.py tests\test_text_editor_visible_whitespace.py tests\test_settings_manager.py tests\test_options_dialog.py
```

Latest result:

```text
targeted pytest: 10 passed
targeted ruff: All checks passed
targeted pyright: 0 errors, 0 warnings, 0 informations
```

## Step11-section13 WordPress Text Column Snippets

Changes:

- Added practical WordPress multi-column text snippets:
  - `2-column text block`
  - `3-column text block`
- Both snippets use WordPress standard `wp:columns` and `wp:column` wrappers.
- The selected text is inserted into the first column.
- The cursor is placed at the end of the first column's paragraph text.
- Remaining columns contain editable placeholder text.
- The snippets are categorized as Layout.
- The snippets are available in Normal, Business / Office, and Hi-security modes.
- Added Japanese and English labels and hover hints.

Validation:

```powershell
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest tests\test_tag_insert.py tests\test_app_translation.py
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m ruff check editor\tag_insert.py tests\test_tag_insert.py
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool dictionaries\wordpress_html_dict.json
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool resources\app_text_ja.json
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool resources\app_text_en.json
```

Latest result:

```text
pytest targeted: 39 passed
ruff targeted: All checks passed
JSON validation: wordpress_html_dict.json OK, app_text_ja.json OK, app_text_en.json OK
```

## Step11-section14 WordPress Custom Frame Snippet

Changes:

- Added a practical WordPress frame snippet:
  - `Custom frame block` / `自由枠ブロック`
- Added frame presets with temporary practical values:
  - `Notice frame block` / `注意枠ブロック`
    - `border: 2px solid #f2c94c`
    - `background-color: #fff8e1`
    - `color: #3a2a00`
  - `Info frame block` / `補足枠ブロック`
    - `border: 2px solid #2f80ed`
    - `background-color: #eef6ff`
    - `color: #102a43`
  - `Important frame block` / `重要枠ブロック`
    - `border: 3px solid #d64545`
    - `background-color: #fff1f1`
    - `color: #4a1111`
- The snippet uses a WordPress group wrapper and an editable inline `style`.
- The editable visual parameters are:
  - Border width: `border: 2px ...`
  - Border color: `#2f80ed`
  - Background color: `background-color: #f5f9ff`
  - Text color: `color: #111111`
  - Padding and border radius are included as practical defaults.
- The selected text is inserted into the frame paragraph.
- The cursor is placed at the end of the inserted paragraph text.
- The snippet is categorized as Layout.
- The snippet is available in Normal, Business / Office, and Hi-security modes.
- Added Japanese and English labels and hover hints.
- Future design note:
  - Add an Options `Theme` tab later.
  - Theme parameters should eventually manage editor colors and reusable content-frame values.
  - Candidate frame parameters:
    - Border width.
    - Border color.
    - Background color.
    - Text color.
    - Padding.
    - Border radius.
  - Keep current dictionary values as temporary defaults until theme editing exists.

Warning 2026-09-23:

- The business WordPress environment blocked or warned on the previous frame output.
- Temporary safety policy:
  - Treat decorated frame snippets as Custom HTML blocks.
  - Do not emit `wp:group` for decorated frame snippets.
  - Keep the opening and closing decorated `<div>` inside one `<!-- wp:html -->` block.
  - Do not split the opening `<div>` and closing `</div>` into separate `wp:html` blocks.
- Current temporary dictionary behavior:
  - `Custom frame block`, `Notice frame block`, `Info frame block`, and `Important frame block` now emit one `wp:html` block containing one styled `<div>`.
  - The selected text is inserted directly inside the styled `<div>` instead of being wrapped in an inner `wp:paragraph`.
  - This is intentionally conservative for on-site testing and may need another revision after the next saved test pattern is checked in the actual business WordPress environment.
- If additional restrictions appear, record the rejected snippet output and the WordPress warning/error text before changing the dictionary again.

Validation:

```powershell
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest tests\test_tag_insert.py tests\test_app_translation.py
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m ruff check editor\tag_insert.py tests\test_tag_insert.py
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool dictionaries\wordpress_html_dict.json
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool resources\app_text_ja.json
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool resources\app_text_en.json
```

Latest result:

```text
pytest tests/test_tag_insert.py: 44 passed
pytest full: 150 passed
ruff full: All checks passed
pyright full: 0 errors, 0 warnings, 0 informations
JSON validation: wordpress_html_dict.json OK
```

## Priority Implementation Queue From 2026-09-21

Track these items before adding larger editor features.

Current status:

Resolved items from the previous next-work order:

1. WordPress HTML mode policy documentation
   - Completed in User Help and this project note.
   - Normal, Business / Office, and Hi-security behavior is documented.
   - Current policy: stricter modes hide risky snippets rather than merely de-prioritize them.

2. Display feature review checklist
   - Completed as a manual/visual checklist below.
   - The checklist covers marker color, search highlights, wrapped lines, proportional fonts, large files, and narrow windows.
   - The actual GUI review should be run before changing colors or rendering behavior.

3. User dictionary plugin format decision
   - Completed for the current format.
   - Current decision: keep `label_key` / `hint_key` required for current user dictionaries.
   - Direct `label` / `hint` text is deferred until the plugin-like dictionary format is designed.

Recommended next-work order:

1. Structured parameter metadata
   - Completed for the minimum schema and validation.
   - Snippet JSON now accepts optional `parameters` arrays with `name`, `required`, `kind`, and `description_key`.
   - Validation rejects invalid parameter shapes, empty names, duplicate names, invalid `required`, invalid `kind`, invalid `description_key`, and missing translations for parameter description keys.

2. Separate lint helpers in Options
   - Foundation completed for the HTML/WP typo lint toggle.
   - The Search tab now owns ON/OFF settings for both Regex lint and HTML/WP typo lint.
   - The Search menu now has a manual Grammar Check action that runs the HTML/WP typo lint against the current document.

1. Dictionary safety validation - mostly completed
   - Completed:
     - Dictionary JSON is parsed at load time.
     - Required `label_key`, `hint_key`, and `template` values are checked.
     - Empty required values are rejected.
     - Duplicate `label_key` values inside one dictionary file are rejected.
     - Duplicate `{cursor}` placeholders are rejected.
     - Broken `{selection}` / `{cursor}` placeholders are rejected.
     - Unknown placeholders other than `{selection}` and `{cursor}` are rejected.
     - Optional structured `parameters` arrays are validated.
     - Parameter `description_key` values are checked against Japanese and English resources when present.
     - Dictionary label and hint keys are checked against Japanese and English resources at load time.
     - Error messages identify the dictionary file and item number where possible.
     - User dictionary folders can be validated from Options before applying the setting.
     - `dictionaries/README.md` documents bundled snippet dictionary format and validation rules.
     - Current user dictionaries continue to require `label_key` / `hint_key`; direct `label` / `hint` text is deferred to the future plugin-like dictionary format.
     - HTML/WP typo lint can be run manually from Search > Grammar Check.

2. Hover hint enrichment - mostly completed
   - Completed:
     - HTML, Markdown, and WordPress HTML hints were expanded.
     - Practical attribute guidance such as `href`, `src`, `alt`, `class`, `id`, `rel`, and `target` was added where relevant.
     - Hover hints remain optional through the Options window.
     - Tag menus now enable Qt menu tooltips when hover hints are enabled.
     - The Insert Tag dialog now updates its hint text when the mouse hovers over a snippet row.
     - Help now includes an HTML attribute guide for `href`, `src`, `alt`, `class`, `id`, `style`, link safety attributes, CSS requirements, and common inline style properties.
     - Structured parameter metadata usage in future linting or guided editing is recorded as future workflow work, not a current blocker.

3. WordPress HTML mode refinement - partially completed
   - Completed:
     - WordPress modes exist: `Normal`, `Business / Office`, and `Hi-security`.
     - Snippets are filtered by mode.
     - Media snippets such as image, gallery, video, audio, and layout/media blocks were categorized and reviewed in tests.
     - User Help documents the exact policy for each mode.
     - Stricter modes hide risky snippets rather than only de-prioritizing them.
     - No immediate work remains. Review the policy again only if users need a temporary "show all snippets" override.

4. User dictionary folder - completed for Options wiring
   - Completed:
     - User-provided dictionaries can be configured separately from bundled dictionaries.
     - The Insert Tag menu and Insert Tag dialog use the configured user dictionary folder.
     - Options has a `Dict validation` toggle.
     - Bundled dictionaries remain separate from user-provided dictionaries.
     - Current user dictionaries continue to require translation keys through `label_key` / `hint_key`.
     - Future plugin-like dictionary needs are recorded as future design work: group metadata, extension metadata, and direct labels.
     - `json_lint.py`, `multi_lang_lint.py`, and `standard_*.json` should stay lightweight until the plugin format is finalized.

5. PyInstaller dictionary packaging - completed
   - Completed:
     - `regex-pad.spec` includes the whole `dictionaries` folder.
     - Dictionary JSON files are not listed one by one.
     - A test checks that the spec includes `('dictionaries', 'dictionaries')`.
     - `regex-pad.spec` includes `resources/app_text_*.json` and `resources/regex_help_*.json`.
     - Clean PyInstaller build completed successfully.
     - Built executable startup smoke test completed without the previous `resources/app_text_en.json` `FileNotFoundError`.
   - Validation:
     - `.\build.ps1`
     - `Test-Path .\dist\regex-pad\_internal\resources\app_text_en.json`
     - `Test-Path .\dist\regex-pad\_internal\dictionaries\html_dict.json`
     - `dist\regex-pad\regex-pad.exe` stayed running for 3 seconds and was then stopped for the smoke test.

6. Display features - mostly completed
   - Completed:
     - Character ruler.
     - Ruler below the tab bar.
     - Click-to-set wrap column.
     - Green wrap-column guide line.
     - Visible half-width spaces, full-width spaces, tabs, and newlines.
     - Options wiring for line numbers, word wrap, ruler, wrap-at-column, wrap column, visible whitespace, and separate whitespace marker colors.
     - Display review checklist was added below for manual/visual checks.
     - No code change is queued for display features. Run the display review checklist on the actual GUI before changing marker colors or rendering behavior.

Display review checklist:

1. Large file visibility
   - Open or paste a long document with hundreds or thousands of lines.
   - Enable visible spaces, TABs, and newlines.
   - Scroll quickly and confirm the editor remains responsive enough for normal use.

2. Search highlight interaction
   - Search for a term that appears many times.
   - Confirm search markers, current match color, and whitespace marks remain readable together.
   - Check both light and dense text areas.

3. Wrapped line behavior
   - Enable word wrap and fixed-column wrap.
   - Use long Japanese and English lines.
   - Confirm visible spaces, TAB marks, newline marks, and the green wrap-column guide do not visually collide in a confusing way.

4. Proportional font behavior
   - Change the editor font to a proportional font from Options.
   - Confirm the ruler and wrap-column guide remain understandable.
   - If proportional fonts make the ruler misleading, document monospace as the recommended setting for ruler-based editing.

5. Narrow window behavior
   - Shrink the window width.
   - Confirm line numbers, ruler, search highlights, and visible whitespace marks do not obscure normal editing.

6. Color adjustment decision
   - Change colors only if the above checks show a concrete readability problem.
   - Prefer existing preset colors before adding a free color picker.

## Step12-section1 WordPress Image, Paragraph Split, And Simple Structure Check

Changes:

- Updated image insertion snippets:
  - `dictionaries/html_dict.json`
    - HTML `<img>` now inserts `style="width: 80%; display: block; margin: 2em auto 1.5em auto;"` immediately after `src`.
  - `dictionaries/wordpress_html_dict.json`
    - WordPress image block now inserts the same default image style.
  - `resources/app_text_ja.json` and `resources/app_text_en.json`
    - Image hover/help text now mentions default width, alignment, and outer margin.
  - `tests/test_tag_insert.py`
    - Added insertion tests that confirm `src=""` cursor placement and the default image style.

- Added paragraph split context-menu support:
  - `editor/paragraph_splitter.py`
    - Added focused WordPress paragraph splitting helpers.
    - Detects a simple `<!-- wp:paragraph --> ... <!-- /wp:paragraph -->` block containing `<p>...</p>`.
    - Rebuilds output as `paragraph before`, inserted block, and `paragraph after`.
    - Trims only edge `<br>` / `<br><br>` markers while preserving meaningful internal line breaks.
    - Supports spacer insertion, empty HTML code block insertion, and selected-text decorated frame wrapping.
  - `main.py`
    - Added the editor context-menu submenu `段落分割`.
    - Added menu items:
      - `スペーサー挿入`
      - `HTML挿入`
      - `枠組み指定`
    - Shows a warning when the cursor or selection cannot be safely handled as a single paragraph block.
  - `resources/app_text_ja.json` and `resources/app_text_en.json`
    - Added labels and error title strings for the paragraph split menu.
  - `tests/test_paragraph_splitter.py`
    - Added string-level regression tests for paragraph detection, spacer insertion, HTML insertion, code wrapping, decorated frame wrapping, and invalid positions.
  - `tests/test_tag_insert.py`
    - Added context-menu regression coverage for the `段落分割` submenu and its three entries.

- Confirmed decorated frame output does not use `wp:preformatted`:
  - Paragraph split `枠組み指定` uses one `wp:html` block containing a styled `div`.
  - Existing WordPress decorated frame snippets continue to use one `wp:html` block and do not emit nested `wp:paragraph` or `wp:preformatted`.
  - Added regression checks for this policy.

- Added WP block simple structure checks to Grammar Check:
  - `search/html_typo_lint.py`
    - Added lightweight count checks for:
      - `<!-- wp:paragraph -->` / `<!-- /wp:paragraph -->`
      - `<!-- wp:html -->` / `<!-- /wp:html -->`
      - `<p>` / `</p>`
      - `<pre>` / `</pre>`
      - `<code>` / `</code>`
    - Added detection for malformed `<\p>`.
    - Added detection for known `margin:2en` typo.
    - Added detection for `wp:html` nested inside `wp:paragraph`.
  - `resources/app_text_ja.json` and `resources/app_text_en.json`
    - Added localized warning messages.
    - Updated the no-issue message to:
      - `簡易チェック完了：大きな構造エラーは見つかりませんでした。`
  - `tests/test_html_typo_lint.py`
    - Added regression tests for all newly added simple structure checks.
  - `tests/test_main_window_search.py`
    - Updated the no-issue dialog expectation.

Important policy notes:

- Do not use `wp:preformatted` for decorated frame output.
- If `wp:preformatted` is used by a separate snippet, do not place `wp:html` inside that `wp:preformatted` block.
- Keep decorated frame snippets as a single `wp:html` block with ordinary HTML inside.
- The new simple structure check is intentionally lightweight. It is not a full HTML validator; it targets common WordPress paste-breaking mistakes first.

Validation:

```powershell
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool dictionaries\html_dict.json
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool dictionaries\wordpress_html_dict.json
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool resources\app_text_ja.json
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool resources\app_text_en.json
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest tests\test_paragraph_splitter.py tests\test_tag_insert.py
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest tests\test_html_typo_lint.py tests\test_main_window_search.py tests\test_app_translation.py
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pyright
```

Validation result:

- JSON validation passed for the changed dictionaries and resources.
- `pytest tests\test_paragraph_splitter.py tests\test_tag_insert.py`: 60 passed.
- `pytest tests\test_html_typo_lint.py tests\test_main_window_search.py tests\test_app_translation.py`: 48 passed.
- Full `pytest`: 204 passed.
- `pyright`: 0 errors, 0 warnings, 0 informations.
- Targeted Ruff passed for the changed Python test/lint files.
- Full `ruff check .` still stops on the pre-existing import-order issue in `dialogs/find_replace_dialog.py`; this was not introduced by Step12-section1.

## Step12-section2 Settings Resilience, Dictionary Expansion, And Saved-File Backups

Purpose:

- Split backup responsibilities clearly:
  - Unsaved backup is temporary crash-recovery data for tabs/windows.
  - Saved-file backup is per-file generation history made before overwriting an existing file.
- Address the frustration that Undo can be cut off at the pre-restore state by keeping external file generations as a separate recovery path.
- Keep `main.py` structurally stable for now; avoid large file splitting until more of the feature surface is settled.

Changes:

- Hardened settings loading and saving:
  - `settings/settings_manager.py`
    - Invalid individual setting value types now fall back to defaults instead of crashing startup.
    - Non-object `settings.json` content falls back to defaults.
    - String boolean values such as `"true"` / `"false"` are handled safely.
    - Numeric settings reject boolean values and fall back on invalid strings such as `"wide"`.
    - Settings are now saved through a temporary file before replacing `settings.json`.
    - Default `backup_retention_count` changed from 10 to 20.
  - `tests/test_settings_manager.py`
    - Added regression coverage for invalid setting value types.
    - Added coverage for saving when the parent settings folder does not exist.

- Added saved-file generation backups:
  - `fileio/file_backup_manager.py`
    - Added `FileBackupManager`.
    - Backs up an existing file before it is overwritten.
    - Skips backup creation when the target file does not exist yet.
    - Stores backups per original file path using a safe file-name prefix and path hash.
    - Prunes backups by retention count and retention days.
  - `main.py`
    - Save / Save As now calls the file backup manager before writing the new file content.
    - Historical note: the original default saved-file backup location was `autosave/file_backups`.
    - Current policy as of 2026-10-06: the default saved-file backup location is `_internal/backup`, and a configured backup folder is used directly.
    - Changing the backup folder from Options refreshes the saved-file backup manager; unsaved session restore stays under `_internal/autosave`.
  - `tests/test_file_backup_manager.py`
    - Added coverage for backup creation, missing-file skip behavior, and 20-generation pruning.
  - `tests/test_main_window_backup.py`
    - Added coverage that overwriting an existing file preserves the old content in saved-file backup history.

- Expanded snippet dictionaries:
  - `dictionaries/html_dict.json`
    - Added `<small>`, `<mark>`, `<details>`, and a basic `<table>` snippet.
  - `dictionaries/markdown_dict.json`
    - Added a 3-column table snippet.
  - `dictionaries/wordpress_html_dict.json`
    - Added a WordPress `wp:table` snippet.
    - Added a single-`wp:html` details/disclosure snippet.
  - `resources/app_text_ja.json` and `resources/app_text_en.json`
    - Added matching labels and hover hints for all new snippets.
  - `editor/tag_insert.py`
    - Updated category mapping and WordPress mode behavior for the new snippets.
  - `tests/test_tag_insert.py`
    - Updated snippet counts and mode/category expectations.
    - Added insertion tests for the WordPress table and single-`wp:html` details snippet.

- Added WordPress block parameter consistency checks:
  - `search/html_typo_lint.py`
    - Warns when WordPress block comment `{}` parameters are invalid JSON.
    - Warns when `wp:heading` `level` and the inner `<h*>` tag disagree.
    - Warns when `wp:spacer` `height` and inner HTML `style` height disagree.
    - Warns when `wp:image` `sizeSlug` and inner HTML `size-*` class disagree.
  - `resources/app_text_ja.json` and `resources/app_text_en.json`
    - Added localized Grammar Check messages for invalid block parameters and comment/HTML mismatches.
  - `tests/test_html_typo_lint.py`
    - Added mismatch and matching-case regression tests.

- Added WordPress parameter writing help:
  - `dialogs/user_help_dialog.py`
    - Added `WPパラメータ記述の注意事項` / `WordPress Parameter Notes`.
    - Documents that `{}` block attributes and inner HTML values must stay aligned.
    - Includes safe and risky examples for heading, spacer, and image blocks.
  - `tests/test_user_help_dialog.py`
    - Added navigation/content checks for the new help topic.

Policy notes:

- Unsaved backup should remain temporary and scoped to crash recovery. Do not treat it as long-term version history.
- Saved-file generation backup should run only when an existing file is about to be overwritten.
- The restore UI is available from File > Restore from Backup. It loads a selected backup into the editor as an unsaved change, so the original file is not overwritten until the user saves.
- The WordPress details snippet is provisional until real Gutenberg paste/save behavior is checked.
- The new parameter consistency lint is intentionally targeted. It checks common high-risk core blocks first, not every possible WordPress block attribute.
- Do not try to cover every core block attribute at once. When dictionaries add or change actual WordPress snippets, extend the lint with focused regression tests for those concrete attributes.

Validation:

```powershell
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest tests\test_settings_manager.py tests\test_tag_insert.py tests\test_app_translation.py
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest tests\test_file_backup_manager.py tests\test_main_window_backup.py tests\test_settings_manager.py
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest tests\test_html_typo_lint.py tests\test_user_help_dialog.py tests\test_main_window_search.py tests\test_app_translation.py
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m ruff check .
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pyright
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest
```

Validation result:

- Targeted settings / tag / translation tests: 62 passed.
- Targeted backup tests: 12 passed.
- Targeted lint / user help / save-warning / translation tests: 60 passed.
- Full `ruff check .`: All checks passed.
- `pyright`: 0 errors, 0 warnings, 0 informations.
- Full `pytest`: 221 passed.

## Step12-section3 Saved-File Backup Restore UI

Purpose:

- Finish the saved-file generation backup loop by adding an in-app recovery path.
- Keep restore behavior conservative: selected backups are loaded into the current editor as unsaved changes, not written directly over the original file.

Changes:

- Added File menu recovery action:
  - `main.py`
    - Added `Restore from Backup...` / `バックアップから復元...`.
    - Shows a dated backup picker for the current saved file.
    - Warns when no saved file is active or no backup exists for that file.
    - Respects the existing unsaved-change confirmation before replacing editor text.
    - Reads the backup using the current file encoding.
    - Marks restored content as modified so the user can review before saving.
  - `resources/app_text_ja.json` and `resources/app_text_en.json`
    - Added localized action text, picker text, empty-state messages, and restore result text.
  - `fileio/file_backup_manager.py`
    - Backup listing and pruning now sort by generated backup file name instead of file mtime.
    - This avoids unstable retention order when rapid consecutive backups inherit the same source-file mtime through `copy2`.

- Added regression tests:
  - `tests/test_main_window_backup.py`
    - Restoring a saved-file backup loads the backup text into the editor.
    - Restoring does not immediately overwrite the current disk file.
    - Declining the unsaved-change confirmation leaves the current editor text intact.

Validation:

```powershell
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest tests\test_main_window_backup.py tests\test_file_backup_manager.py
```

Validation result:

- Targeted backup tests: 10 passed.
- Full `ruff check .`: All checks passed.
- `pyright`: 0 errors, 0 warnings, 0 informations.
- Full `pytest`: 227 passed.

## Step13-section1 Rectangular Copy Foundation

Purpose:

- Start the rectangular-selection section with a safe, testable foundation.
- Provide a usable first action before implementing a full mouse/keyboard rectangular selection mode.

Changes:

- Added rectangular text extraction helpers:
  - `editor/rectangular_selection.py`
    - Converts normal text selection positions into line/column rectangle coordinates.
    - Extracts the same column range from each selected line.
    - Preserves short lines as empty cells instead of padding or changing source text.

- Added an Edit menu action:
  - `main.py`
    - Added `Copy as Rectangle` / `矩形としてコピー`.
    - Shortcut: `Ctrl+Alt+C`.
    - Copies the rectangular text to the clipboard.
    - Leaves editor text and undo history unchanged.
    - Shows status messages for no selection, empty rectangular copy, and successful copy.
  - `resources/app_text_ja.json` and `resources/app_text_en.json`
    - Added action and status text.

- Added regression tests:
  - `tests/test_rectangular_selection.py`
    - Covers position-to-rectangle conversion and rectangular text extraction.
  - `tests/test_main_window_rectangular_selection.py`
    - Covers MainWindow action wiring through the clipboard.

Remaining for this section:

- Full rectangular selection mode is still pending.
- Mouse-based rectangular selection and keyboard expansion are still pending.
- Visual rectangular selection highlighting is still pending.

Validation:

```powershell
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest tests\test_rectangular_selection.py tests\test_main_window_rectangular_selection.py tests\test_app_translation.py
```

Validation result:

- Targeted rectangular-copy tests: 7 passed.
- Full `ruff check .`: All checks passed.
- `pyright`: 0 errors, 0 warnings, 0 informations.
- Full `pytest`: 227 passed.

## Step13-section2 HTML Dictionary Help Topic

Purpose:

- Add a beginner-friendly HTML dictionary separate from the existing HTML attribute guide.
- Make RegexPad usable as a reference when writing ordinary HTML pages, not only WordPress snippets.

Changes:

- Added a new Help topic:
  - `dialogs/user_help_dialog.py`
    - Added `HTML Dictionary` / `HTML辞典`.
    - Covers the overview of HTML, CSS, and JavaScript responsibilities.
    - Includes a basic full-page HTML structure with `doctype`, `html`, `head`, `body`, `meta`, CSS, and script placement.
    - Lists common text, layout, media, form, table, and `head` tags, including tags not currently provided as snippets.
    - Explains what data can be placed inside tags: text, child HTML, attributes, metadata, CSS, JavaScript, and JSON data for scripts.
    - Adds META and JavaScript writing examples.
    - Adds a practical list of tags/features likely to be removed or restricted outside Normal mode, such as `script`, event attributes, `style`, `iframe`, embed tags, forms, SVG with script, `canvas`, and body-level `meta`/`link`.
    - Keeps code examples copyable from the Help viewer.

- Updated regression tests:
  - `tests/test_user_help_dialog.py`
    - Updated topic ordering after inserting `HTML辞典`.
    - Added Japanese and English content checks for the new dictionary.

Validation:

```powershell
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest tests\test_user_help_dialog.py
```

Validation result:

- Targeted user help tests: 6 passed.

## Step13-section3 HTML Tag Expansion, Risk Lint, And Color Picker

Purpose:

- Connect the new HTML dictionary to practical tag insertion.
- Add lightweight pre-save visibility for HTML tags and attributes that are often removed or restricted in stricter WordPress/security contexts.
- Improve existing color settings with visible swatches and a `#RRGGBB` color picker.
- Confirm that regex token coloring in Find / Replace already exists before changing that area.

Changes:

- Expanded HTML tag snippets:
  - `dictionaries/html_dict.json`
    - Added semantic/page-structure snippets: `header`, `nav`, `main`, `section`, `article`, `aside`, `footer`.
    - Added form/media snippets: `form`, `button`, `video`, `audio`.
  - `editor/tag_insert.py`
    - Categorized the new snippets into existing HTML menu groups.
  - `resources/app_text_ja.json` and `resources/app_text_en.json`
    - Added labels and hover hints for the new snippets.

- Added restricted HTML warnings:
  - `search/html_typo_lint.py`
    - Warns for tags that are likely to be removed or restricted by stricter WordPress/site settings, such as `script`, `style`, `iframe`, `object`, `embed`, form controls, `button`, and `canvas`.
    - Warns for event-handler attributes such as `onclick`.
    - Keeps these as warnings because they may be valid in normal standalone HTML.
  - `resources/app_text_ja.json` and `resources/app_text_en.json`
    - Added localized warning messages.

- Improved color selection UI:
  - `dialogs/options_dialog.py`
    - Existing color settings now show small color swatches in their combo boxes.
    - Added `色選択...` / `Choose Color...` buttons next to the existing color combo boxes.
    - The dialog accepts arbitrary colors through Qt's color picker and stores them as `#rrggbb`.
    - Applied to search marker colors, visible whitespace marker colors, and WordPress frame background/text colors.

- Confirmed existing regex coloring:
  - `dialogs/regex_input_edit.py`
    - `RegexInputHighlighter` already colors regex tokens when regex mode is enabled in the Find / Replace dialog.
    - No behavior change was made there in this section.

Validation:

```powershell
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool dictionaries\html_dict.json
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool resources\app_text_ja.json
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool resources\app_text_en.json
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest tests\test_tag_insert.py tests\test_html_typo_lint.py tests\test_options_dialog.py tests\test_find_replace_dialog.py
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m ruff check .
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pyright
```

Validation result:

- JSON validation passed for the HTML dictionary and both app translation files.
- Targeted tag/lint/options/find-replace tests: 90 passed.
- Full `ruff check .`: All checks passed.
- `pyright`: 0 errors, 0 warnings, 0 informations.

## Step13-section4 Editor Theme And HTML Syntax Highlighting

Purpose:

- Add full editor-side HTML tag coloring to make HTML and WordPress snippets easier to inspect in the main text editor.
- Add editor-wide theme switching with saved background, text, and HTML tag colors.
- Keep the implementation local and portable through the existing settings JSON.

Changes:

- Added editor-side HTML highlighting:
  - `editor/text_editor.py`
    - Added a `QSyntaxHighlighter` for HTML tags and WordPress block comments.
    - Tags such as `<div>`, `</p>`, and `<br>` are highlighted in the configured HTML tag color.
    - WordPress block comments such as `<!-- wp:paragraph -->` are highlighted in a softer comment color.
    - The highlighter is visual only and does not modify the source text.

- Added editor theme settings:
  - `settings/settings_manager.py`
    - Added persistent keys for `editor_theme`, `editor_background_color`, `editor_text_color`, and `html_tag_color`.
  - `dialogs/options_dialog.py`
    - Added theme presets: light, soft paper, dark, high contrast, and custom.
    - Added color picker rows for editor background, editor text, and HTML tag color.
  - `main.py`
    - Applies the saved editor colors to all open tabs.
    - Applies the selected colors immediately after accepting the Options dialog.
    - Applies the saved colors to newly created tabs.

- Updated localization and tests:
  - `resources/app_text_ja.json` and `resources/app_text_en.json`
    - Added labels for editor theme controls and color rows.
  - `tests/test_settings_manager.py`
    - Covered saving/loading the new theme fields.
  - `tests/test_options_dialog.py`
    - Covered the new theme controls and returned values.
  - `tests/test_text_editor_visible_whitespace.py`
    - Covered editor color application to the text editor stylesheet.

Validation:

```powershell
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool resources\app_text_ja.json
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool resources\app_text_en.json
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest tests\test_options_dialog.py tests\test_settings_manager.py tests\test_text_editor_visible_whitespace.py
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m ruff check .
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pyright
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest
```

Validation result:

- JSON validation passed for both app translation files.
- Targeted options/settings/text-editor tests: 13 passed.
- Full `ruff check .`: All checks passed.
- `pyright`: 0 errors, 0 warnings, 0 informations.
- Full `pytest`: 230 passed.

## Step13-section5 Modeless Grammar Check And Core Block Color

Purpose:

- Allow editing the main document while grammar check results remain visible.
- Reduce fragile tag-count false positives by counting actual HTML tag tokens instead of broad text matches.
- Make WordPress core block comment color configurable separately from ordinary HTML tag color.

Changes:

- Added a modeless grammar check results window:
  - `dialogs/grammar_check_dialog.py`
    - Added a reusable non-modal grammar check dialog.
    - Shows the current result summary and a clickable list of issue rows.
    - Clicking an issue moves the editor cursor to that line.
    - Added a `Recheck` / `再チェック` button so the user can keep the results window open while editing.
  - `main.py`
    - Manual Grammar Check now opens/updates the modeless result window instead of blocking with `QMessageBox.warning()` or `QMessageBox.information()`.
    - Save-time grammar confirmation remains modal because it protects the save operation.

- Tightened lint token counting:
  - `search/html_typo_lint.py`
    - Counts `<p>`, `<pre>`, and `<code>` pairs from extracted `<...>` HTML tag tokens.
    - Does not treat plain text such as `code` as a tag.
    - Accepts compact WordPress block comments such as `<!--wp:paragraph-->` and `<!--/wp:paragraph-->` for simple count checks.

- Added configurable core block color:
  - `editor/text_editor.py`
    - WordPress block comments can now use a separate configured color.
  - `settings/settings_manager.py`, `dialogs/options_dialog.py`, and `main.py`
    - Added `wordpress_core_block_color` to load/save, options, theme presets, and all-tab application.
  - `resources/app_text_ja.json` and `resources/app_text_en.json`
    - Added labels for core block color and grammar recheck.

- Updated tests:
  - `tests/test_main_window_search.py`
    - Verifies grammar check uses a modeless result window and that issue rows can jump to the source line.
  - `tests/test_html_typo_lint.py`
    - Verifies `<code>code</code>` and compact WordPress comments do not trigger false count mismatches.
  - `tests/test_options_dialog.py`, `tests/test_settings_manager.py`, and `tests/test_text_editor_visible_whitespace.py`
    - Covered the new core block color setting.

Validation:

```powershell
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool resources\app_text_ja.json
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool resources\app_text_en.json
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest tests\test_html_typo_lint.py tests\test_main_window_search.py tests\test_options_dialog.py tests\test_settings_manager.py tests\test_text_editor_visible_whitespace.py
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m ruff check .
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pyright
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest
```

Validation result:

- JSON validation passed for both app translation files.
- Targeted lint/main-window/options/settings/text-editor tests: 67 passed.
- Full `ruff check .`: All checks passed.
- `pyright`: 0 errors, 0 warnings, 0 informations.
- Full `pytest`: 231 passed.

## Step13-section6 Sample-Based Grammar Lint Expansion

Purpose:

- Reduce the gap between RegexPad's grammar check and the real `sample/test.wp_html` problems found during external review.
- Stop collapsing several different HTML/WP breakages into only one `<code>` count mismatch.
- Preserve the lightweight lint approach while adding regression coverage for the current sample.

Findings:

- `sample/test.wp_html` no longer had the old global backslash escaping issue.
- RegexPad reported only one `<code>` count mismatch because the existing lint mostly checked total open/close counts.
- The sample actually had several different issue categories:
  - Empty `<p></p>` outside a WordPress block.
  - Duplicated paragraph openings after the embed section.
  - Broken `/code&gt;` fragments.
  - Nested/unclosed `<code>` tags.
  - `<code>` contamination inside a separator block.
  - Missing `</strong>`.
  - Lone `<br>` outside a WordPress block.

Changes:

- Expanded `search/html_typo_lint.py`:
  - Added `<strong>` count mismatch checks.
  - Added non-nestable `<code>` nesting checks so broken code snippets are reported near their source.
  - Added orphan line checks for standalone `<p></p>` and `<br>` outside WordPress blocks.
  - Added a separator-body check that warns when `<code>` tags are mixed into a separator block.
  - Added a broken escaped close-fragment check for `/code&gt;`.
  - Added a lightweight duplicate WordPress paragraph opening check based on normalized visible paragraph text.
  - Adjusted the first mismatch position logic so an unclosed/nested `<code>` reports near the first nested problem instead of only near the final imbalance.

- Updated localization:
  - `resources/app_text_ja.json`
  - `resources/app_text_en.json`
  - Added user-facing messages for the new lint categories.

- Updated regression tests:
  - `tests/test_html_typo_lint.py`
    - Added focused tests for nested `<code>`, missing `</strong>`, orphan `<p></p>` / `<br>`, separator code contamination, `/code&gt;`, duplicate paragraph openings, and the real `sample/test.wp_html` problem categories.
    - The sample now produces multiple issue categories instead of only one `<code>` count mismatch.

Validation:

```powershell
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool resources\app_text_ja.json
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool resources\app_text_en.json
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest tests\test_html_typo_lint.py tests\test_main_window_search.py
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m ruff check .
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pyright
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest
```

Validation result:

- JSON validation passed for both app translation files.
- Targeted lint/main-window tests: 59 passed.
- Full `ruff check .`: All checks passed.
- `pyright`: 0 errors, 0 warnings, 0 informations.
- Full `pytest`: 236 passed.
- Current `sample/test.wp_html` lint output: 16 issue rows across the expected categories.

## Step13-section7 Escaped Code Display And Inline Tag Lint Order

Purpose:

- Re-check the grammar lint algorithm after `sample/test.wp_html` was mostly repaired.
- Avoid false positives from escaped HTML shown inside code display blocks.
- Report real inline HTML tag breakage at the source line instead of at a later unrelated matching tag.

Findings:

- Current `sample/test.wp_html` no longer has the previous broad set of sample breakages.
- The remaining grammar-check output had three rows:
  - 299 and 319 were `/code&gt;` fragments inside `wp:code` display content, not broken live HTML.
  - The `<strong>` issue was still real in the file, but the old count-based check pointed at a later normal `<strong>` line.
- Total tag counts are useful as a coarse fallback, but they are fragile for inline tags because a later valid close tag can mask where the actual omission started.

Lint order policy:

1. Read WordPress block comments first and identify block bodies.
2. Treat escaped display content inside `wp:code` and `wp:html` as code text for fragile escaped-fragment checks.
3. Run simple WordPress block structure checks.
4. Run real HTML token checks with `HTMLParser`.
5. For inline tags such as `strong`, `em`, `span`, `code`, and `a`, detect:
   - Unclosed inline tags before a parent close such as `</p>`.
   - Invalid closing order such as closing `</strong>` before `</span>`.
6. Keep dictionary/tag/attribute and WordPress attribute-vs-HTML consistency checks as targeted warnings.

Changes:

- Updated `search/html_typo_lint.py`:
  - Added inline-tag stack checks for unclosed inline tags before parent close tags.
  - Added a separate document-end message for inline tags that remain open at EOF.
  - Added closing-order checks for nested inline tags.
  - Stopped using global `<strong>` count mismatch as the primary diagnostic.
  - Ignored `/code&gt;` escaped-fragment warnings inside `wp:code` and `wp:html` bodies.

- Updated localization:
  - `resources/app_text_ja.json`
  - `resources/app_text_en.json`
  - Added repair-oriented messages for inline tag closing and closing-order issues.

- Updated regression tests:
  - `tests/test_html_typo_lint.py`
    - Added tests for `<strong>` missing before `</p>`.
    - Added tests for invalid inline nesting order.
    - Added tests for inline tags left open at document end.
    - Added tests confirming escaped HTML inside a WordPress code block is accepted.
    - Adjusted the real sample check so repaired samples do not depend on old issue counts.

Current sample result:

- `sample/test.wp_html` now reports one remaining issue:
  - 501行目: `<strong>` is not closed before `</p>`.
- The former 299/319 `/code&gt;` rows are no longer reported.

## Step13-section8 Planned Lint Ledger Refactor

Purpose:

- Prepare the next lint foundation pass before adding more individual rules.
- Reduce false positives and missed errors by separating typo detection, WordPress block structure, and HTML tag structure.
- Use the standard lint dictionary as the shared reference source instead of letting each check infer its own truth.

Direction:

- Treat `dictionaries/lint_reference.json` as the standard reference dictionary for known WordPress core blocks, HTML tags, HTML attributes, and allowed attribute prefixes.
- Gradually change the grammar check into three comparison stages:
  1. `Typo_lint`
     - Detect simple textual damage and dictionary mismatches.
     - Examples: unknown WordPress block names, unknown HTML tags, unknown attributes, `<\p>`, `margin:2en`, and fragile literal fragments.
     - Do not decide complex open/close structure here.
  2. `WP_lint`
     - Parse only WordPress block comments such as `<!-- wp:paragraph -->` and `<!-- /wp:paragraph -->`.
     - Build a WordPress block ledger with line numbers, open/close kind, block name, parent relationship, body range, and display-code/custom-HTML ranges.
     - Do not deeply validate HTML tags in this stage.
  3. `HTML_lint`
     - Parse real HTML tags using the WP ledger as context.
     - Ignore escaped display content inside `wp:code` and other ledger-marked display areas.
     - Check tag open/close order, missing close tags, unexpected close tags, and inline-tag parent boundaries.

Ledger policy:

- Prefer in-memory ledgers for normal lint execution.
- Use `lint_wp_blocks.json` and `lint_html_tags.json` only as optional debug output or inspection artifacts, not as always-on source-of-truth files.
- Avoid depending on stale generated JSON during ordinary grammar checks.
- If debug JSON output is added later, write it under a cache/debug location and make it explicitly regenerated per lint run.

Planned internal records:

- `WPBlockRecord`
  - `line_number`
  - `block_name`
  - `kind` (`open` / `close`)
  - `pair_id`
  - `parent_pair_id`
  - `body_start`
  - `body_end`
  - `is_display_code_area`
- `HtmlTagRecord`
  - `line_number`
  - `tag_name`
  - `kind` (`open` / `close` / `self_closing`)
  - `pair_id`
  - `wp_block_pair_id`
  - `ignored_reason`

Implementation notes for next pass:

- Keep existing user-facing grammar-check output stable while replacing the internal structure.
- First build ledger helpers inside `search/html_typo_lint.py` to avoid premature large-file/module splitting.
- After behavior is stable, consider extracting to dedicated modules such as `linting_wp_block.py` and `linting_html_tag.py`.
- Add regression tests for each migration step before removing old count-based checks.
- Keep `wp:code` and inline `<code>&lt;...&gt;</code>` display content out of live HTML structural checks.

## Step13-section9 Grammar Issue Background Highlight

Purpose:

- Make grammar-check findings visible directly in the main editor while the check result is active.
- Restore the editor to the normal theme/background when the warning context is gone or the text changes.

Changes:

- Updated `editor/text_editor.py`:
  - Added a separate grammar issue line highlight state.
  - Combined grammar issue selections with existing search selections instead of replacing search highlights.
  - Uses a faint red full-line background for grammar issue lines.

- Updated `main.py`:
  - Manual Grammar Check now highlights all issue lines in the current editor.
  - A no-issue result clears existing grammar issue highlights.
  - Editing the text clears stale grammar issue highlights.
  - Save-time grammar confirmation highlights issue lines only while the confirmation is active, then clears them.
  - Closing/hiding the modeless grammar-check dialog clears the highlights.

- Updated `dialogs/grammar_check_dialog.py`:
  - Added a `dismissed` signal emitted when the dialog is hidden.

- Updated `tests/test_main_window_search.py`:
  - Added regression tests for issue-line highlighting.
  - Added tests for clearing highlights after no-issue checks, edits, and dialog hide.

Validation:

```powershell
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest tests\test_main_window_search.py tests\test_text_editor_visible_whitespace.py
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m ruff check editor\text_editor.py dialogs\grammar_check_dialog.py main.py tests\test_main_window_search.py
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pyright
```

Validation result:

- Targeted grammar/search/editor tests: 43 passed.
- Targeted Ruff: All checks passed.
- Pyright: 0 errors, 0 warnings, 0 informations.

## Step13-section10 Line Selection From Gutter

Purpose:

- Make line selection easier while reviewing lint results or editing line-based text.
- Allow clicking the line-number area to select exactly that line.
- When line numbers are hidden, allow the far-left line head area to perform the same line selection.

Changes:

- Updated `editor/line_number_area.py`:
  - Left-clicking the line number gutter selects the clicked line.

- Updated `editor/text_editor.py`:
  - Added shared line-selection helpers based on visible block position.
  - Added a small left-edge hit area for line selection when line numbers are hidden.
  - Kept ordinary clicks unchanged outside that narrow left-edge area.

- Updated `tests/test_text_editor_visible_whitespace.py`:
  - Added tests for selecting a line by clicking the line-number area.
  - Added tests for selecting a line by clicking the line head when line numbers are hidden.

Related validation fix:

- Updated `fileio/file_backup_manager.py` after full-suite validation exposed an existing backup-retention instability.
  - Fast repeated backups could collide or sort inconsistently when relying on timestamps alone.
  - Backup filenames now include a manager-local monotonic sequence.
  - Backup file mtime is refreshed after copy so retention-days checks use the backup creation time rather than the source file timestamp.

Validation:

```powershell
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest tests\test_file_backup_manager.py tests\test_text_editor_visible_whitespace.py tests\test_main_window_search.py
```

Validation result:

- Targeted file-backup/editor/search tests: 48 passed.

## Step13-section11 Backup Scope Policy

Purpose:

- Clarify the backup feature policy after the line-selection and lint-highlight pass.
- Keep backup behavior simple and local instead of turning it into a full long-term generation history system.

Policy:

- Saved-file backups are treated as a per-file recovery ring, similar to an external Undo/Redo safety net.
- Keep about 20 recent backups per original file by default.
- Do not expand this into a separate heavy generation-backup feature unless requirements change.
- The temporary unsaved backup remains separate:
  - It is for tab/window crash recovery.
  - It is not long-term file history.
- The default backup location should remain inside the RegexPad project folder:
  - Unsaved temporary backup: `_internal/autosave/unsaved_backup.json`
  - Saved-file recovery backups: `_internal/backup`
- The current Options-based backup folder override is sufficient:
  - Empty setting uses the RegexPad-local default.
  - A configured folder stores saved-file recovery backups under that user-selected folder.
  - Unsaved session restore is not moved by the backup folder setting.

Implementation note:

- The current saved-file backup manager already keeps backups per original file path and defaults to 20 entries.
- Keep the restore UI conservative: selected backup content is loaded into the editor as an unsaved change, not written directly over the original file.

## Step13-section12 Paragraph Split Insertion Baseline

Purpose:

- Make the paragraph split insertion start point match the user's actual editing gesture.
- Reduce accidental paragraph splitting when inserting spacer, HTML code, or decorated frame blocks.

Changes:

- Updated `editor/paragraph_splitter.py`:
  - Spacer insertion now only works from an empty line inside a simple `wp:paragraph`.
  - Non-empty-line spacer insertion is rejected with a clear message asking the user to right-click an empty line created by Enter.
  - HTML code block wrapping and decorated frame wrapping now expand a partial selection to whole content lines before splitting the paragraph.
  - The selected line range becomes the inserted `wp:html` block content, while before/after lines remain normal paragraph blocks.

- Updated `main.py`:
  - Right-clicking the editor moves the cursor to the clicked position only when there is no active selection.
  - HTML insertion now uses the same selection-wrapping path as the code-block wrapper, so selected text is contained instead of inserting an empty block at the cursor.

- Updated `tests/test_paragraph_splitter.py`:
  - Added spacer-empty-line behavior coverage.
  - Added nonblank-line spacer rejection coverage.
  - Added partial-selection-to-line-range coverage for HTML code and decorated frame wrapping.

Validation:

```powershell
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest tests\test_paragraph_splitter.py
```

Validation result:

- Paragraph splitter tests: 10 passed.

## Step13-section13 Linter Token Inventory Hardening

Purpose:

- Continue hardening the Grammar Check / HTML-WP linter foundation.
- Move fragile count checks toward separate token inventories for WordPress block comments and live HTML tags.
- Keep displayed escaped code examples out of live HTML tag counting.

Changes:

- Updated `search/html_typo_lint.py`:
  - Added an internal `_LintToken` model for detected WordPress block comments and HTML tags.
  - WordPress block count checks now use a WordPress-comment token list instead of ad hoc per-rule counting.
  - HTML `<p>`, `<pre>`, and `<code>` count checks now use `HTMLParser`-collected live tag tokens.
  - Nested `<code>` detection now uses the same live tag token stream.
  - WordPress block mismatch handling no longer consumes the currently open block when the closing comment name is wrong and no matching block exists on the stack.

- Updated `tests/test_html_typo_lint.py`:
  - Added coverage that escaped display examples such as `&lt;code&gt;...&lt;/code&gt;` do not trip live `<code>` counts.
  - Added coverage that a wrong closing WordPress block comment does not hide a later valid closing comment for the still-open block.

Sample check:

- `sample/test.wp_html` currently reports only the expected `<strong>` before `</p>` issue at line 501.

Validation:

```powershell
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest tests\test_html_typo_lint.py
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m ruff check search\html_typo_lint.py tests\test_html_typo_lint.py
```

Validation result:

- HTML typo linter tests: 33 passed.
- Targeted Ruff: All checks passed.

## Step13-section14 HTML Structural Tag Lint Hardening

Purpose:

- Continue hardening the Grammar Check / HTML-WP linter after the token inventory baseline.
- Detect malformed live HTML tag order that count-only checks can miss.
- Keep the first pass conservative by limiting the structural stack check to `<p>`, `<pre>`, and `<code>`.

Changes:

- Updated `search/html_typo_lint.py`:
  - Added a structural stack pass over the existing live HTML tag token stream.
  - Detects tracked closing tags with no matching opener.
  - Detects crossed closing order such as `<pre><code>...</pre></code>`.
  - Detects tracked tags left open at the end of the document.

- Updated `resources/app_text_ja.json` and `resources/app_text_en.json`:
  - Added localized messages for unexpected, mismatched, and missing HTML closing tags.

- Updated `tests/test_html_typo_lint.py`:
  - Added regression tests for tracked-tag closing order, extra closing tags, and missing closing tags.

Sample check:

- `sample/test.wp_html` still reports only the expected `<strong>` before `</p>` issue at line 501.

Validation:

```powershell
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest tests\test_html_typo_lint.py tests\test_app_translation.py
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool resources\app_text_en.json
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool resources\app_text_ja.json
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m ruff check search\html_typo_lint.py tests\test_html_typo_lint.py
```

Validation result:

- HTML typo linter and app translation tests: 39 passed.
- JSON syntax checks: passed.
- Targeted Ruff: All checks passed.

## Step13-section15 Separator Code Cascade Suppression

Purpose:

- Reduce noisy cascade errors in Grammar Check when a separator block contains accidental `<code>` tags.
- Keep the root cause visible as one representative warning.
- Preserve line numbers and normal HTML tag checks outside the contaminated separator block.

Changes:

- Updated `search/html_typo_lint.py`:
  - Added detection for separator block bodies containing `<code>` tags.
  - Masks only those contaminated separator bodies before the general live-HTML tag checks run.
  - Preserves newlines while masking so later warning line numbers stay stable.
  - Keeps the WordPress separator-specific warning on the original source text.

- Updated `resources/app_text_ja.json` and `resources/app_text_en.json`:
  - Expanded the separator `<code>` warning to explain that it can confuse later tag checks and should first be repaired to `<hr ... />` only.

- Updated `tests/test_html_typo_lint.py`:
  - Added a regression test that `<hr ...><code><code>` inside `wp:separator` reports only the representative separator warning instead of cascading into `<code>` count, nesting, and missing-close warnings.

Sample check:

- `sample/test_sample.wp_html` now reports 8 review items instead of 14.
- The 130-line separator issue remains, while the six 131-line `<code>` cascade items are suppressed.

Validation:

```powershell
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest tests\test_html_typo_lint.py tests\test_app_translation.py
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool resources\app_text_en.json
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool resources\app_text_ja.json
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m ruff check search\html_typo_lint.py tests\test_html_typo_lint.py
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m ruff check .
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pyright
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest
```

Validation result:

- HTML typo linter and app translation tests: 40 passed.
- JSON syntax checks: passed.
- Targeted Ruff: All checks passed.
- Full Ruff: All checks passed.
- Pyright: 0 errors, 0 warnings, 0 informations.
- Full pytest: 255 passed.

## Step13-section16 WordPress Block Message Clarity

Purpose:

- Keep independent Grammar Check findings as separate rows even when line numbers repeat.
- Improve WordPress block findings so each row gives a concrete repair direction.
- Preserve the separator cascade suppression and the 8-item `test_sample.wp_html` result.

Changes:

- Updated `resources/app_text_ja.json` and `resources/app_text_en.json`:
  - `unexpected_wordpress_closing_block` now explains either removing the extra closing comment or adding the intended opening comment.
  - `mismatched_wordpress_block` now shows the expected closing comment before the currently encountered closing comment.
  - `missing_wordpress_closing_block` now shows the exact closing comment to add.

- Updated `tests/test_html_typo_lint.py`:
  - Added `sample/test_sample.wp_html` regression coverage for the current 8 finding rows.
  - Locked in the rule that independent findings remain separate while the separator `<code>` cascade stays suppressed.

Sample check:

- `sample/test_sample.wp_html` reports 8 review items:
  - line 31 `<strong>` before `</p>`
  - line 35 `<span>` before `</strong>`
  - line 49 `<a>` before `</p>`
  - line 78 missing `<!-- /wp:list-item -->`
  - line 85 close `<!-- /wp:list-item -->` before `<!-- /wp:list -->`
  - line 98 broken `/code&gt;`
  - line 130 separator `<code>` contamination representative warning
  - line 148 `<span>` before `</p>`

Validation:

```powershell
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest tests\test_html_typo_lint.py tests\test_app_translation.py
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool resources\app_text_ja.json
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool resources\app_text_en.json
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m ruff check .
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pyright
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest
```

Validation result:

- HTML typo linter and app translation tests: 41 passed.
- JSON syntax checks: passed.
- Full Ruff: All checks passed.
- Pyright: 0 errors, 0 warnings, 0 informations.
- Full pytest: 256 passed.

## Step13-section17 Grammar Check Copy List And Wider Dialog

Purpose:

- Make the Grammar Check dialog wide enough for longer Japanese repair hints.
- Let the user copy the current review list as plain text for notes or external review.

Changes:

- Updated `dialogs/grammar_check_dialog.py`:
  - Set the initial dialog size to `930 x 360`.
  - Added a copy-list action button.
  - Store the current result rows as newline-separated plain text.
  - Disable the copy button when there are no findings.

- Updated `resources/app_text_ja.json` and `resources/app_text_en.json`:
  - Added the localized copy-list button label.

- Updated `tests/test_main_window_search.py`:
  - Added regression coverage for the `930` width.
  - Added clipboard-copy coverage for Grammar Check findings.
  - Added no-issue coverage that keeps the copy button disabled.

Validation:

```powershell
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest tests\test_main_window_search.py tests\test_app_translation.py
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool resources\app_text_ja.json
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool resources\app_text_en.json
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m ruff check .
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pyright
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest
```

Validation result:

- Main window search and app translation tests: 39 passed.
- JSON syntax checks: passed.
- Full Ruff: All checks passed.
- Pyright: 0 errors, 0 warnings, 0 informations.
- Full pytest: 256 passed.

## Step13-section18 Linter Target Lines And Block Scope Hardening

Purpose:

- Point Grammar Check findings at the line that should be edited, not only the opening WordPress block comment.
- Catch HTML tag structure problems inside each WordPress core block.
- Keep escaped code examples inside `<code>...</code>` acceptable.
- Support whole-file HTML structure checks when the document has no WordPress block comments.
- Add conservative WordPress core block attribute checks for representative blocks.

Changes:

- Updated `search/html_typo_lint.py`:
  - WordPress paragraph checks now report the first body line, `<p>` line, or `<div>` line when available.
  - Separator `<code>` contamination now reports the line containing the stray `<code>`.
  - Repeated non-nestable WordPress blocks such as `wp:list-item` now report the next opening block line as the practical repair point.
  - HTML structure checks now run per WordPress block, while pure HTML files use a whole-file structure check.
  - Block-level HTML tags such as `div`, `main`, `section`, `ul`, `li`, and table tags are now included in structure checks.
  - Added conservative allow-list checks for common WordPress block comment attributes.

- Updated `resources/app_text_ja.json` and `resources/app_text_en.json`:
  - Added `unknown_wordpress_block_attribute` user-facing messages.

- Updated `tests/test_html_typo_lint.py`:
  - Updated expected line numbers from opening block lines to practical repair lines.
  - Added coverage for unknown WordPress block attributes.
  - Added coverage for accepted known block attributes.
  - Added coverage for an unclosed `<div>` inside a `wp:html` block.
  - Added coverage for whole-file pure HTML structure checks.

Notes:

- Japanese typo/style checks are intentionally left as future work because they need a separate Japanese dictionary and settings switch.
- The attribute check is intentionally conservative: blocks without an allow-list are skipped to avoid noisy false positives.

Validation:

```powershell
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest tests\test_html_typo_lint.py tests\test_app_translation.py
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool resources\app_text_ja.json
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m json.tool resources\app_text_en.json
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m ruff check search\html_typo_lint.py tests\test_html_typo_lint.py
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m ruff check .
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pyright
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest
```

Validation result:

- HTML typo linter and app translation tests: 45 passed.
- JSON syntax checks: passed.
- Targeted Ruff: All checks passed.
- Full Ruff: All checks passed.
- Pyright: 0 errors, 0 warnings, 0 informations.
- Full pytest: 260 passed.

## Step13-section19 Scheduled Linter Cascade Review

Date: 2026-10-02

Changes:

- Kept separator structural cascade suppression, but checked original markup for independent unknown tags, attributes, restricted markup, and fragile typos.
- Preserved multiple independent findings on the same line and stable ascending line-number ordering.
- Clarified JA/EN missing WordPress closing-block messages with insertion guidance before the next same-type block or the parent closing markup.
- Added regressions for two independent attributes on a contaminated separator line, a separate CSS typo, a later paragraph error, repeated list-item openings, and a list/list-item closing mismatch.
- Reviewed localized sample/test_sample.wp_html results: 8 findings at lines 31, 35, 49, 81, 98, 120, 131, and 148; no separator code cascade.

Validation:

- Focused linter and translation tests: 49 passed.
- JA/EN translation JSON parsing: passed.
- Full Ruff: passed.
- Pyright: 0 errors, 0 warnings, 0 informations.
- Full pytest: 264 passed.
- Manual GUI and real Gutenberg acceptance were not performed in this scheduled run.

## Step13-section20 WordPress Core Block Reference Dictionary Expansion

Date: 2026-10-03

Changes:

- Expanded `dictionaries/lint_reference.json` with the current official WordPress Core Blocks Reference block names.
- Added `wordpress_block_attributes` to `lint_reference.json` so `{}` parameter checks can be maintained from dictionary data instead of only hard-coded Python allow-lists.
- Kept common WordPress support attributes such as `className`, `style`, `metadata`, `lock`, and common color/font keys accepted conservatively across blocks.
- Added common WordPress-generated HTML attributes such as `srcset`, `sizes`, `decoding`, `fetchpriority`, `datetime`, `poster`, and media boolean attributes.
- Updated `search/html_typo_lint.py` to load block-attribute allow-lists from the startup lint reference cache.
- Updated README files and dictionary format notes for the expanded lint reference.
- Added regressions for official reference block attributes, unknown reference attributes, and WordPress image generated HTML attributes.

Notes:

- The reference is a bundled offline snapshot; RegexPad still does not fetch WordPress documentation at runtime.
- Deprecated / unsupported official core entries are accepted by the linter to avoid false unknown-block warnings, but this does not mean they should be promoted as snippet insertion candidates.
- Real Gutenberg paste/save acceptance was not performed in this step.

## Step13-section21 HTML Attribute Reference and Tag-Specific Lint

Date: 2026-10-05

Changes:

- Added `global_html_attributes` and `html_attributes_by_tag` to `dictionaries/lint_reference.json`.
- Added conservative tag-specific HTML attribute checks so known attributes on unusual tags, such as `href` on `<p>`, can be reported separately from unknown attributes.
- Preserved `aria-*`, `data-*`, and common global attributes as accepted on tag-specific checks.
- Expanded common HTML attribute typo suggestions for WordPress-generated media attributes such as `srcset`, `sizes`, `decoding`, and `fetchpriority`.
- Updated README files and dictionary format notes for the tag-specific HTML attribute dictionary.
- Added regressions for unexpected tag/attribute combinations, global/prefixed attributes, and `scrset` -> `srcset` suggestions.

Notes:

- The tag-specific attribute map is intentionally conservative and article-focused to avoid broad false positives.
- Real Gutenberg paste/save acceptance was not performed in this step.

## Step13-section22 Search Replace Focus Verification

Date: 2026-10-05

Changes:

- Confirmed the SearchEngine replacement path still covers literal replacement, regex groups, `$1` / `${name}` compatibility, preview, selected-only, and visible-only flows through existing tests.
- Restored the find-text focus after single Replace and Replace Marked operations, matching the existing Replace All behavior.
- Added GUI-level regressions for Replace, Replace All, and Replace Marked button flows returning focus to the find text box and selecting the current search text.

Notes:

- The checks were performed with Qt offscreen tests, not manual GUI interaction.

## Step13-section23 Linter Error Sample V2 Robustness

Date: 2026-10-05

Changes:

- Fixed JA/EN `invalid_wordpress_block_attributes` translations by escaping the literal `{}` as `{{}}`, preventing Grammar Check dialog crashes during `.format()`.
- Deduplicated unknown HTML tag warnings for the same tag on the same line, so `<pr>...</pr>` reports one `pr` typo instead of separate open/close messages.
- Suppressed WordPress block attribute-vs-HTML consistency checks when the block comment JSON is invalid, avoiding cascade messages such as default heading `level=2` mismatches after malformed JSON.
- Added typo suggestions for unknown WordPress block attributes such as `lebel` -> `level`.
- Added regressions for literal brace formatting, same-line unknown tag deduplication, invalid block JSON cascade suppression, and block-attribute typo suggestions.
- Checked `sample/wp_linter_error_test.wp_html` and `sample/wp_linter_error_test_v2.wp_html` through MainWindow message formatting with Qt offscreen.

Notes:

- `wp_linter_error_test_v2.wp_html` now formats without crashing and produced 63 findings after deduplication and invalid-JSON cascade suppression.
- Manual GUI dialog display with two real tabs was not performed in this step.

## Step13-section24 Per-Tab Grammar Check Result Files

Date: 2026-10-05

Changes:

- Added a small grammar lint result store that writes the current Grammar Check summary, rows, issue lines, document label, and source hash to a per-tab temporary JSON file.
- Associated each open editor tab with its own result file so multi-tab Grammar Check dialogs can switch to the selected tab's latest valid result.
- Invalidated and deleted stale result files when a tab's text changes, preventing old results from being shown after edits.
- Deleted the associated temporary result file when a tab is closed or removed.
- Deleted the temporary Grammar Check result folder when the last RegexPad window closes, so Temp does not retain an empty application namespace.
- Updated the Grammar Check dialog title to include the current document label, making the displayed result's owner visible.
- Updated README.md and README_jp.md with the per-tab Grammar Check result behavior.
- Added regressions for per-tab result separation, tab-switch dialog refresh, issue-line restoration, result-file deletion on tab close, and Temp folder deletion on window close.

Notes:

- Result files are stored under the OS temporary folder and are intended only for the current editing session; the result folder is removed when the final RegexPad window closes.
- The result is reused only when the stored source hash still matches the current tab text.
- Moving a tab to a new window recreates the tab in the destination window and does not preserve the old temporary result file.

## Step13-section25 WordPress Attribute Semantic Lint

Date: 2026-10-05

Changes:

- Added targeted WordPress block attribute semantic checks for JSON that is syntactically valid and uses known attribute names but has suspicious values.
- Warned when `wp:heading` `level` is a string instead of an integer.
- Warned when `wp:paragraph` `dropCap` is a string instead of a boolean.
- Warned when `wp:paragraph` `align` is outside the accepted `left`, `center`, and `right` values, including a `centre` -> `center` suggestion.
- Broadened WordPress block-comment recovery so malformed attribute text, such as `{"level":3}XYZ`, still participates in block start/end structure checks while reporting the JSON error.
- Added JA/EN messages for attribute type and value warnings.
- Updated README.md and README_jp.md with the attribute type/value lint behavior.
- Added regressions for type mismatches, invalid align values, and block-structure recovery after malformed attribute text.

Notes:

- This is intentionally narrow and dictionary-like: it covers the high-value cases from `sample/wp_linter_error_test_v2.wp_html` without attempting full WordPress schema validation.
- Real Gutenberg paste/save acceptance was not performed in this step.

## Step13-section26 Inline HTML Wrap Shortcuts

Date: 2026-10-05

Changes:

- Added editor actions for wrapping the current selection with common inline HTML.
- Added `Ctrl+B` for `<strong>...</strong>`.
- Added `Ctrl+U` for `<u>...</u>`.
- Added `Ctrl+Alt+R` for `<span style="color: red">...</span>`.
- Supported the no-selection case by inserting the tag pair and placing the cursor between the opening and closing tags.
- Added JA/EN action labels and exposed the actions in the Edit menu.
- Updated README.md and README_jp.md with the inline HTML shortcut behavior.
- Added regressions for shortcut assignment, selected-text wrapping, no-selection insertion, cursor placement, and undo.

Notes:

- These shortcuts are intentionally limited to common inline editing helpers and do not replace the existing tag insertion menu.
- Qt offscreen tests covered the action behavior; manual GUI keypress acceptance was not performed.

## Step13-section26b Seven Color Inline Span Shortcuts

Date: 2026-10-11

Changes:

- Expanded the inline color shortcut action from red-only to seven color variants.
- Assigned `Ctrl+Alt+1` through `Ctrl+Alt+7` to red, blue, green, orange, purple, pink, and gray text spans.
- Kept `Ctrl+Alt+R` as an additional red-text shortcut for existing muscle memory.
- Used hex color values in the generated `<span style="color: ...">` markup.
- Updated JA/EN action labels, README.md, and README_jp.md.
- Added regression coverage for shortcut assignment and selected-text wrapping with the color actions.

Notes:

- Number shortcuts were chosen to reduce the impact if `Alt` is not detected; the prior dangerous `Ctrl+R` reload shortcut has been removed separately.
- Qt offscreen tests cover QAction behavior, not physical Windows keypress acceptance in the packaged EXE.

## Step13-section27 Find/Replace Regex Input Follow-Up Checks

Date: 2026-10-05

Changes in progress:

- Kept the Find/Replace inputs as `RegexInputEdit` (`QPlainTextEdit`) so regex syntax highlighting can continue to work.
- Delayed Find/Replace focus restoration after Replace/Replace All with a 0 ms `QTimer` so Qt can finish the editor update first.
- Restored full selection of the search text after replacement so the next typed search pattern replaces the previous pattern instead of being inserted before it.
- Cleared a full-input selection when the regex input loses focus, keeping the text visible after moving to the replacement box or buttons.
- Added highlighting support for common escaped regex tokens such as `\n` and `\t`.
- Cleared stale preview rows whenever the search text, replacement text, or search options change.
- Made the Find/Replace search and replacement boxes vertically expandable so multi-line patterns can be inspected by resizing the dialog.
- Added regression coverage for second-pass regex input, visible search text after focus movement, second Replace All success, stale preview clearing, and expandable multi-line input boxes.
- 2026-10-06 follow-up: cleared existing editor search markers immediately when a new delayed search-highlight request is scheduled, preventing old markers from appearing to belong to the current search text.
- 2026-10-06 follow-up: added a regex lint warning for an actual `¥` character used where a regex escape backslash was likely intended. This only warns; it does not rewrite the user's pattern.
- 2026-10-06 follow-up: confirmed by command-line GUI simulation that `<!-- /wp:paragraph -->\n<!-- wp:paragraph -->\n` with real half-width backslashes (`U+005C`) matches and the Find button selects a match.
- 2026-10-06 follow-up: changed preview "after replacement" context so repeated matches on the same line show the line after all replacements in that line, avoiding misleading partial previews such as `<h3 ...></h2>`.
- 2026-10-06 follow-up: made unsaved-backup writes tolerate `PermissionError` / `OSError` during temporary-file replacement, cleaning up the temp file and avoiding traceback spam during editing.

Manual verification checklist for the next session:

- Start the app with `D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe main.py`.
- Open Find/Replace and enable regular expression search.
- Test first replacement with a WordPress paragraph-boundary pattern such as `<!-- /wp:paragraph -->\n\n<!-- wp:paragraph -->` and a replacement such as `<br><br>\n`.
- After Replace All, confirm the search box text remains visible when moving focus to the replacement box.
- Type a second pattern, for example `</p>\n<p>`, and confirm it replaces the previous search text rather than being inserted in front of leftover text.
- Confirm matching markers appear for the second pattern before replacement.
- Confirm changing the search text clears old markers immediately; stale markers should not remain while the 250 ms delayed highlight is pending.
- Run Replace All for the second pattern and confirm it no longer reports "no replacements" when matching text exists.
- Confirm the preview table clears when the search text, replacement text, or regex/search options are changed.
- Confirm a simple same-line replacement such as `2` -> `3` on `<h2 class="wp-block-heading"></h2>` previews as `<h3 class="wp-block-heading"></h3>`.
- Resize the Find/Replace dialog vertically and confirm the search and replacement boxes expand enough to inspect multi-line patterns.
- Confirm `\n`, `\t`, and `\d+` are highlighted in the regex input while regex mode is enabled.
- If a pattern visibly uses `¥n`, confirm whether the character is a displayed backslash (`U+005C`) or an actual yen sign (`U+00A5`). Actual `¥` should show a regex-check warning and should not be treated as an escape.
- If autosave reports access denied again, confirm whether another RegexPad instance, antivirus, sync tool, or read-only ACL is holding `autosave/unsaved_backup.json`; editing should continue without traceback after this change.
- If manual GUI behavior differs from tests, capture the exact search text with `find_text_edit.text()` before changing code again.

Validation already run:

```powershell
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m ruff check .
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pyright
```

Result:

- `pytest`: 295 passed
- `ruff check .`: All checks passed
- `pyright`: 0 errors, 0 warnings, 0 informations

Notes:

- The preview table does not write data back into the search or replacement inputs; it only displays rows and a summary.
- The earlier "visible search text but no match" case was caused by leftover previous search text remaining inside the input after `selectAll()` was removed.
- Real manual GUI acceptance on Windows was not completed after the final expandable-input change.

## Step13-section28 Unsaved Session Restore

Date: 2026-10-06

Changes in progress:

- Changed the unsaved-backup file from a current-editor-only backup into a restorable session format.
- Added `UnsavedBackupSession` with `version: 2`, `current_index`, and a `tabs` list while keeping legacy single-backup loading compatible.
- Saved all modified, non-empty tabs into `autosave/unsaved_backup.json`.
- Restored all saved tabs on startup when the user accepts the restore prompt, including the active tab index, encoding, and original save path.
- Stopped startup initialization from clearing a pending backup before the restore prompt is shown.
- Saving one tab now refreshes the unsaved session instead of deleting other modified tabs from the restore file.
- Opening or reloading a file now refreshes the unsaved session instead of clearing unrelated modified tabs.
- Duplicating, moving, or closing a tab refreshes the unsaved session so stale tab entries are less likely to remain after later abnormal termination.
- Continued to use a temporary file only as the write-in-progress target; the persistent restore data remains in `unsaved_backup.json`.

Manual verification checklist:

- Start the app, create two unsaved tabs, enter different text in both, then force-close from the terminal or Task Manager without using the app's normal close flow.
- Restart the app and accept the restore prompt; confirm both tabs return and the previously active tab is selected.
- Save only one restored tab, then force-close again; restart and confirm the saved tab is no longer restored but the other modified tab is.
- Open or reload a separate file while another tab is modified; confirm the modified tab remains restorable after a forced restart.
- Close the app normally after choosing save/discard for modified tabs; confirm the restore prompt does not reappear on the next normal launch.
- Confirm the restore file is created under `_internal/autosave/unsaved_backup.json`.
- Confirm saved-file backups are created under `_internal/backup` when the Options backup folder is blank.
- Set a custom backup folder in Options and confirm saved-file backups use that folder directly, while unsaved session restore still uses `_internal/autosave`.
- If `PermissionError` appears again, check whether another process is locking `_internal/autosave/unsaved_backup.json`; editing should continue without traceback.

Notes:

- This is a local session-restore mechanism, closer to modern Notepad behavior than a saved-file backup.
- It is still not a substitute for explicit file saving: normal Save writes the real document, while session restore protects unsaved editor state after abnormal termination.
- Default paths now separate the two backup types: unsaved session restore uses `_internal/autosave`, and saved-file generation backups use `_internal/backup` unless the user sets a custom backup folder in Options.
- 2026-10-06 follow-up: added an Options `配色` / `Colors` tab and moved editor color, tag color, search marker color, and whitespace marker color controls into it. The disabled color-theme checkbox is no longer shown in the View tab.
- 2026-10-06 follow-up: added `config.py` and changed the default settings file from `settings.json` to `config.json`. Existing `settings.json` is copied to `config.json` on first launch when `config.json` does not exist.
- 2026-10-06 follow-up: removed disabled placeholder checkboxes from the Backup Options tab: local settings file, no environment-variable changes, and restore mode.
- Automated validation after this change: `pytest` 309 passed, `ruff check .` passed, and `pyright` reported 0 errors.
- Manual forced-restart acceptance on Windows remains to be performed.

## Step13-section29 Emergency AutoSave and Regex Input Stability

Date: 2026-10-08

Emergency changes:

- Added a 3-minute unsaved-session autosave timer.
- Before risky operations that may discard or move editor state, the app now attempts to autosave modified tabs first.
- If that autosave fails, the risky operation is cancelled and a critical message is shown.
- Startup restore decline no longer deletes the pending unsaved-session file.
- Empty-but-modified tabs are now included in the unsaved-session JSON.
- Saved-file backups are now latest-only per source file, using `*.latest.bak`.
- Added paragraph-boundary regex recipes for both LF and CRLF:
  - `</p>\r?\n<p>` -> `<br><br>\n`
  - `</p>[ \t]*\r?\n[ \t]*<p>` -> `<br><br>\n`
- Stabilized the shared search/replace regex input widget by wrapping long text to the widget width and refreshing the viewport after selection/focus changes.

Notes:

- AutoSave and saved-file Backup remain separate mechanisms.
- AutoSave is for unsaved editor-state recovery and must not overwrite original files.
- Backup is for saved-file protection and now keeps only the latest backup file.
- The search and replace inputs still use `QPlainTextEdit` so multiline regex input and syntax highlighting remain available.

Validation:

- `pytest`: 315 passed
- `ruff check .`: All checks passed
- `pyright`: 0 errors, 0 warnings, 0 informations

## Step13-section30 Decorative Separator and Find/Replace Display Follow-Up

Date: 2026-10-09

Changes:

- Added a WordPress HTML snippet named `装飾区切り線` / `Decorative separator`.
- Placed the new snippet in WordPress `レイアウト` / `Layout`.
- Implemented it as a single `wp:html` block rather than a `wp:separator` block.
- The inserted HTML exposes editable CSS custom properties for:
  - line style: `--separator-line-style`
  - thickness: `--separator-thickness`
  - single color: `--separator-color`
  - gradient: `--separator-gradient`
- Added structured dictionary parameters for the same four values so a future parameter-input UI can reuse the metadata.
- Added JA/EN labels, hints, and parameter descriptions.
- Included the snippet in Normal, Business, and High-security WordPress modes.
- Added regression coverage for dictionary loading, category placement, mode placement, parameter metadata, and inserted HTML structure.

Find/Replace window follow-up:

- Historical note: the selection/repaint mitigation recorded below was superseded on 2026-10-13 by `Step14-section2`.
- Do not restore automatic full selection of both inputs or the duplicate 0 ms / 50 ms focus callbacks. Those operations contributed to the visible-text instability.

- The Find/Replace inputs still use `RegexInputEdit` (`QPlainTextEdit`) for multiline regex input and syntax highlighting.
- Real GUI behavior showed that, after replacement, the search/replacement text could appear blank even though the stored text remained intact.
- Manual dragging/selecting the text made the content visible again, suggesting a Qt layout/paint/selection refresh issue rather than data loss.
- The 2026-10-09 mitigation selected all text in both inputs after replacement, then refreshed the viewport. This behavior has now been removed.
- That mitigation also ran focus restoration twice with `QTimer.singleShot(0, ...)` and `QTimer.singleShot(50, ...)`. The 50 ms callback has now been removed.

Historical Find/Replace countermeasure notes:

- Manually verify the built EXE on Windows, not only offscreen pytest, because this issue is visual and timing-sensitive.
- Test Replace, Replace All, and Replace Marked with both short and long regex strings.
- Test moving focus between search box, replacement box, preview table, and main editor after replacement.
- Confirm both `.text()` and visible rendering remain correct after each operation.
- If the visual disappearance still occurs, consider replacing `RegexInputEdit` (`QPlainTextEdit`) with a custom single/multiline input wrapper that uses `QLineEdit` for one-line patterns and opens a larger editor only on demand.
- If keeping `QPlainTextEdit`, consider an explicit `repolish` helper that temporarily toggles focus or selection state in a controlled way after replacement.
- Avoid changes that silently rewrite search or replacement text; display fixes must not mutate the actual pattern.

Validation:

- `json.tool`: `dictionaries/wordpress_html_dict.json`, `resources/app_text_ja.json`, and `resources/app_text_en.json` passed.
- `pytest`: 322 passed.
- `ruff check .`: All checks passed.
- `pyright`: 0 errors, 0 warnings, 0 informations.

## Step14-section1 Embedded WordPress Conversion Core and Shortcut Safety

Date: 2026-10-11

Scope:

- Move the high-value Markdown-to-WordPress conversion core into RegexPad itself.
- Keep RegexPad as a one-folder portable application with no environment-variable changes and no external `wp_converter` executable requirement.
- Add selected-text conversion for Markdown tables and lists while avoiding nested WordPress paragraph blocks.
- Harden risky keyboard shortcuts after a reported accidental reload/data rollback path.

Embedded conversion core:

- Added `wp_conv_core/` as a local, RegexPad-owned conversion module.
- Namespaced imported converter pieces with `wp_` prefixes where needed to avoid collisions with existing project folders such as `dictionaries`.
- Added `editor/wordpress_markdown_converter.py` as the RegexPad-facing adapter layer.
- Supported Markdown table conversion into `wp:table`.
- Supported unordered and ordered Markdown list conversion into `wp:list` and `wp:list-item`.
- Supported common inline Markdown inside converted cells/items:
  - `**strong**`
  - `*emphasis*`
  - backtick code
  - Markdown links
  - plain URL auto-linking

UI integration:

- Added selected Markdown table/list conversion under the editor context menu's `段落分割` submenu.
- Added separate actions for:
  - `表変換`
  - `リスト変換`
  - `Markdown表/リストをWordPressブロック化`
- Kept the existing `HTML変換` menu focused on HTML escape/unescape and WordPress code block conversion.
- When the selection is inside a WordPress paragraph block, conversion now only proceeds when the selected range covers the paragraph content that can safely be replaced by a standalone block.
- Partial selections inside a paragraph are rejected with a status message so `wp:table` or `wp:list` is not inserted inside `<p>...</p>`.

Shortcut safety follow-up:

- Removed the `Ctrl+R` shortcut from Reload after a likely accident path was identified:
  - user intended `Ctrl+Alt+R` for red text,
  - `Alt` may have failed to register,
  - the app received `Ctrl+R`,
  - Reload replaced the editor text with the last manually saved file contents.
- Added a reload confirmation dialog for modified documents.
- Reload still saves an unsaved-session backup before continuing; if the user cancels the confirmation, the current editor text remains unchanged.
- Added regression coverage that Reload has no keyboard shortcut and that cancelling Reload preserves modified text while keeping the recovery backup.

Inline color shortcut follow-up:

- Expanded red-only inline color wrapping into seven color actions:
  - `Ctrl+Alt+1`: red
  - `Ctrl+Alt+2`: blue
  - `Ctrl+Alt+3`: green
  - `Ctrl+Alt+4`: orange
  - `Ctrl+Alt+5`: purple
  - `Ctrl+Alt+6`: pink
  - `Ctrl+Alt+7`: gray
- Kept `Ctrl+Alt+R` as a red-text compatibility alias.
- Used number shortcuts to reduce damage if `Alt` is not detected.

Documentation:

- Updated `README.md` and `README_jp.md` for the embedded `wp_conv_core` conversion behavior.
- Updated `README.md` and `README_jp.md` for the seven inline color shortcuts.
- Added JA/EN resource strings for conversion actions, reload confirmation, and color actions.

Decorated block safety follow-up:

- Added Grammar Check guidance for styled `wp:preformatted` and `wp:group` blocks.
- If either block contains a direct `style` attribute in its HTML body, RegexPad now warns that decorated content should be moved to a Custom HTML `wp:html` block.
- If either block uses a WordPress block-comment `style` parameter, RegexPad warns on the block opening line.
- Plain, unstyled `wp:preformatted` and `wp:group` blocks remain accepted.
- The warning is intentionally narrow; `wp:html` remains the preferred destination for colored text, backgrounds, borders, padding, and free-form layout.

Validation:

- Focused WordPress conversion tests: 29 passed.
- `tests/test_main_window_backup.py`: 21 passed after Reload safety changes.
- `tests/test_tag_insert.py`: 60 passed after seven color shortcut changes.
- `tests/test_html_typo_lint.py` plus translation checks: 66 passed after decorated block guidance.
- `json.tool`: `resources/app_text_ja.json` and `resources/app_text_en.json` passed.
- `ruff check .`: All checks passed.
- `pyright --pythonpath D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe`: 0 errors, 0 warnings, 0 informations.
- Full `pytest`: 338 passed, 4 failed.

Known remaining failures:

- `tests/test_main_window_search.py::test_replace_all_button_previews_and_replaces`
- `tests/test_main_window_search.py::test_replace_all_button_replaces_wordpress_paragraph_gap_regex`
- `tests/test_paragraph_splitter.py::test_split_paragraph_insert_html_code_block`
- `tests/test_regex_input_display_flow.py::test_replace_all_then_second_regex_input_keeps_display_and_regex_colors`

Notes:

- The full-suite failures above are the existing Replace All preview retention and paragraph splitter issues observed before the Step14 changes.
- Real Windows GUI keypress acceptance and packaged EXE validation remain to be performed.
- Real Gutenberg paste/save acceptance for the generated table/list blocks remains to be performed.

## Step14-section2 Find/Replace Visible Text and Automatic Input Height

Date: 2026-10-13

Reported symptoms:

- After Replace, Replace All, or Replace Marked, the search/replacement strings could appear blank even though the document markers still reacted to the stored search value.
- A second reported case used this multiline search text:
  - `<!-- /wp:heading -->`
  - a blank line
  - `<!-- wp:paragraph -->`
- Moving the cursor to edit the real newline as the regex token `\n` made the whole input appear empty.
- In both cases, the internal value remained intact; this was a rendering, selection, focus, scroll, and viewport-height problem rather than data loss.

Historical comparison:

- Compared the packaged `regex-pad_Step11-section14.zip` build with repository history.
- The EXE timestamp was 2026-09-23 21:41 and closely matched commit `a2c7306` from 21:38.
- That stable build used `QLineEdit` for both Find and Replace inputs.
- Commit `9767b36` on 2026-09-24 changed both inputs to `RegexInputEdit`, based on `QPlainTextEdit`, so multiline input and partial regex syntax coloring could be supported.
- The display instability started after this widget change; the later Markdown table/list core import was not the cause.

Change policy:

- Keep `RegexInputEdit` / `QPlainTextEdit` so partial brown regex-token highlighting and multiline search input remain available.
- Never rewrite or reassign the stored search/replacement text merely to repair its appearance.
- Display recovery must preserve cursor position, selection state, undo behavior, IME state, replacement preview rows, and search markers.
- Do not automatically select all text after replacement.
- Restore focus once on the next Qt event cycle; do not run a second delayed 50 ms focus/selection callback.
- Use non-mutating viewport refreshes only when a repaint is needed.
- Fit each input to its visual line count, including wrapped lines, from 1 through 5 visible lines.
- For 6 or more visual lines, keep the input at 5 lines and use the vertical scrollbar.
- A repaint alone cannot fix a one-line viewport that is correctly showing an empty logical line. The viewport must expose surrounding non-empty lines.

Modified locations:

- `main.py`
  - `_focus_find_text_after_replace_all()` now queues only one 0 ms focus restoration.
  - `_focus_find_text_after_replace_all_now()` refreshes both inputs without selecting or rewriting their contents, then focuses the Find input.
- `dialogs/regex_input_edit.py`
  - Added automatic height calculation from the laid-out document height so real newlines and wrapped lines are both counted.
  - Added a 1-line minimum and 5-line maximum.
  - Added queued height recalculation after text and width changes.
  - Retained regex syntax highlighting and non-mutating viewport refresh behavior.
- `tests/test_main_window_search.py`
  - Replace, Replace All, and Replace Marked now assert that both input strings remain intact and neither input is automatically selected.
- `tests/test_regex_input_display_flow.py`
  - Added repeated replacement coverage and checks that the second replacement keeps both strings visible and unselected.
- `tests/test_find_replace_dialog.py`
  - Added automatic one-line-to-multiline height coverage.
  - Added the exact WordPress heading/blank-line/paragraph regression pattern.
  - Added the 5-line height-cap and vertical-scroll regression check.

Observed dimensions in the offscreen GUI check:

- One visual line: 26 px.
- The reported three-line pattern: 54 px.
- Ten lines: 82 px, capped at five visible lines with vertical scrolling.
- With the cursor on the blank middle line, the first and third lines remained inside the visible viewport.

Validation:

- Focused Find/Replace tests: 65 passed.
- Full suite excluding the known paragraph-splitter mismatch: 337 passed.
- Full suite: 346 passed, 1 failed.
- Ruff: All checks passed.
- Pyright with the project interpreter: 0 errors, 0 warnings, 0 informations.
- `git diff --check`: passed.
- User-confirmed source-script acceptance on Windows: the text remained drawn after the second replacement.

Known remaining issue and acceptance scope:

- `tests/test_paragraph_splitter.py::test_split_paragraph_insert_html_code_block` still fails because the test places the cursor on non-empty `行B`, while the current implementation requires an empty user-created line. This failure is unrelated to Find/Replace rendering.
- The newly rebuilt packaged EXE has not yet been tested for this change.
- Continue checking repeated replacement, focus movement, actual newlines, literal `\n`, long wrapped regex patterns, and Japanese IME input in the Windows GUI.

## Step15-section1 CSS, JSON, HTML Tag, and WordPress Block Dictionaries

Date: 2026-10-13

Goal:

- Prepare dictionary-backed syntax and semantic checks before expanding the lint pipeline.
- Keep the intended flow explicit:
  - whole-text typo checks
  - HTML parsing and `style` attribute extraction
  - CSS validation by the future `css_lint.py`
  - WordPress core-block parsing and JSON attribute extraction
  - JSON syntax validation by `json_lint.py`
- Make HTML checks derive allowed attributes from the combination of the tag name and its attribute definitions.

Dictionary responsibilities:

- `dictionaries/lint_reference.json`
  - Remains the broad reference for known HTML tags, globally allowed attributes, tag-specific attribute names, permitted `aria-` / `data-` prefixes, WordPress core-block names, and block-attribute names.
  - This file answers whether a tag or attribute name is known and allowed.
- `dictionaries/standards/html_tag_schema.json`
  - Adds typed definitions for common tag-specific and global attributes.
  - Records enum candidates, integer minimums, required attributes, allowed empty values, and void elements.
  - Starts with common article tags, headings, lists, tables, images, links, media, code, figures, quotations, and time elements.
  - `img` requires both `src` and `alt`; an empty `alt` remains valid for decorative images.
  - The `style` global attribute points to the `css_inline_style` value schema so HTML lint can later delegate its value to CSS lint.
- `dictionaries/standards/standard_css.json`
  - Replaces the placeholder with an active CSS reference.
  - Defines stylesheet and inline-style contexts, common properties, accepted value categories, units, CSS functions, at-rules, global keywords, custom/vendor prefixes, common typo repairs, and full-width punctuation repairs.
- `dictionaries/standards/standard_json.json`
  - Defines JSON root/value types, literals, escapes, number syntax, unsupported JavaScript-style features, common typo repairs, full-width punctuation repairs, and syntax-error hints.
- `dictionaries/standards/wordpress_block_schema.json`
  - Adds typed attributes for 15 common Gutenberg core blocks.
  - Defines shared attributes plus per-block string, boolean, integer, array, object, enum, range, URL, and CSS-length constraints.

Implementation:

- `multi_lang_lint.py`
  - Registers all new standard files.
  - Validates each file as JSON and checks its identifier plus required non-empty collections.
- `tests/test_multi_lang_lint.py`
  - Checks dictionary presence and JSON validity.
  - Checks that CSS properties/functions reference defined value types.
  - Checks JSON syntax metadata and common corrections.
  - Checks that HTML tags and their typed attributes remain subsets of `lint_reference.json`.
  - Checks required HTML attributes, enum candidates, global attributes, allowed prefixes, and void tags.
  - Checks that WordPress block and attribute names remain compatible with `lint_reference.json` and use defined value types.
- `dialogs/schema_help.py`
  - Generates separate Japanese or English Markdown tables directly from `html_tag_schema.json`, `standard_css.json`, and `wordpress_block_schema.json`.
  - The HTML topic shows tag-specific attributes, types, candidate values, required attributes, global attributes, allowed prefixes, and void tags.
  - The CSS topic shows registered properties and value rules, known typo corrections, and accepted units.
  - The WordPress topic shows each core block's known attributes and constraints separately from shared attribute candidates.
  - Missing or malformed schema files show a local table-load message without preventing the rest of Help from opening.
- `dialogs/schema_reference_dialog.py`
  - Shows `HTMLタグ・属性表`, `CSSプロパティ表`, and `WordPressブロックJSON表` as separate tabs in an independent resizable window.
  - Uses a non-modal `Qt.Window`, so the main editor remains enabled and editable while the reference is visible.
  - Places the reference to the right of the main window on first display when space is available, otherwise tries the left side and remains freely movable for Windows snapping.
  - Regenerates all three tables when the application language changes.
- `main.py` / `resources/app_text_ja.json` / `resources/app_text_en.json`
  - Adds `HTML / CSS / WordPress 参考表...` to the Help menu and retains one reusable reference window.
- `tests/test_schema_reference_dialog.py`
  - Checks independent HTML, CSS, and WordPress tabs, modeless operation, Japanese/English updates, visibility, and continued editor availability.
- `README.md` / `README_jp.md`
  - Document the independent schema-generated reference window.
- `regex-pad.spec`
  - No change is needed because the existing specification packages the complete `dictionaries` directory.

Safety boundary:

- This section establishes and validates the dictionaries and exposes them as read-only Help tables.
- It does not yet change user-visible lint findings or automatically rewrite HTML, CSS, JSON, or WordPress block markup.
- The WordPress Help table describes known block attributes, not a guarantee that every displayed content attribute should be written into block-comment JSON. Some attributes are sourced from saved HTML, and the table states this limitation.
- The future HTML lint integration should look up the current tag first, merge its tag-specific attributes with global attributes and allowed prefixes, then validate each value by its declared type.
- Inline `style` values should be passed to `css_lint.py`; CSS parsing rules should not be duplicated inside `html_lint.py`.
- WordPress block-comment JSON should first be syntax-checked by `json_lint.py`, then checked against `wordpress_block_schema.json` by the core-block lint layer.
- Unknown or newly introduced valid web-platform values should initially produce conservative warnings rather than destructive rewrites.

Validation:

- Schema-reference, user-help, and dictionary-focused tests: 18 passed.
- JSON syntax validation: passed for the CSS, JSON, HTML-tag, and WordPress-block dictionaries.
- Ruff: All checks passed.
- Pyright with the project interpreter: 0 errors, 0 warnings, 0 informations.
- Full suite: 353 passed, 1 failed.
- The remaining failure is the existing `tests/test_paragraph_splitter.py::test_split_paragraph_insert_html_code_block` cursor-position mismatch and is unrelated to these dictionaries.

Next implementation stage:

- Extend `json_lint.py` so extracted WordPress comment fragments can be checked with correct source positions.
- Add the schema-backed HTML tag/attribute/value checks without duplicating CSS rules.
- Connect parsed Gutenberg attributes to the WordPress block schema after JSON syntax succeeds.

## Step15-section2 Dictionary-Backed CSS Lint and Reference Table

Date: 2026-10-13

Goal:

- Use one CSS dictionary for standalone stylesheets, HTML inline styles, embedded `<style>` elements, and the Help reference table.
- Report repair locations and likely corrections without rewriting the user's source text.
- Keep the CSS layer separate so HTML lint delegates style values instead of maintaining duplicate CSS rules.

Implementation:

- `search/css_lint.py`
  - Adds `lint_inline_style()` for HTML `style` attributes and `lint_stylesheet()` for complete CSS text.
  - Returns line-aware `CssLintIssue` objects compatible with the existing Grammar Check result dialog.
  - Handles semicolons inside quoted strings and CSS functions, CSS comments, nested blocks such as `@media`, and CSS custom properties.
- `search/html_typo_lint.py`
  - Delegates every HTML `style` attribute and each `<style>` element to the CSS linter.
  - Converts CSS findings into the existing HTML lint message shape while retaining source line numbers.
  - Removes the old one-off `margin:2en` rule because the shared CSS typo dictionary now owns that check.
- `main.py`
  - Dispatches standalone `.css` documents to `lint_stylesheet()` for manual and pre-save Grammar Check.
  - Leaves non-CSS documents on the existing HTML / WordPress lint path.
- `dictionaries/standards/standard_css.json`
  - Expands article-writing coverage for tables, lists, text decoration, wrapping, spacing, object positioning, background attachment, and aspect ratio.
  - Keeps property definitions, value categories, units, functions, at-rules, typo repairs, and full-width punctuation repairs in one data source.
- `dialogs/schema_help.py` / `dialogs/schema_reference_dialog.py`
  - Adds the CSS property table as the middle tab of the independent reference window.
  - Shows registered value rules, typo corrections, and units from the same dictionary used by lint.
- `resources/app_text_ja.json` / `resources/app_text_en.json`
  - Adds localized CSS findings and updates the reference-window action/title to HTML / CSS / WordPress.
- `tests/test_css_lint.py` / `tests/test_html_typo_lint.py` / `tests/test_schema_reference_dialog.py`
  - Covers valid article CSS, property and unit typos, punctuation and delimiter damage, missing colon/semicolon candidates, comments, colors, keywords, ranges, custom properties, nested at-rules, inline styles, embedded stylesheets, standalone `.css` routing, and the CSS reference tab.
- `README.md` / `README_jp.md`
  - Documents CSS Grammar Check coverage and the three-part reference window.

CSS findings:

- Structural syntax:
  - missing or unexpected `{}`
  - unclosed `/* ... */`, quotes, and parentheses
  - full-width CSS punctuation
  - missing `:` and likely missing `;`
- Dictionary-backed semantics:
  - unknown or known-misspelled property names
  - known unit typos and likely missing units
  - invalid registered keywords and hexadecimal colors
  - integer/range checks for selected properties
  - duplicate declarations as information-level findings
  - unknown at-rules

Safety boundary:

- The linter only reports findings and never rewrites CSS or HTML.
- Unknown properties are warnings because browser and plugin ecosystems can introduce valid properties before the bundled dictionary is updated.
- Custom properties such as `--article-color` and values using `var(...)` remain accepted.
- Registered keyword validation is limited to properties whose accepted keyword set is defined by the dictionary.
- Automated Qt offscreen checks establish dialog structure and routing, but do not replace a manual Windows GUI or packaged-EXE display check.

Validation:

- CSS, HTML, schema-reference, dictionary, and main-window focused tests: 136 passed.
- JSON syntax validation: passed for `standard_css.json`, `app_text_ja.json`, and `app_text_en.json`.
- Ruff: All checks passed.
- Pyright with the project interpreter: 0 errors, 0 warnings, 0 informations.
- Full suite: 371 passed, 1 failed.
- The remaining failure is the existing `tests/test_paragraph_splitter.py::test_split_paragraph_insert_html_code_block` cursor-position mismatch. It places the cursor on non-empty `行B`, while the implementation requires a user-created empty line, and is unrelated to CSS lint.
- Qt offscreen smoke checks confirmed standalone `.css` routing plus Grammar Check and CSS reference-tab construction. Manual Windows GUI and packaged-EXE checks remain open.

## Step15-section3 JSON Fragment Lint for WordPress Block Comments

Date: 2026-10-13

Goal:

- Continue the modular lint flow recorded in Step15:
  - HTML detects CSS and delegates to `css_lint.py`.
  - WordPress block parsing detects `{...}` JSON fragments and delegates JSON syntax to `json_lint.py`.
- Preserve source-document positions when linting extracted JSON fragments so Grammar Check can point to the correct line.

Implementation:

- `json_lint.py`
  - Added `JsonFragmentIssue`.
  - Added `lint_json_fragment()` for linting extracted JSON strings.
  - Added source-position mapping from `JSONDecodeError` line/column values back to the original document line and column.
  - Kept `lint_json_file()` and `validate_json_file()` compatible with existing file-level dictionary checks.
- `search/html_typo_lint.py`
  - Replaced direct `json.loads()` error detection in WordPress block-comment attributes with `lint_json_fragment()`.
  - Kept the existing recovery behavior: malformed block JSON still allows block start/end structure tracking to continue.
  - Kept WordPress semantic checks separate from JSON syntax checks; valid JSON that is semantically wrong remains the WordPress block layer's responsibility.
  - Added explicit rejection for non-object WordPress block attributes such as `<!-- wp:paragraph [1, 2] -->`.
- `tests/test_multi_lang_lint.py`
  - Added source-position regression coverage for JSON fragments.
  - Added root-container validation coverage for fragments.
- `tests/test_html_typo_lint.py`
  - Added coverage for non-object WordPress block attributes.
  - Retained invalid-JSON block recovery coverage.

Validation:

- JSON fragment and WordPress block focused tests: 5 passed.
- CSS, HTML typo lint, and multi-language lint focused tests: 92 passed.
- Ruff on changed lint/test files: All checks passed.
- Pyright on changed lint/test files: 0 errors, 0 warnings, 0 informations.

Notes:

- This does not yet implement schema-backed WordPress block attribute semantics from `wordpress_block_schema.json`.
- The next modular lint step is to connect syntactically valid block-comment JSON to the WordPress block schema.

## Step15-section4 CSS Reference Description Column

Date: 2026-10-13

Goal:

- Make the CSS reference table easier to read by adding a short explanation column after `型・使用可能な値`.

Implementation:

- `dialogs/schema_help.py`
  - Added a localized `解説` / `Description` column to the CSS property table.
  - Added the same localized explanation column to the HTML tag/attribute tables.
  - Added the same localized explanation column to the WordPress block JSON tables.
  - Corrected CSS reference formatting so entries using `value_types` display concrete types such as `color / keyword / css_variable` instead of `unknown`.
  - Added localized HTML attribute, WordPress block-attribute, and CSS property descriptions with safe fallback text.
  - Kept support for future dictionary-provided `description`, `description_ja`, and `description_en` fields.
  - Changed WordPress block reference labels from internal `core/...` names to user-facing `wp:...` names.
- `tests/test_schema_reference_dialog.py`
  - Added regression coverage for the new English `Description` headers.
  - Added coverage that HTML, CSS, and WordPress explanations render in the reference text.
  - Added coverage that `value_types` render in the CSS reference text.
- `tests/test_paragraph_splitter.py`
  - Synchronized the paragraph-split HTML insertion regression test with the confirmed policy that insertion is allowed only from a user-created blank line.

Validation:

- `pytest tests/test_schema_reference_dialog.py`: 3 passed.
- `pytest tests/test_schema_reference_dialog.py tests/test_paragraph_splitter.py`: 14 passed.
- `ruff check dialogs/schema_help.py tests/test_schema_reference_dialog.py`: All checks passed.
- `ruff check .`: All checks passed.
- `pyright --pythonpath D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe`: 0 errors, 0 warnings, 0 informations.
- `git diff --check`: passed.
- `pytest`: 376 passed.
- Manual schema generation smoke check confirmed Japanese CSS rows render as:
  - `| プロパティ | 型・使用可能な値 | 解説 |`
  - `| background-color | color / keyword / css_variable | 背景色を指定します。 |`
- Manual schema generation smoke check confirmed WordPress block rows render as `wp:code`, `wp:column`, and related `wp:...` labels.
- Manual schema generation smoke check confirmed Japanese HTML and WordPress rows render as:
  - `| タグ | 属性 | 型・使用可能な値 | 解説 | 必須 |`
  - `| <a> | href | url | リンク先や参照先のURLを指定します。 | いいえ |`
  - `| ブロック | 属性 | 型・使用可能な値 | 解説 |`
  - `| wp:paragraph | content | string | ブロックの編集可能な本文を保存します。 |`

## Step15-section5 CSS Parameter Insert Context Menu

Date: 2026-10-13

Goal:

- Put an easy entry point for inserting `style` and common CSS parameters in the editor right-click menu.

Implementation:

- `main.py`
  - Added a right-click `CSS挿入` / `Insert CSS` submenu.
  - Added fixed insert actions for:
    - `style=""`
    - `color`
    - `background-color`
    - `font-size`
    - `font-weight: bold`
    - `text-align`
    - `margin`
    - `padding`
    - `border`
    - `border-radius`
    - `display: inline-block`
  - Extended `insert_text_at_cursor()` so each action can place the cursor at the editable value position.
- `resources/app_text_ja.json` / `resources/app_text_en.json`
  - Added localized labels for the new context-menu entry and CSS insert actions.
- `tests/test_tag_insert.py`
  - Added coverage that the right-click context menu exposes the `CSS挿入` submenu.
  - Added coverage that `style=""` and `background-color: ;` insert text and leave the cursor in the value position.

Validation:

- `pytest tests/test_tag_insert.py::test_editor_context_menu_has_tag_insert_actions tests/test_tag_insert.py::test_css_insert_context_menu_actions_insert_editable_text tests/test_app_translation.py`: 6 passed.
- `json.tool`: `resources/app_text_ja.json` and `resources/app_text_en.json` passed.
- `ruff check main.py tests/test_tag_insert.py`: All checks passed.

## Step15-section6 PyInstaller JSON Data Bundling

Date: 2026-10-13

Goal:

- Ensure the EXE build includes all existing project JSON files needed by resources, dictionaries, standards, lint, and embedded conversion features.
- Keep runtime/user-generated JSON such as `_internal/autosave` out of the packaged app.

Implementation:

- `regex-pad.spec`
  - Replaced the fixed JSON list with `_project_json_datas()`.
  - Recursively collects project `*.json` files at build time.
  - Preserves each JSON file's relative destination so PyInstaller places them under the one-folder `_internal` contents tree.
  - Excludes generated/cache/runtime folders including `_internal`, `build`, `dist`, `.pytest_cache`, `.ruff_cache`, `.git`, `.vscode`, `.venv`, and `__pycache__`.
- `portable_runtime.py`
  - Added `bundled_base_dir()` for read-only bundled assets.
  - Uses `sys._MEIPASS` when frozen so bundled resources are read from PyInstaller's `_internal` folder.
- `main.py`
  - Loads `resources` and schema-reference standards from `bundled_base_dir()`.
  - Keeps writable runtime data such as autosave and backup under `app_base_dir() / "_internal"`.
- `tests/test_pyinstaller_spec.py`
  - Added coverage that the spec dynamically collects JSON files.
  - Added coverage that current source JSON files such as `resources/app_text_ja.json`, `dictionaries/standards/standard_css.json`, and `config.json` are included.
  - Added coverage that `_internal/...` runtime JSON is excluded.
- `tests/test_portable_runtime.py`
  - Added coverage that frozen runtime reads bundled data from `sys._MEIPASS`.

Validation:

- Spec JSON collection smoke check: 19 project JSON entries collected; `_internal/autosave` entries excluded.
- `pytest tests/test_pyinstaller_spec.py tests/test_portable_runtime.py tests/test_schema_reference_dialog.py tests/test_app_translation.py`: 12 passed.
- `ruff check main.py portable_runtime.py tests/test_pyinstaller_spec.py tests/test_portable_runtime.py`: All checks passed.

## Step15-section7 Context Menu Priority And CSS Insertion Follow-Up

Date: 2026-10-13

User decisions:

- EXE distribution check item 1 is accepted.
- WordPress conversion should stay biased toward Custom HTML blocks when block behavior differs by mode.
- Simple table conversion needs another focused re-check.
- Context menu operation priority is:
  1. Paragraph Split
  2. Insert Tag submenu
  3. CSS Insert
  4. Insert Tag dialog (`Ctrl+Shift+T`)
  5. HTML Escape Transform
- Grammar Check readability improvements should be handled next.
- Unsaved-session recovery has been manually verified on real hardware.
- Documentation cleanup can wait until the main implementation pass is complete.

Implementation:

- Reordered the editor right-click menu to match the requested operation priority.
- Kept CSS insertion in the right-click menu and changed the visible labels to editable snippets such as `color: ;`.
- Changed `style=""` insertion so it is placed inside the nearest opening tag before `>` when the cursor is on or just after that tag.
- Changed CSS declaration insertion so declarations go into an existing nearest `style` value, or create `style="..."` inside the nearest opening tag when needed.
- CSS declarations with an empty value keep the cursor before `;`, for example `color: |;`.
- Renamed the HTML transform menu label to make the escape/unescape purpose clearer.

Validation:

- `pytest tests/test_tag_insert.py::test_editor_context_menu_has_tag_insert_actions tests/test_tag_insert.py::test_css_insert_context_menu_actions_insert_editable_text tests/test_tag_insert.py::test_css_insert_style_attribute_stays_inside_opening_tag_after_tag_cursor tests/test_tag_insert.py::test_css_insert_declaration_uses_existing_style_value tests/test_tag_insert.py::test_css_insert_declaration_creates_style_attribute_in_tag tests/test_html_transform.py::test_html_transform_context_menu_is_available`: 6 passed.
- `json.tool`: `resources/app_text_ja.json` and `resources/app_text_en.json` passed.
- `ruff check main.py tests/test_tag_insert.py tests/test_html_transform.py`: All checks passed.
- `ruff check .`: All checks passed.
- `pyright --pythonpath D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe`: 0 errors, 0 warnings, 0 informations.
- `pytest`: 382 passed.
- `git diff --check`: passed.

## Step15-section8 Markdown Table Recheck And Grammar Readability

Date: 2026-10-13

Goal:

- Re-check simple Markdown table conversion before expanding conversion scope further.
- Make Grammar Check results easier to scan without changing the underlying lint rules.

Implementation:

- `wp_conv_core/wp_converters/wp_markdown_converter.py`
  - Kept literal escaped pipes inside table cells as text, for example `speed \| quality`.
  - Continued accepting web-copied tables where structural pipes are escaped as `\|`.
  - Normalized simple table width by padding short rows with empty cells so generated WordPress table rows stay rectangular.
- `main.py`
  - Sorted Grammar Check rows by severity, then by line number.
  - Added severity labels to each row: error, warning, and note.
  - Added severity counts to the Grammar Check summary and pre-save summary.
- `resources/app_text_ja.json` / `resources/app_text_en.json`
  - Added localized severity labels and summary text.
- Tests
  - Added table conversion regressions for literal escaped pipes and padded short rows.
  - Added Grammar Check assertions for visible severity labels and summary counts.

Validation:

- `pytest tests/test_wordpress_markdown_converter.py tests/test_html_transform.py::test_wordpress_table_transform_converts_selected_markdown_table tests/test_main_window_search.py::test_grammar_check_reports_html_and_wordpress_typos`: 14 passed.
- `json.tool`: `resources/app_text_ja.json` and `resources/app_text_en.json` passed.
- `ruff check main.py wp_conv_core\wp_converters\wp_markdown_converter.py tests\test_wordpress_markdown_converter.py`: All checks passed.
- `ruff check .`: All checks passed.
- `pyright --pythonpath D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe`: 0 errors, 0 warnings, 0 informations.
- `pytest`: 384 passed.
- `git diff --check`: passed.

## Step15-section9 Remaining Work Snapshot

Date: 2026-10-13

Purpose:

- Record the remaining likely work before ending the current implementation session.
- Keep the next session focused on validation and packaging rather than widening features too early.

High priority:

- Rebuild the EXE and distribution ZIP after the JSON bundling and runtime path fixes.
- Verify the rebuilt one-folder EXE on Windows:
  - App launches.
  - Translation resources load.
  - HTML / CSS / WordPress reference tables open.
  - `wp_conv_core` conversion runs inside the packaged app.
  - Writable runtime data such as autosave and backup remains under the portable `_internal` area.
- Paste-check the generated WordPress blocks in Gutenberg:
  - Markdown table to `wp:table`.
  - Markdown list to `wp:list`.
  - Paragraph Split to `wp:html`.
  - Decorated Custom HTML frames.
  - `wp:preformatted` and `wp:group` warning guidance.
- Manually smoke-test right-click CSS insertion in the real GUI:
  - `<div>|text</div>` with `style=""`.
  - `<span style="">|text</span>` with `color: ;`.
  - `<span>|text</span>` with `color: ;`.
  - Existing attributes on the same opening tag.
  - Multi-line tags are not a primary target yet.

Medium priority:

- Use real examples to decide whether Grammar Check needs more readability features:
  - Color-coded rows.
  - Error-only filtering.
  - Folding duplicate warning kinds.
  - Stronger separation between error, warning, and note.
- Re-check additional Markdown table cases only if they appear in actual use:
  - Larger tables.
  - Extra or missing cells.
  - HTML inside cells.
  - Text-table or box-drawing style tables.
  - Cells that appear to contain line breaks.
- Re-check list conversion only if needed:
  - Nested lists.
  - Mixed ordered and unordered lists.
  - Checklist syntax such as `- [ ]`.
  - Multi-line list item descriptions.
- Keep complex or risky conversion biased toward `wp:html` rather than forcing fragile native Gutenberg blocks.

Low priority / final cleanup:

- Create a distribution checklist before office use.
- Update `README.md` and `README_jp.md` after the remaining behavior is stable.
- Gradually replace brittle Japanese literal assertions in tests with translator-key based assertions where useful.
- Ignore old temporary worktrees for future implementation; continue editing in `D:\PC\Python\regex_pad_project`.

Current stopping point:

- Core checks were green after Step15-section8.
- Next best action is packaging and real-GUI / real-WordPress verification.

## Validation Commands

Use the project virtual environment:

```powershell
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m ruff check .
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pyright
"D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe" -m pytest
```

## Project Principles

- Keep the app usable as a high-function one-folder application.
- Do not modify environment variables.
- Do not use the Windows Registry for settings.
- If a setting would normally require Registry usage, store it in a local `.ini` or `.json` file instead.
- Do not require administrator privileges.
- Store settings locally.
- Keep regex usable for non-programmers.
- Do not modify text during search.
- Modify text only when the user explicitly runs Replace or Replace All.
- Keep English and Japanese help aligned in meaning.

## Step15-section10 Packaging Rebuild And Bundle Verification

Date: 2026-10-14

Goal:

- Continue the Step15-section9 packaging work in the main project checkout.
- Rebuild the one-folder EXE after the JSON bundling and runtime-path fixes.
- Confirm the packaged app contains the resources needed by translation, schema/reference dialogs, and portable startup.

Implementation:

- `regex-pad.spec`
  - Added a project JSON collection helper for PyInstaller data files.
  - Included JSON files under `resources`, `dictionaries`, and other project data locations.
  - Ensured a minimal `config.json` exists for packaging when no local config has been created yet.
  - Excluded build/runtime/development folders and files from JSON collection: `build`, `dist`, `_internal`, `.git`, `.vscode`, and `pyrightconfig.json`.
  - Kept the GUI bundle settings aligned with packaging expectations: `console=False` and `upx=False`.
- `build.ps1`
  - Not edited in this section. The existing ChatGPT-updated build script was used as-is.
- Distribution output:
  - Rebuilt `D:\PC\Python\regex_pad_project\dist\regex-pad`.
  - Created `D:\PC\Python\regex_pad_project\dist\regex-pad_step15-section10.zip`.

Validation:

- `pytest tests\test_pyinstaller_spec.py tests\test_portable_runtime.py`: 5 passed.
- `ruff check regex-pad.spec tests\test_pyinstaller_spec.py tests\test_portable_runtime.py`: All checks passed.
- `git diff --check`: passed. Git reported CRLF/LF notices for pre-existing `.gitignore` and `build.ps1` working-copy line endings.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1`: passed.
- Bundle file checks passed:
  - `dist\regex-pad\regex-pad.exe`
  - `dist\regex-pad\_internal\resources\app_text_ja.json`
  - `dist\regex-pad\_internal\resources\regex_help_ja.json`
  - `dist\regex-pad\_internal\dictionaries\standards\standard_css.json`
  - `dist\regex-pad\_internal\dictionaries\standards\wordpress_block_schema.json`
  - `dist\regex-pad\_internal\config.json`
- Development-file exclusion checks passed:
  - `_internal\.git`: absent.
  - `_internal\.vscode`: absent.
  - `_internal\pyrightconfig.json`: absent.
- ZIP content check confirmed:
  - `regex-pad/regex-pad.exe`
  - `regex-pad/_internal/config.json`
  - `regex-pad/_internal/dictionaries/standards/standard_css.json`
  - `regex-pad/_internal/resources/app_text_ja.json`
- Packaged EXE smoke test:
  - `dist\regex-pad\regex-pad.exe` launched successfully and was still running after 5 seconds.
  - The process was then stopped intentionally, so the observed exit code was `-1`.

Remaining:

- Manual GUI operation inside the packaged EXE is still not fully checked:
  - Open HTML / CSS / WordPress reference tables.
  - Run selected Markdown conversion inside the packaged app.
  - Confirm writable autosave/backup behavior from normal user operation.
- Real Gutenberg paste acceptance is still unverified:
  - Markdown table to `wp:table`.
  - Markdown list to `wp:list`.
  - Paragraph Split to `wp:html`.
  - Decorated Custom HTML frames.
  - `wp:preformatted` and `wp:group` warning guidance.

## Step15-section11 Find Replace Input Drag Scroll Recovery

Date: 2026-10-17

Goal:

- Investigate the report that the Find/Replace input text appears to disappear after a large mouse drag outside the compact input field.
- Review the supplied `regex_input_scroll_fix.zip` without blindly overwriting existing files.

Investigation:

- The supplied ZIP contained `dialogs/regex_input_edit.py`, `tests/test_find_replace_dialog.py`, and `tests/test_regex_input_scroll.py`.
- SHA-256 comparison confirmed that all three executable/test files exactly match the current files in `D:\PC\Python\regex_pad_project`.
- The matching implementation was already committed as `a093d29` (`fix: Fixed Dialog focus error`) at 2026-10-17 13:29 JST, so the ZIP was not copied over the project again.
- The ZIP `README.md` differs from the project README, but it is an explanatory document rather than a runtime file and was left unchanged.

Implementation already present:

- `dialogs/regex_input_edit.py`
  - Replaced the old fixed `lineSpacing * visible_lines + 12` field-height calculation with a calculation based on the actual font height, document margins, frame width, and a small rounding allowance.
  - Added `scrollContentsBy()` recovery that resets the vertical scrollbar only when `firstVisibleBlock()` has become invalid after selection autoscrolling.
  - Reuses the same validity check during queued visible-text refreshes.
  - Leaves normal multi-line scrolling intact when the first visible block is valid.
- `tests/test_regex_input_scroll.py`
  - Covers single-line input, large pointer movement outside the viewport, legacy tight-height recovery, and normal multi-line scrolling.
- `tests/test_find_replace_dialog.py`
  - Updates the height expectation to account for document margins and the real input frame.

Validation performed on 2026-10-17:

- `pytest tests\test_find_replace_dialog.py tests\test_regex_input_scroll.py tests\test_regex_input_display_flow.py tests\test_main_window_search.py`: 70 passed.
- `ruff check dialogs/regex_input_edit.py tests/test_find_replace_dialog.py tests/test_regex_input_scroll.py tests/test_regex_input_display_flow.py tests/test_main_window_search.py`: All checks passed.
- `pyright --pythonpath "D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe"`: 0 errors, 0 warnings, 0 informations.
- Full `pytest`: 389 passed.

Remaining manual acceptance:

- On Windows 11, enter short text, a long regular expression, and multi-line text in both the Find and Replace fields.
- Drag each selection beyond all four edges of the field, then confirm the text remains visible and further typing still works.
- Repeat after Replace All while regular-expression highlighting is enabled.

## Step15-section12 Recommended WordPress Background Color Menu

Date: 2026-10-20

Goal:

- Provide gentle background-color choices for WordPress article HTML, because colors copied directly from Paint can render much darker in the published page.
- Keep ordinary CSS input available without forcing a preset selection.

Implementation:

- The editor context menu action `CSS挿入 > background-color: ;` now opens a color-swatch popup at the inserted value position.
- The popup offers these recommended values:
  - Rose: `#FFE4E4`
  - Pale yellow: `#FFFBDE`
  - Pale yellow-green: `#F4FFDD`
  - Pale green: `#E2FFDF`
  - Blue-leaning pale green: `#DCFFF2`
  - Light cyan: `#DBFFFE`
  - Pale blue: `#D8E8FF`
  - Lavender: `#E8DDFF`
  - Pink: `#FCDCFF`
- Choosing a preset replaces only the empty `background-color` value and keeps its terminating semicolon.
- Pressing `Esc` closes the popup without changing `background-color: ;`, leaving the cursor in the value position for manual CSS input.
- Updated `README.md` and `README_jp.md` with this workflow.

Validation:

- Added tests for the nine color values and color-swatch icons, replacing a value inside an existing `style` attribute, and Esc closing the popup while retaining manual input position.
- Focused `pytest tests/test_tag_insert.py`: 66 passed.
- `ruff check .`: All checks passed.
- `pyright --pythonpath "D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe"`: 0 errors, 0 warnings, 0 informations.
- Full `pytest`: 391 passed.

Remaining manual acceptance:

- In the Windows GUI, right-click the editor and choose `CSS挿入 > background-color: ;`.
- Confirm the popup appears beneath the cursor, a selected color is inserted correctly, and Esc permits a custom value such as `rgb(240, 248, 255)`.

## Step15-section13 Text Color Presets And Context Menu

Date: 2026-10-20

Goal:

- Add the same color-selection workflow to `color: ;` and the existing inline text-color actions.
- Preserve the fast `Ctrl+Alt+1` through `Ctrl+Alt+7` workflow for selected text.

Implementation:

- `CSS挿入 > color: ;` now opens a color-swatch popup with the seven colors already used by inline text-color shortcuts:
  - Red: `#d00000`
  - Blue: `#0057b8`
  - Green: `#008a3d`
  - Orange: `#c85a00`
  - Purple: `#7a3db8`
  - Pink: `#c2185b`
  - Gray: `#555555`
- A new right-click `文字色` / `Text Color` submenu exposes the same existing inline-color actions with color swatches.
- The existing `Ctrl+Alt+1` through `Ctrl+Alt+7` shortcuts remain direct selection-wrap actions; no shortcut behavior was replaced.
- Choosing a `color: ;` preset replaces only the CSS value and retains the ending semicolon.
- Esc closes the `color: ;` popup while keeping the cursor ready for a custom CSS value.
- Added the `action.inline_color_menu` translation key in both application-language JSON files and updated both READMEs.

Validation:

- Added tests for the Text Color context submenu, the seven color values/icons, CSS value replacement, Esc manual-input behavior, and retained `Ctrl+Alt+2` shortcut assignment.
- `pytest tests/test_tag_insert.py tests/test_app_translation.py`: 72 passed.
- Both translation JSON files passed `python -m json.tool` parsing.
- `ruff check .`: All checks passed.
- `pyright --pythonpath "D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe"`: 0 errors, 0 warnings, 0 informations.
- Full `pytest`: 393 passed.

Remaining manual acceptance:

- In the Windows GUI, confirm `CSS挿入 > color: ;` shows the seven text colors, Esc leaves `color: ;` editable, and the right-click `文字色` submenu wraps selected text correctly.
- Confirm the color-swatch popups remain readable with the editor's light, dark, and custom display themes.

## Step15-section14 Editable Color Presets And List Frame Conversion

Date: 2026-10-20

Goal:

- Move text-color and background-color preset names and values out of `main.py` and into an editable JSON file.
- Keep the same JSON editable beside the packaged EXE.
- Add an alternative conversion for sites whose WordPress theme hides bullets or ordered-list markers.

Implementation:

- Added `color_presets.json` at the project root and a bundled default at `resources/color_presets.json`.
- Added `settings/color_presets.py`:
  - Loads text and background color names and CSS values from JSON.
  - Loads text-color shortcut assignments from the same JSON.
  - Copies the bundled default safely beside the application when the editable file is missing.
  - Leaves malformed editable JSON untouched and falls back to the bundled default for that launch.
- Updated `main.py` so `color: ;`, `background-color: ;`, the Text Color submenu, and `Ctrl+Alt` inline-color actions all use the loaded catalog.
- Added `段落分割 > リストを枠囲みに変換` / `Paragraph Split > List to Framed Block`.
- The new conversion accepts a selected Markdown list or existing WordPress list block and emits one `wp:html` frame.
- Unordered and ordered markers are emitted as visible text (`・` or `1.`, `2.`, and so on), not as theme-dependent `ul` / `ol` markers.
- The converted frame uses the current frame alignment, outer spacing, background color, and text color settings.
- Kept the existing WordPress `wp:list` conversion action unchanged.
- The PyInstaller spec's existing project-JSON collection includes both color-preset JSON files; packaging tests now assert both destinations explicitly.
- Updated `README.md` and `README_jp.md` with the post-packaging edit workflow and list-frame behavior.

Validation:

- Focused tests cover JSON loading/copy/fallback/override, both list input forms, the main-window action, menu placement, translations, and PyInstaller data collection.
- Focused `pytest`: 110 passed.
- Focused Ruff checks: All checks passed.
- `pyright --pythonpath "D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe"`: 0 errors, 0 warnings, 0 informations.
- Full `pytest` in `D:\PC\Python\regex_pad_project`: 401 passed.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1`: passed.
- Packaged color-preset checks passed:
  - `dist\regex-pad\_internal\resources\color_presets.json` is present.
  - Starting `dist\regex-pad\regex-pad.exe` created editable `dist\regex-pad\color_presets.json`.
  - The initial editable file matched the bundled default by SHA-256 and contained 7 text colors and 9 background colors.
  - The packaged EXE remained running after 5 seconds and was stopped intentionally after the smoke check.

Remaining manual acceptance:

- In the Windows GUI, edit text/background names, CSS values, and a text shortcut in `color_presets.json`; restart and confirm all related menus use the new values.
- In the packaged GUI, confirm both swatch popups and the Text Color submenu render the configured names and colors correctly.
- Paste a converted unordered and ordered framed list into the workplace Gutenberg environment and confirm its markers remain visible after save/reload.

## Step15-section15 HTML / WordPress Linter Gap Repair And Algorithm Audit

Date: 2026-10-22

Goal:

- Reproduce the supplied false negatives and the self-closing block false positive before changing the implementation.
- Repair the reported P0 cases incrementally, audit stack handling, and propagate the verified changes from worktree `b960` to `D:\PC\Python\regex_pad_project`.

Implementation:

- `search/html_typo_lint.py`:
  - Reports unmatched inline closing tags, including the editor's `u` formatting tag, and checks `h1` through `h6` pairs.
  - Checks nested paragraphs/anchors, block elements inside paragraphs, and the direct list parent of `li`.
  - Recognizes self-closing WP comments separately from opening/closing comments. Their JSON is still checked, but they never enter the open-block stack or pair counts.
  - Checks direct `list-item` / `list` and `column` / `columns` relationships, allowed children of lists/columns, and disallowed child blocks of paragraphs.
  - Requires one real paragraph/heading root in the respective blocks, with no sibling root elements or outside body text. Comments and escaped code cannot satisfy this check.
  - Checks selected paragraph typography/color properties against block-comment `style`, and checks the expected classes for declared text/background colors and font-size presets.
  - Keeps inline-child formatting separate from paragraph-root formatting and skips consistency guesses when CSS syntax is broken.
- `search/css_lint.py`: exposes declaration values through the existing comment/quote/parenthesis tokenizer, avoiding a second naive CSS splitter.
- Added six matching JA/EN message keys and updated both READMEs.
- Added 82 regression cases covering the reported failures, valid controls, malformed JSON recovery, source lines, and translation formatting.

Algorithm audit:

1. Counts are only supporting diagnostics. Actual tag/block stacks detect ordering errors even when opening and closing counts match.
2. The HTML tag inventory is collected once for document-wide pairing/content checks. Block-boundary checks slice the same inventory by original source position; paragraph/heading roots are parsed separately once per closed block and shared by shape/attribute checks.
3. Document-wide HTML pairing now runs even when WP comments are present, so HTML outside blocks is not omitted. Block-local checks still catch tags that cross WP boundaries.
4. A wrong WP closing comment is looked up before the stack is modified. This recovery now also applies to ignored/suppressed body-range collection.
5. Inline entries retain their enclosing boundary depth. Closing a paragraph no longer consumes an anchor that validly surrounds the whole paragraph.
6. Nested `code` openings retain their stack entries after reporting, so later nested siblings remain detectable.
7. Identical severity/key/line/value findings from document and nested-block checks are displayed once. Results remain ordered by original line, with enclosing WP diagnostics retained first on the same line.
8. The checks read the source without rewriting it. A strict five-phase UI or complete HTML/WP tree/schema validator is not implemented by this repair; the independent checks share source positions and apply syntax guards before consistency checks.

Validation in worktree `b960`:

- Reproduction before implementation: 45 failing cases in the first test batch, including the valid block-link false positive; existing focused baseline: 71 passed.
- Focused HTML/CSS/translation pytest: 167 passed.
- Full pytest: 483 passed.
- Ruff: All checks passed.
- Pyright with the specified Python interpreter: 0 errors, 0 warnings, 0 informations.
- Both translation JSON files passed `python -m json.tool`; `git diff --check` passed.

Canonical checkout propagation and validation:

- Confirmed both checkouts were at `eedb7a9`, their AGENTS instructions matched after newline normalization, and all eight destination files still matched their committed versions before copying.
- Propagated exactly the eight changed source/test/resource/documentation files using verified temporary writes and atomic replacement. No settings or other files were copied.
- Full pytest in `D:\PC\Python\regex_pad_project`: 483 passed.
- Canonical Ruff: All checks passed. Canonical Pyright: 0 errors, 0 warnings, 0 informations.
- Canonical translation JSON parsing and `git diff --check`: passed.
- Verified source/destination SHA-256 equality for all eight files after propagation.

Scope and remaining acceptance:

- This is targeted paste-safety validation, not browser DOM recovery or regeneration of Gutenberg's complete save output.
- HTML content-model rules and WP parent/allowed-child rules are limited to those listed above. Paragraph consistency covers selected typography/color styles and declared preset classes; arbitrary classes, theme CSS, spacing/borders and all plugin-specific serialization are not inferred.
- A full schema-driven dual-tree/phase refactor remains a separate follow-up. It must preserve the regression cases added here.
- Windows GUI interaction, actual workplace Gutenberg paste/save/reload, and a rebuilt packaged EXE have not been tested in this change.

## Step15-section16 Search Exclusion Field

Date: 2026-10-23

- Added an Exclude / 除外条件 input to Find / Replace. An empty input preserves existing behavior.
- Exclusion matches protect their character ranges; any overlapping search match is skipped.
- Exclusions use the search regex and case settings. Whole-word matching applies only to the search pattern. Zero-width exclusion matches protect no characters.
- Regex alternatives use `|`: search `\n` with exclusion `<br><br>\n|>\n` to preserve tag-ending newlines. A leading `-` is literal text, not an exclusion operator.
- Applied exclusions to forward/backward navigation, highlighting, current/all/marked replacement and previews, inside the existing selected/visible scope.
- Current and marked replacement validate exclusions against the original scope. Preview line rendering reuses the filtered original matches, preserving exclusions that span multiple lines.
- Invalid exclusion regexes receive a labeled lint error and prevent replacement. Replacement group numbers and escape handling are preserved.
- Added regression coverage and updated both translation files and READMEs. Inputs follow the existing dialog lifetime and are not persisted across restarts.

Validation in worktree `f79c`:

- Full pytest: 526 passed, using the specified Python 3.12 interpreter and Qt offscreen platform.
- Ruff: All checks passed.
- Pyright with the specified interpreter: 0 errors, 0 warnings, 0 informations.
- Both translation JSON files parsed successfully; translation key parity and `git diff --check` passed.
- Rendered and inspected the Japanese dialog offscreen with Meiryo: the new field fits the layout. This is automated rendering, not a manual Windows GUI interaction check.

Remaining acceptance:

- Physical keyboard/mouse operation in the running Windows application and a rebuilt packaged EXE have not been checked.

Canonical propagation follow-up (2026-10-23):

- The user established canonical propagation as the default completion rule. Added it to `AGENTS.md` in both checkouts and recorded a persistent preference note.
- Confirmed both checkouts started at `3ce12fbd3cec27e78142085e568e5e3c7087d76f`; the canonical checkout was clean and all 12 destination files matched the worktree base after newline normalization.
- Propagation includes the 11 exclusion-feature files and `AGENTS.md`; no settings, Git metadata, backups, or build output are included.
- Transferred the 12 files using verified temporary writes and atomic replacement; all 12 source/destination SHA-256 values matched.
- Canonical full pytest: 526 passed. Canonical Ruff: All checks passed. Canonical Pyright with the specified interpreter: 0 errors, 0 warnings, 0 informations. Canonical `git diff --check`: passed.
- Source propagation is complete. Restart an already-running source application to load the added exclusion field. EXE rebuilding and physical Windows GUI acceptance remain unperformed.

Input order follow-up (2026-10-23):

- Reordered Find / Replace inputs to Find text, Exclude, Replace with, and aligned input creation order for keyboard focus navigation.
- Changed the Japanese exclusion label to `検索時、除外条件` and updated the existing label assertion and both READMEs.
- Validated in both worktree and canonical checkout: related pytest 85 passed; Ruff passed; Pyright reported 0 errors, 0 warnings, 0 informations.
- Verified input positions and focus-chain order automatically, and inspected an offscreen Japanese dialog rendering. Propagated all six changed files to the canonical project with SHA-256 equality. Physical Windows interaction and an EXE rebuild remain unperformed.

## Step15-section17 Orphan HTML Attribute Continuations

Date: 2026-10-23

Goal and evidence:

- Follow the user-supplied `FIX_LINTER_STEPS.md` using the qualification article's original and official repaired source as a structural regression pair.
- Before implementation, direct lint returned zero findings for both articles. The original contains 11 completed `<div>` openers followed by orphan `style` text; three also contain live `<br>` tokens in the attempted attribute continuation.
- Preserve editorial wording, heading choices, CSS spacing, final body breaks and other design differences. No source rewriting or Gutenberg regeneration was added.

Implementation:

- Extended the existing `HtmlTypoLintParser`, reusing its source positions, suppression ranges and cached HTML attribute dictionary/prefix recognition.
- Track only the immediate body prefix following a parser-confirmed complete opening tag. The parser consumes valid multiline opening tags and their quoted `>` values before this check runs.
- Warn on a known attribute assignment followed by an extra raw `>`, or an attribute-only continuation on following lines. A lone inline attribute example or ordinary prose is not sufficient.
- Report `html_attribute_outside_opening_tag` for orphan attributes, `unexpected_html_tag_close_delimiter` for a contextual standalone `>` without an unfinished start tag, and `malformed_html_attribute_continuation` when live `<br>` tokens interrupt the attempted attribute list.
- Emit one root-cause warning per malformed prefix, on the first attribute line. Do not duplicate warnings for every attribute, break or extra delimiter.
- Comments, code/preformatted/raw-text regions and the existing contaminated-separator suppression remain boundaries. Suppressed separator `<code>` tokens do not poison continuation state in subsequent blocks.
- Added aligned JA/EN repair messages, updated both READMEs, and retained exact copies of both supplied files under `tests/fixtures/linter_cases/qualification_article_20261023/` with a provenance/expectation note.
- Added focused positive/negative controls and automated MainWindow Grammar Check integration checks for both whole articles, including source preservation and highlighted lines.

Measured article results after implementation:

- Original: 11 warnings, consisting of eight `html_attribute_outside_opening_tag` and three `malformed_html_attribute_continuation` findings.
- Warning lines: 22, 82, 109, 127, 151, 211, 288, 361, 430, 496, 523. Continuation-with-break warnings are on lines 109, 127 and 523.
- Official repaired article: zero findings for the new family; the direct run also currently has zero total findings. Regression expectations target the new family rather than unrelated future rules.

Validation:

- Test-first reproduction: 58 expected failures and 176 passing HTML lint cases. A later focused case separately reproduced and fixed separator-suppression state leaking into the next block.
- Focused HTML/CSS/translation/MainWindow pytest: 316 passed.
- Full worktree pytest after the separator-state repair: 622 passed. Both translation files passed `python -m json.tool`; translation-key parity and `git diff --check` passed.
- Ruff: All checks passed after fixing test import spacing and a set-literal lint finding. Pyright with the specified interpreter: 0 errors, 0 warnings, 0 informations.

Acceptance boundary:

- The original files and `FIX_LINTER_STEPS.md` are read-only inputs; the user's `.gitignore` edit and unrelated changes are preserved.
- Actual WordPress paste/save/reload, physical Windows GUI interaction and a rebuilt packaged EXE have not been exercised. The repaired source is user-supplied; automated lint is not evidence of live WordPress acceptance.

Canonical propagation and validation:

- Before transfer, all eight existing destination files matched the inspected canonical snapshot; the three new fixture paths were absent. Copied exactly these 11 files using verified temporary writes and atomic replacement.
- Canonical `pytest tests/test_html_typo_lint.py`: 243 passed. Canonical full pytest: 622 passed.
- Canonical Ruff: All checks passed. Canonical Pyright with the specified interpreter: 0 errors, 0 warnings, 0 informations.
- Both canonical translation JSON files passed `python -m json.tool`; `git diff --check` passed in both checkouts.
- Direct canonical runs on the actual supplied articles reproduced the measured 11 / 0 results. Both originals still match their regression copies byte-for-byte.
- Final source/destination SHA-256 equality was verified for all 11 files, including this completed implementation record. Source propagation is complete; restart a running source application before using F7.

## Step15-section18 Standard WordPress Preview And Runtime Feedback

Date: 2026-10-23

User decisions:

- Use actual WordPress core and its standard theme as the `normal` baseline, without copying a restricted production site's theme/CSS/plugins.
- Use the default browser for display. The user explicitly selected first-use preparation of an optional WordPress environment; existing local WordPress/PHP/MySQL are not prerequisites.
- Incorporate WordPress execution feedback into checking, while preserving structural lint that the rendering engine does not report.

Implementation:

- Added View > WordPress Preview (normal), Ctrl+Alt+P, and a Stop action. Send an unchanged unsaved editor snapshot to a dedicated child process; show the resulting local URL through QDesktopServices.
- Added `preview/wordpress_runtime.py`: optional first-use preparation under `runtime/wordpress-preview`, official Playground 3.1.60 packages, PHP 8.3 only, official WordPress core ZIP, and SQLite integration. No global Python/npm install or administrator rights.
- Reuse compatible Node (24.18+). If unavailable on Windows, prepare portable Node LTS and check its ZIP against the official SHA-256 list. npm packages use local prefix/cache and ignore install scripts.
- Added `resources/wordpress_preview/bridge.mjs`, using official `bootWordPressAndRequestHandler` and PHP.wasm. WordPress code runs in its virtual filesystem. Create/update one in-memory local preview post; use the real front-end template, content filters, dynamic blocks and standard theme styles. Source text is passed as Base64-encoded JSON data, never evaluated as PHP.
- Bind HTTP only to 127.0.0.1, reject foreign Host headers and HTTP writes; editor updates use private stdin. Serialize engine access, reject foreign browser URLs and stale replies, and stop owned processes on Stop/editor close.
- First preparation runs in a cancellable QThread; the bridge runs in QProcess. Failed setup, runtime failures and browser-open failures are reported without crashing the editor.
- Display WordPress HTTP/PHP execution feedback separately in Grammar Check, with no fabricated article-line mapping. Retain the existing line-aware diagnostics; clear feedback when the document/result changes and support copying it even with zero static findings.
- Exclude optional runtime JSON from the PyInstaller data collector and ignore the runtime folder in Git. Standard app packaging does not include WordPress/npm/Node data.
- Updated JA/EN messages, both READMEs, and added `python -m preview.verify_wordpress_preview` for opt-in real-engine integration checks. Normal pytest never downloads or boots WordPress.

Evidence and validation in the worktree:

- Real engine: WordPress 7.1.3, Twenty Twenty-Five, PHP 8.3. The dynamic core/latest-posts block was rendered, not merely copied as static source.
- Original qualification article: HTTP 200, no runtime warnings, 11 static lint findings. Repaired article: HTTP 200, no runtime warnings, zero static findings. This demonstrates why runtime feedback cannot replace the structural linter.
- Actual MainWindow action -> setup thread -> QProcess -> real WordPress -> 11 static findings plus HTTP feedback passed offscreen, with the browser-open call captured rather than physically opening the default browser. Editor source stayed unchanged and the owned process stopped cleanly.
- Portable Node LTS 24.22.1 was downloaded, SHA-256 verified, extracted and executed successfully; the real-engine verification also passed under it.
- Focused preview/packaging/translation pytest: 21 passed. Full worktree pytest: 635 passed. Ruff passed; Pyright with the specified interpreter: 0 errors, 0 warnings, 0 informations.
- Measured optional runtime: about 126 MB with an existing compatible Node; the tested portable Node ZIP plus extraction add about 138 MB. The discarded design using the complete Playground CLI would include all PHP versions; it is not the implementation shipped by this feature.

Scope and acceptance boundary:

- Normal means standard core/theme content rendering, with standard demo data. It does not reproduce production plugins/data, Gutenberg editor save-markup validation, or PHP-side external API/oEmbed networking. WordPress cron/automatic updates and outbound HTTP are disabled for the offline preview baseline. Remote article images still require browser network access.
- Existing settings, unrelated worktree edits and the canonical .gitignore additions must remain intact. Transfer only this feature's manifest; prepare optional runtime locally, rather than copying developer build output.
- Physical Windows default-browser interaction and a rebuilt packaged EXE remain unperformed acceptance steps. Cached operation and real HTTP rendering are tested separately from that manual acceptance.

Canonical propagation and validation:

- Preflight confirmed the nine existing destination files matched the captured canonical SHA-256 values and the six new paths were absent. Transferred only these 15 feature files using verified temporary writes and atomic replacement; merged one runtime ignore rule while preserving every existing canonical `.gitignore` byte.
- Canonical full pytest completed successfully: 635 passed. Ruff: All checks passed. Pyright with the specified interpreter: 0 errors, 0 warnings, 0 informations. Translation JSON parsing, JavaScript syntax and `git diff --check` passed.
- Prepared the optional environment directly under canonical `runtime/wordpress-preview`, without copying worktree build output. Real-engine verification passed with WordPress 7.1.3 and Twenty Twenty-Five: dynamic latest-posts rendered, HTTP writes/foreign hosts rejected, original article 11 static findings versus repaired article zero, both HTTP 200 with no runtime warnings. Shutdown made the local URL inaccessible.
- Final source/canonical SHA-256 equality was verified for all 15 feature files, including this completed record. The canonical `.gitignore` differs only by its intended added rule from its captured version. Source propagation is complete; restart a running source application to load the new View menu actions. EXE rebuilding and physical default-browser acceptance remain unperformed.

## Step15-section19 Bundle WordPress Preview In EXE Distributions

Date: 2026-10-23

User request: update the spec and build script so EXE distributions can include the WordPress preview environment. The existing script is `build.ps1` (the request spelled it `build.sp1`).

Implementation:

- Default `build.ps1` prepares official preview dependencies plus a portable Node, independent of an installed build-machine Node. `-SkipWordPressRuntime` retains first-use setup for smaller distributions. Restore temporary build environment settings afterwards.
- `regex-pad.spec` explicitly collects the prepared WordPress/standard theme ZIP, SQLite integration, PHP.wasm/module dependencies, portable Node executable and license files under `_internal/runtime/wordpress-preview`. Exclude npm/download caches, logs, Node ZIPs and Node's npm tooling. Direct spec builds fail clearly if runtime preparation is missing; `REGEXPAD_SKIP_WORDPRESS_RUNTIME=1` explicitly opts out.
- Added `preview/package_runtime.py` for preparation, strict data selection and post-build checks. Node must start and meet the supported version; missing runtime components abort the build.
- The app prefers complete bundled runtime data via `default_runtime_root`; lightweight builds keep the adjacent writable runtime setup path. Source behavior is unchanged.
- Build post-checks require the preview bridge and validate the bundled runtime. Resource replacement verifies its target stays under project dist. Removed the old trailing signature comment block when editing the PowerShell script; no signing certificate was used.
- Updated both READMEs and packaging regressions for bundle contents, missing dependencies, portable Node preparation and frozen-path resolution. Distribute the complete onedir folder, including `_internal`.

Worktree validation:

- Full pytest: 640 passed. Ruff passed. Pyright with the specified interpreter: 0 errors, 0 warnings, 0 informations. PowerShell AST parsing and `git diff --check` passed.
- Ran the actual default `build.ps1` through PyInstaller 6.22.2 successfully. Build post-checks validated 234 WordPress runtime files, including executable portable Node. The bundled runtime occupies about 189 MiB; the complete tested onedir distribution is about 303 MiB.
- Real-engine integration used the distribution's own bridge, WordPress ZIP, SQLite, PHP.wasm modules and Node: WordPress 7.1.3 / Twenty Twenty-Five, dynamic latest-posts rendering, HTTP/Host restrictions, both article regressions and shutdown all passed.
- Started the packaged EXE offscreen for five seconds; it stayed running and initialized its adjacent runtime/data folders, then the owned smoke process was terminated. Physical GUI/menu/default-browser interaction and acceptance on a separate clean PC remain unperformed. The packaged real-engine check is separate from GUI acceptance.

Canonical propagation and validation:

- Preflight checked all eight existing destination files against captured SHA-256 values and confirmed the new helper path was absent. Propagated only this request's nine source/test/documentation files by verified temporary writes and atomic replacement, preserving unrelated changes.
- Canonical full pytest: 640 passed. Ruff passed; Pyright with the specified interpreter: 0 errors, 0 warnings, 0 informations. PowerShell syntax parsing and `git diff --check` passed.
- Prepared canonical portable Node directly from the official download rather than copying developer runtime/build output. `python -m preview.package_runtime` validated all 234 selected runtime files, making the canonical source ready for the default build and direct spec collection.
- Final SHA-256 equality was verified for all nine transferred files, including this record. Actual EXE build/startup and packaged-runtime integration were performed in the worktree. The existing canonical dist/EXE was not replaced; running canonical `build.ps1` creates its updated distribution.

## Step15-section20 Read-only Gutenberg Recovery And Save Analysis

Date: 2026-10-24

Request: follow the canonical `CODE_ANALYSIS_POLICY.md`, investigate visual-editor validation, Attempt recovery, Resolve/HTML conversion, disappearing ordinary text, whitespace/br changes and effects on later blocks. Never modify WordPress Core, Gutenberg, the existing preview runtime, or RegexPad application code for analysis.

Deliverables:

- Added `GUTENBERG_BEHAVIOR_REPORT.md` and the explicit `analysis_cases/` artifact manifest: nine synthetic before/manual-fixed/after cases, database snapshots, editor block trees, phase diffs, case notes, screenshots, source references and reproducible external probes.
- Used the existing WordPress 7.1.3 / PHP 8.3 / Twenty Twenty-Five archives in a separate memory-only installation. Actual Chrome WordPress UI operations and Save draft were observed. No production site was accessed or changed, no Gutenberg plugin or theme update was performed.
- Confirmed wrong heading roots can produce empty extracted content and erase ordinary text on recovery; missing block closers absorb later paragraph/heading blocks whose content is then omitted by paragraph save; stray closers turn the remainder into Classic content and invoke autop; editing RichText can collapse source newlines to spaces while untouched custom HTML remains unchanged.
- Distinguished PHP read-side Block Hooks transformations from database values and client-side serialization. Confirmed that normal recovery with correct boundaries preserves the tested later siblings. Existing nested core/html is valid in this fixed version; automatic double-wrapping from ordinary HTML conversion was not reproduced.
- No linter rules were changed. Recorded existing findings and manual fixes, including the fact that a recovered output can have zero lint findings after text has already disappeared. Full real-site/plugin/version/permission coverage is not claimed.

Worktree validation:

- Nine actual editor cases; 79 saved-evidence/source-reference checks passed. Five assertions against the unmodified JS delimiter parser and six independent PHP read-pipeline assertions passed.
- Full pytest: 640 passed. Ruff passed; Pyright with the specified interpreter: 0 errors, 0 warnings, 0 informations. Resource/dictionary/analysis JSON parsing and Node syntax checks passed.
- All 29 extracted reference files match their ZIP originals byte-for-byte. Existing preview runtime: all 2,281 files unchanged by SHA-256. Owned analysis server stopped and its origin was confirmed unreachable.

Canonical propagation and validation:

- Preflight confirmed canonical SCRIPT_STEP.md matched the worktree base after newline normalization and all new destination paths were absent. Transferred only the 263-file manifest using verified temporary writes and atomic replacement: report, this record and dedicated analysis artifacts. No `.git`, settings, build output or existing runtime content was copied.
- Canonical full pytest: 640 passed. Ruff: All checks passed. Pyright: 0 errors, 0 warnings, 0 informations. Canonical evidence verification: 79 checks passed; resource/dictionary/analysis JSON: 109 files parsed. Node syntax, parser/PHP probes and both git diff checks passed.
- All 263 transferred files, including the final report and this record, match by SHA-256. Canonical `.gitignore` remains byte-identical to the captured preflight value; the original policy matches its byte-preserving snapshot. Both source trees contain no application/linter/Core changes from this analysis.
- Actual local WordPress editor recovery/save/reload was performed for the documented cases. EXE rebuild, production-site acceptance, other versions/plugins/permissions, exhaustive block-definition coverage and autosave/revision behavior remain outside this validation.

## Step15-section21 Gutenberg Content-Loss Prevention Lint

Date: 2026-10-24

Request: implement `LINTER_MODIFICATION_POLICY.md` using the existing linter, regression tests and the fixed WordPress 7.1.3 analysis. Prioritize text preservation over matching Gutenberg validity or recovery output.

Implementation:

- Added repair-aware block span metadata (pair/parent IDs, depth, positions, opening/closing lines and self-closing status) to the existing WP stack. Missing/orphan/mismatched closers and invalid known core parent/child relationships are Error; missing closers include conservative affected-line candidates and explicit recovery/save risks in JA/EN.
- Added core child checks for paragraph, heading, separator, spacer and image. Checked paragraph/heading/list/list-item root shapes and actual HTML repair lines. Nested wp:html remains a portability Warning; RichText newline and br spelling differences alone remain accepted.
- Added HTML crossing a WP closing boundary as Error, while preserving valid container wrappers. Mask child HTML for parent shape/attribute checks, suppress the equivalent missing-tag diagnostic and repeated-list-item parent cascade, and keep independent parent shape/CSS/JSON issues and separator suppression.
- Accept multiline block JSON comments and retain structural checks after JSON errors. CSS/JSON validation implementations and reference dictionaries are unchanged.
- MainWindow change is limited to the grammar-save gate: Info-only findings do not request confirmation; Error/Warning continue using the existing default-cancel confirmation. The linter does not rewrite text.
- Added seven minimal broken/fixed/control fixture groups and a dedicated risk regression module. Original WordPress recovered/saved/reloaded observations are separate data, never a correct-text reference. Updated the specific old assertions affected by new diagnostic keys, range values and Error priority; removed no tests.
- Updated both READMEs and added `LINTER_MODIFICATION_REPORT.md`, a preflight hash record, an intended-file manifest and a verification record. Historical analysis data remains intact.

Validation:

- Before modification: full pytest 640 passed, Ruff passed, Pyright 0 errors/warnings/informations, 109 JSON files parsed.
- Focused HTML/Gutenberg/CSS/reference/translation/MainWindow selection: 369 passed. Full worktree pytest: 682 passed (42 additional cases). Source/reference JSON parsing and diff checks passed.
- Original analysis evidence verification: 79 checks passed. Existing preview runtime: 2,281 files unchanged by SHA-256. No WordPress Core/Gutenberg/Preview, Find/Replace, Backup, editor rendering, tag insertion, Markdown conversion or build changes.
- Canonical focused pytest: 369 passed. Canonical full pytest: 679 passed / 3 failed. Ruff passed; Pyright 0 errors/warnings/informations; JSON parsing: 112 files successful.
- The three full-suite failures are unchanged frame-insertion tests expecting 2px borders while the existing canonical WordPress snippet dictionary uses 3px. Reproduced all three with pre-modification HEAD main/linter modules and the existing dictionary in a read-only comparison. Policy section 48 forbids changing this unrelated tag-insertion/dictionary area, so the failures are reported and not hidden or fixed by overwriting user data. Full canonical-suite success remains unmet.
- Propagated only the 55-file linter manifest using preflight hashes and atomic writes. Final SHA-256 equality includes the report, record, validation JSON and all fixtures. Preserved canonical .gitignore, the policy original and the existing 3px snippet dictionary. No historical analysis files or unrelated source were transferred.
- Qt offscreen confirms severity decisions and unchanged text. Physical GUI readability/navigation/file-save acceptance, a rebuilt EXE, production-site saves and exhaustive Gutenberg schemas remain unperformed.

- Final observation detected another update to the out-of-scope snippet dictionary after validation. Preserved that update without overwriting it; recorded both hashes. The reported full-suite result belongs to the tested dictionary version, not the later update.

## Step15-section22 Multiline HTML Tag Highlighting

Date: 2026-10-25

Request: color complete multiline HTML opening tags, including multiline style attributes, without changing the linter or modifying document text.

Implementation:

- Changed only HtmlSyntaxHighlighter in editor/text_editor.py. Carry unclosed tag, single/double-quoted attribute and comment states between QTextBlocks using previousBlockState/setCurrentBlockState. End a tag only at an unquoted > and restore ordinary body formatting immediately afterwards.
- Preserve the configured HTML tag and WordPress comment colors, and keep comment/escaped-display content from starting tag runs. Convert Python character positions to Qt UTF-16 offsets so leading non-BMP text does not shift highlights.
- Added tests/test_html_syntax_highlighter.py: 13 new cases covering the supplied div/img layouts, quoted >, empty continuation lines, ordinary and WordPress comments, single-line neighboring tags, color settings, incremental quote edits, disable/enable, unchanged text/modification flags and emoji offsets.
- Updated both READMEs. No linter/parser/CSS/JSON implementation, application settings, WordPress runtime or build configuration changes.

Worktree validation:

- Highlighter plus existing whitespace/display tests: 22 passed. Full pytest: 695 passed (13 added tests).
- Rendered a separate Qt offscreen editor with multiline div/img examples; supplied Windows font files only to that test process. The rendered colors and actual QTextLayout format ranges were inspected; no user window/settings were changed.
- Canonical transfer and validation results are appended after final verification. EXE rebuilding and physical GUI acceptance remain separate and were not performed.

Canonical validation:

- Focused highlighter/display pytest: 22 passed. Full canonical pytest: 692 passed / 3 failed. The same three out-of-scope frame insertion tests disagree with the current snippet dictionary border/color/font-weight settings; do not overwrite those settings to make this highlighting task pass.
- Ruff passed; Pyright reported 0 errors, 0 warnings, 0 informations. Worktree full pytest: 695 passed. After merging parallel canonical documentation/type annotations, the focused 22 tests, Ruff and Pyright passed again; rendering logic was compared with annotations/docstrings excluded.
- Preserved concurrent Pylint comments, docstrings and type annotations in the canonical editor file. Transferred only editor/text_editor.py, tests/test_html_syntax_highlighter.py, README.md, README_jp.md and this appended record; unrelated sample data remains intact.
- Final SHA-256 equality was checked for the five intended files. No HTML/CSS/JSON/multilanguage linter changes were made in this task. The source application must be restarted to load the fix; no packaged EXE was rebuilt and physical GUI acceptance remains unperformed.


## Step15-section23 Hover Hint Wiring Audit

Date: 2026-10-25

Request: verify hover-hint connections after the multiline HTML highlighting fix.

Findings and narrow repair:

- Tag menu QAction.hovered signals reach the status bar, and menu/context-menu tooltips are enabled by the saved hover-hint option. The options checkbox, settings save/load and menu rebuild were already connected.
- TagInsertDialog received no hover-hint option and always enabled candidate tooltips/itemEntered explanations. Added set_hover_hints_enabled and apply it every time MainWindow opens the cached dialog; suppress hover hints while disabled, including filtered candidates, and retain keyboard/selection explanations.
- Editor source tags and lint highlights currently have no hover-explanation provider/event handler. No new editor hover feature, linter behavior, document modification or WordPress core change is introduced by this audit.
- Added tests/test_hover_hints.py for real Qt action/list signals, context-menu wiring, disabled/reenabled picker hints, filtered candidates, selected-candidate explanations and options-to-cached-dialog/settings propagation. Updated both READMEs.

Validation:

- Before repair: new wiring tests 1 passed / 2 failed. After repair: related tag/options/settings tests 74 passed, excluding four unrelated frame-template cases.
- Worktree full pytest: 698 passed. Ruff passed. Pyright with the required interpreter explicitly selected (--pythonpath D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe): 0 errors, 0 warnings, 0 informations. Bare Pyright initially could not resolve installed Qt/pytest; explicit interpreter selection resolved its environment lookup without source/config changes.
- Canonical propagation and verification follow. Tests use Qt offscreen and isolated settings; physical pointer acceptance and packaged EXE rebuild are unperformed.

Canonical validation:

- Related tag/options/settings pytest: 74 passed / 4 unrelated frame tests deselected. Full pytest: 693 passed / 5 failed. Three failures are the existing frame dictionary border/color/font-weight expectations; two are existing whitespace marker tests expecting U+2423 while the canonical editor now returns U+00B7 (canonical HEAD 7afd934, fixed space visualize font). Those unrelated source/dictionary/test changes were preserved.
- Ruff passed; Pyright with --pythonpath pointing to the required interpreter: 0 errors, 0 warnings, 0 informations. git diff --check passed.
- Transferred only main.py, dialogs/tag_insert_dialog.py, tests/test_hover_hints.py, README.md, README_jp.md and SCRIPT_STEP.md after comparing the canonical destinations to their preflight SHA-256 values. Final six-file SHA-256 equality checked. No editor/highlighter, linter, settings files, dictionary or WordPress core modifications in this task.
- Source repair is available in D:\PC\Python\regex_pad_project. EXE not rebuilt; physical mouse/tool-tip acceptance unperformed. Qt signal connections and settings propagation were tested offscreen with isolated temporary configuration files.


## Step15-section24 Neutral WordPress Preview Theme

Date: 2026-10-25

Request: remove Twenty Twenty-Five page styling/chrome from article preview without editing WordPress core, Gutenberg, Twenty Twenty-Five or the existing downloaded runtime.

Implementation:

- Added resources/wordpress_preview/themes/regexpad-preview with only a style.css theme header, theme.json v3 (contentSize/wideSize 100%, blockGap 0; no typography/body padding), and templates/index.html containing only the default-layout post-content block.
- Added a resource-relative theme.mjs installer. The bridge copies these new theme assets into the disposable PHP virtual filesystem and activates the theme with WordPress switch_theme. Existing runtime archives/packages and standard themes stay untouched; missing assets/activation failures report an error rather than silently using the old theme.
- The editor defaults to regexpad-preview. The backend/verifier accepts only regexpad-preview or twentytwentyfive so future theme comparison is possible; no theme-selector UI is added. Neither article text nor editor settings are rewritten. Existing loopback/read-only HTTP/stdin-update/shutdown behavior remains intact.
- Retained WordPress core block CSS and inline article styles. No CSS dequeueing, !important override layer, or font/body-padding injection. Only theme-added page elements are absent; an explicitly authored dynamic block still renders normally.
- Theme assets remain under resources, already included by both the spec and build.ps1. Neither build configuration nor runtime preparation/version dependencies are changed. Added Node built-in tests for theme-only writes, article-only template/configuration, relocated packaged resources, and missing-resource failure before writes.
- Extended the opt-in real-engine verifier to assert selected theme, served core block CSS, inline colors/spacer height, absence of standard-theme chrome/fonts/width, existing runtime SHA-256 equality, and the existing real-article/loopback/shutdown checks. Updated both READMEs, including restart/stop requirements and future comparison scope.

Worktree validation:

- Node theme/resource tests: 2 passed, including the missing-asset failure case. Real WordPress 7.1.3 / PHP 8.3 neutral and unmodified Twenty Twenty-Five verification succeeded; dynamic latest-posts rendering, spacer/latest-posts CSS, inline styles, HTTP write/foreign-host rejection and shutdown checks passed. Real broken/fixed article cases remain 11/0 static findings and both render HTTP 200 without PHP warnings.
- Existing runtime assets: 234 SHA-256 comparisons unchanged, including wordpress.zip eb58a90ed55147f90f7bd55d0d3334960a69b7e8a4cc142c8ddfea8965218227. The verifier log is diagnostic output and is excluded from the runtime asset inventory.
- Full worktree pytest reported 698 passed. Canonical validation, final lint/type checks and transfer verification follow. EXE rebuild, physical default-browser acceptance, production-site appearance and Gutenberg save() acceptance are separate and unperformed.

Canonical validation:

- Real neutral WordPress preview verification passed from the canonical resources: WordPress 7.1.3, regexpad-preview theme, core spacer/latest-posts CSS served, inline article styles preserved, HTTP 200/no PHP warnings for both qualification fixtures, 11/0 existing static findings, loopback/write restrictions and shutdown passed. Existing runtime assets: 234/234 SHA-256 comparisons unchanged. Saved analysis_cases/neutral_preview_verification.json.
- Node built-in theme/resource tests: 2 passed. Ruff passed. Pyright using the required --pythonpath: 0 errors, 0 warnings, 0 informations. Full canonical pytest: 693 passed / 5 existing unrelated failures (three frame dictionary/style expectations, two U+2423 vs U+00B7 whitespace-marker expectations). These settings/source/test differences were preserved.
- Worktree full pytest: 698 passed with exit code 0; Ruff and explicit-interpreter Pyright passed. git diff --check passed for this task's intended files. A whole-canonical diff check additionally reports pre-existing trailing whitespace at lines 34/319 of the user-edited tests/linter_check_tests_fixed.wp_html; preserved that file.
- Final intended manifest: bridge.mjs, theme.mjs, three regexpad-preview theme files, preview/verify_wordpress_preview.py, tests/wordpress_preview_theme.test.mjs, both READMEs, SCRIPT_STEP.md and the neutral verification JSON. Eleven files SHA-256-matched between worktree and D:\PC\Python\regex_pad_project. No unrelated source/settings/dictionaries/build/runtime files copied.
- Source changes are available in the canonical project. Stop a preview process already running before this update, then invoke the normal preview action again to load Neutral Preview. No EXE rebuild or physical-browser/production-site/Gutenberg-save acceptance was performed. No new third-party dependency.


## Step15-section25 Simple Export and Live Theme Preview

Date: 2026-10-25

Request: faster WordPress-backed preview with two visible modes. Simple mode should export a basic page and automatically stop WordPress; Twenty Twenty-Five mode should remain available until the user exits WordPress. User explicitly rejected reuse of previously rendered article HTML because edits must always be reflected.

Implementation:

- View menu: simple / auto-stop (Ctrl+Alt+P), Twenty Twenty-Five / live (Ctrl+Alt+Shift+P), and Exit WordPress. Separate controllers and source snapshots prevent simple completion from stopping the live preview or mixing feedback across documents/modes. Editor close stops both owned processes.
- Every action sends the current unsaved editor text through WordPress again, including an unchanged source. No article HTML cache lookup/reuse. Simple exports use a unique filename each time; reloading an older exported page retains that historical view and is not an editor refresh.
- Added a WordPress-initialization cache using the supported beforeDatabaseSetup hook, DB_PATH constant and install-from-existing-files-if-needed mode. Save only the fresh demo database before installing the preview theme or submitting any article. Runtime archive/SQLite/package-lock fingerprints and stored data SHA-256 invalidate missing, corrupt or outdated data. Existing WordPress/package/theme files remain untouched. No dependencies added.
- Simple mode embeds local CSS, nested CSS imports, fonts/images/srcset/inline CSS URLs into an HTML file under the portable Temp/WordPressPreview directory. External resources remain external. Remove executable scripts/event handlers for display-only use; preserve native HTML details. Asset retrieval stays on the owned loopback origin, blocks foreign redirects, respects size limits/cancellation, and runs outside the GUI thread. Stop PHP/WordPress before opening the file. Export errors and stop requests release the simple backend.
- Live mode retains real Twenty Twenty-Five assets and the existing read-only local HTTP server until explicit Exit WordPress/editor close. Subsequent live previews update the existing process. Production plugin/form/AJAX write behavior remains outside this read-only environment.
- Added static-export regression tests, controller/menu/lifecycle/current-source tests, Node bootstrap cache tests, and an opt-in real WordPress + Qt lifecycle/timing verifier. Updated both language resources and READMEs. Preserved canonical .gitignore rules and added only the generated preview-output exclusion.

Worktree validation:

- Original bridge: about 12.907 seconds to ready, 0.469 seconds to render (one local measurement). With initial demo DB cache, measured backend readiness 12.945 seconds cold / 1.772 seconds restored. End-to-end simple export measured 16.609 seconds first initialization, 2.420 / 2.446 seconds for edited / unchanged re-render, live start 2.443 seconds and live update 0.511 seconds. First-use downloads are not included, timings are machine/load dependent.
- Real engine/Qt verification passed: current edits reflected, unchanged article also re-rendered, unique output files, local display images embedded, simple process already stopped before opening file, live process remained available during another simple export, explicit stop closed HTTP, old snapshots remained readable. Initial-cache article-text exclusion is additionally checked in the final verifier run. Physical browser opening was suppressed.
- Full worktree pytest 704 passed. Ruff passed. Explicit-interpreter Pyright 0 errors/0 warnings/0 informations. Node theme/bootstrap tests 4 passed. Related snapshot/preview tests 19 passed. Canonical propagation/final validation follow.

- Packaging follow-up: exclude generated Temp JSON from regex-pad.spec collection so bootstrap/export metadata is not bundled. An isolated collector smoke check confirmed Temp exclusion and ordinary resource inclusion; no EXE build was performed.

Delayed prestart follow-up requested during implementation:

- Added one-shot 10,000 ms warm-up timer after editor initialization. It starts only an already-prepared runtime, sends no article, downloads nothing, and keeps simple WordPress ready until use/exit. Background progress/errors do not interrupt editing. An earlier explicit preview/exit cancels the timer; selecting live mode stops an unused simple standby. Normal offscreen pytest suppresses automatic optional-runtime startup.
- Cached-only preparation also checks for a compatible existing Node without calling normal installation. A manual request arriving during warm-up uses its current text; preparation completion handles the missing-Node/manual-request race. Simple mode still stops WordPress after export and does not rewarm automatically.
- Added tests for timer/signal wiring, no background downloads, quiet failure, latest-source submission after warm-up and the live handoff. Real WordPress verification measured prestarted simple render/export/stop in 0.660 seconds. New full worktree pytest: 707 passed; related preview/snapshot tests: 22 passed. No previously rendered article is reused.

Final live-mode clarification and canonical validation:

- User clarified that live preview should normally end together with RegexPad, rather than requiring manual Exit WordPress after each preview. The live controller already retains its process; changed EN/JA status text and READMEs to make early manual exit optional. Added actual process-ID equality checks across live re-renders, plus a MainWindow close regression that stops its retained live controller.
- Final canonical real-engine/Qt run passed. Measured simple cold export 17.404 seconds, subsequent edited/unchanged exports 2.682/2.617 seconds, theme start 2.586 seconds, theme update 0.548 seconds, prestarted simple export 0.660 seconds. Every invocation re-rendered current text; unchanged-source execution also submitted to WordPress. The initial DB cache contained none of the article test tokens. Prestart submitted no article/opened no browser, and stopped after simple export. Live process ID remained the same across previews, including while separate simple exports completed. Manual early stop and normal editor-close wiring were checked.
- Canonical full pytest: 702 passed / 5 known unrelated failures (three frame dictionary border/style expectations, two whitespace U+2423 vs U+00B7 expectations). Related preview/export tests: 22 passed. Worktree full pytest: 707 passed. Ruff and explicit-interpreter Pyright passed in both trees. Node theme/bootstrap tests: 4 passed. Isolated packaging collection check excluded Temp metadata while retaining resource JSON.
- Existing runtime inventory remained unchanged: 234 SHA-256 checks, including original WordPress ZIP eb58a90ed55147f90f7bd55d0d3334960a69b7e8a4cc142c8ddfea8965218227. No WordPress core, downloaded packages, Twenty Twenty-Five or linter changes in this task. Generated initialization cache and export files live outside bundled dependencies.
- Intended manifest: .gitignore; regex-pad.spec; main.py; preview/wordpress_preview.py, static_snapshot.py, verify_preview_modes.py; resources/app_text_en.json and app_text_ja.json; resources/wordpress_preview/bridge.mjs and boot-cache.mjs; tests/test_wordpress_preview.py, test_static_snapshot.py and wordpress_preview_boot_cache.test.mjs; both READMEs; SCRIPT_STEP.md; analysis_cases/preview_modes_worktree_verification.json and preview_modes_canonical_verification.json. Eighteen files SHA-256-matched with D:\PC\Python\regex_pad_project after final propagation. Preserved unrelated canonical ignore rules, dictionary/editor differences and the edited linter_check_tests_fixed.wp_html sample.
- Source available in the canonical project; restart RegexPad to load both actions and the delayed timer. No EXE rebuild, physical browser interaction, production-site/plugin or Gutenberg save() acceptance was performed. Tests suppressed external browser opening.


## Step15-section26 Simple Preview Side Padding

Date: 2026-10-25

Request: the supplied simple-preview PDF starts too close to the left edge; reserve about two full-width characters of space.

- Added styles.spacing.padding.left/right = 2em to the regexpad-preview theme.json only. Keep 100% content/wide sizes, zero block gap and existing article font/inline styles. Twenty Twenty-Five, WordPress core, user article sources and the supplied PDF are unchanged.
- Updated the existing Node theme contract and both READMEs. No new runtime code/dependency or automatic article correction.
- Read-only PDF inspection: rendered the first supplied PDF page using Poppler and inspected its positioning. Rendered the existing fixed qualification-article fixture through real WordPress into a new standalone snapshot. In an isolated headless Edge, measured body font 16px and left/right padding 32px at viewport widths 800px and 375px; content rectangles were [32,768] and [32,343]. Inspected the resulting screenshot. External network resources were blocked during that layout check; image availability was not assessed.
- Worktree Node theme/bootstrap tests: 4 passed. Related pytest: 22 passed. Canonical transfer/verification follow. No PDF authoring or EXE build.

Canonical validation:

- Node theme/bootstrap tests 4 passed; related preview/export pytest 22 passed. Ruff passed; Pyright with the required --pythonpath reported 0 errors/0 warnings/0 informations. Task-scoped diff check passed. Full pytest was not repeated for this theme-padding-only change.
- Five intended files SHA-256-matched between worktree and D:\PC\Python\regex_pad_project: neutral theme.json, existing Node theme test, both READMEs and this record. No unrelated files copied. Existing real-article layout was checked at two viewport widths using real WordPress output and headless Edge; physical GUI and EXE rebuild remain unperformed.
- If an older preview process is already prestarted, Exit WordPress once and request a new simple preview to load the updated theme resources. Existing exported HTML/PDF files remain unchanged.


## Step15-section27 Persistent WordPress Core Status

Date: 2026-10-25

Request: show WordPress readiness/preparation state permanently on the right of the status bar; ten seconds is a deferred start time, not guaranteed readiness.

- Added a permanent WP QLabel and per-controller state_changed notifications. Right-side text tracks simple and live modes independently: waiting, not prepared, preparing, runtime/core download, component/core preparation, starting, ready, rendering/exporting, stopped and failed. Ordinary status/cursor/count updates no longer obscure WordPress state. Language switching refreshes the indicator; hover help explains deferred prestart/manual first setup and escapes failure details.
- Ready is set only after validating the backend ready event. Warm-up state updates remain visible on the right without producing transient messages/dialogs. Missing cached runtime/Node is not prepared, not ready; background failures remain visible as failed. Simple automatic stop and explicit cancellation show stopped while retaining the live process's readiness if it remains active.
- Added a core-download progress event only inside the actual missing-archive download branch. Existing archive validation uses core preparation, avoiding a false downloading label. Preparation/download policy is unchanged: automatic prestart uses prepared data only, and first-time acquisition begins on an explicit Preview action. Article text, WordPress core, installed packages, themes and preview lifecycle semantics are unchanged.
- Updated both language resources, both READMEs and five state/wiring regressions. Tests cover ready acknowledgment, quiet prestart, missing data, downloads versus existing ZIP, failures/cancellation, persistent label during editing/language changes and independent simple/live status.
- Worktree related pytest: 27 passed; full pytest: 712 passed. Ruff/Pyright and canonical results follow. Ran an isolated offscreen MainWindow against actual WordPress: observed prepare -> boot -> ready -> render -> export -> stopped with matching right-label text. Inspected a Qt status-bar screenshot showing normal editing information at left and WP readiness at right. No physical desktop interaction or external browser was performed.

Canonical validation:

- Full canonical pytest: 707 passed / 5 known unrelated failures (three frame dictionary border/style expectations, two whitespace U+2423 vs U+00B7 expectations). Full worktree pytest: 712 passed; related status/preview/export pytest: 27 passed. Ruff and explicit-interpreter Pyright passed in both trees. Task-scoped diff check passed.
- Propagated only main.py, preview/wordpress_preview.py, preview/wordpress_runtime.py, both app-text resources, tests/test_wordpress_status.py, both READMEs and SCRIPT_STEP.md. Final nine-file SHA-256 equality checked with D:\PC\Python\regex_pad_project; preserved prior padding changes and unrelated canonical files.
- Actual WordPress startup/render/export signals were checked in an isolated offscreen MainWindow, including right-label visibility while normal editing messages remained at left. New unit tests also checked the missing-archive download event and absence of that event when the archive already exists, without network access.
- Restart the source application to load the permanent status widget. No EXE rebuild, physical GUI/default-browser or production-site acceptance was performed. No article rewriting, core/package/theme modification or automatic-download policy change.


## Step15-section28 WordPress Runtime Cleanup

Date: 2026-10-25

Request: include downloaded WordPress core/related files and any app-created environment/registry settings in module_cleaner.exe cleanup targets.

- Added three app-owned namespaces independent of module-install records: runtime/wordpress-preview, _internal/runtime/wordpress-preview and Temp/WordPressPreview. These include core/SQLite/PHP.wasm, portable Node, npm/setup/partial-download files, initialized demo DBs and exported simple HTML/metadata. Existing app resources, other runtime/venv folders and article folders are not added automatically.
- Preserve recorded additions while handling relative paths and consolidating parent/child duplicates. Reject the app root, outside targets, symbolic links/junctions and nested links before deletion; revalidate after confirmation and immediately before recursive deletion. Keep scan/dry-run and DELETE confirmation. Locked-file failures produce a nonzero exit status and explicit deleted/error lists in cleaner_report.json.
- Audited runtime preparation, portable_runtime.py, installer and build scripts. Runtime installation is prefix/cache-local, no registry APIs or persistent environment writes are used. Environment overrides are process-local; build-script overrides are restored. Reports record empty persistent environment/registry cleanup lists. Do not delete shared Node/Python, global PATH or user-defined registry/settings.
- Added tests/test_module_cleaner.py. Nine tests passed, including actual Windows directory junction fixtures, no-record/partial/bundled downloads, deduplication/scoping, dry-run, cancellation, revalidation after confirmation, preserved article/venv/resources and locked-file reporting. Read-only discovery on real source and dist folders recognized their existing WordPress namespaces without deleting their contents.
- Full worktree pytest: 721 passed. Ruff/Pyright and canonical validation follow. Rebuild only module_cleaner.exe, verify the packaged binary on disposable fixtures, and retain the existing GUI EXE/runtime files. Do not run destructive cleanup against actual installed/downloaded data.

Canonical/source and packaged validation:

- Full worktree pytest: 721 passed. Full canonical pytest: 716 passed / 5 existing unrelated failures (three frame dictionary/style expectations and two whitespace U+2423 vs U+00B7 expectations). Cleaner regressions: 9 passed, including Windows junction cases. Ruff and explicit-interpreter Pyright passed in both trees. Intended source changes matched by SHA-256 for module_cleaner.py, tests/test_module_cleaner.py, both READMEs and SCRIPT_STEP.md.
- Rebuilt only the cleaner using required Python 3.12.10 / PyInstaller 6.22.2 as a standalone console onefile EXE. Build work/spec/cache/output are confined to build/cleaner-update; temporary PYINSTALLER_CONFIG_DIR override was restored. The main regex-pad GUI EXE was not rebuilt or replaced.
- Tested the built executable in a disposable Japanese-named portable folder: default-root --dry-run listed all three namespaces without deletion; --clean --yes removed only synthetic WordPress fixtures and preserved article/venv/non-WordPress resources; --scan then reported no candidates. All exited 0. Actual payload cleanup was confined to temporary fixtures.
- Updated D:\PC\Python\regex_pad_project\dist\regex-pad\module_cleaner.exe. Size 8,347,009 bytes; SHA-256 d003df1a6810fb3399a49c16e45e8d596dacfd2980be6d46b391a64ac580796e. Previous helper retained under build/cleaner-update/previous/module_cleaner-<old hash>.exe. Binary update is separate from the five-file source propagation; no build output was copied into the worktree.
- Ran the deployed cleaner with --dry-run only against its actual adjacent app folder. It recognized _internal/runtime/wordpress-preview, wrote cleaner_report.json and deleted nothing. Confirmed source WordPress ZIP, bundled WordPress ZIP and the existing GUI EXE retained their pre-check SHA-256 values. No real downloaded/runtime/cache/article data or system environment/registry settings were removed.
- Normal use: exit RegexPad/WordPress first, inspect --dry-run, then --clean with DELETE confirmation. Use --app-root for source or another portable folder. Source is available in the canonical project and the cleaner binary is updated; physical double-click/interactive-console acceptance remains unperformed.


## Step15-section29 First-Run Manual Cleanup Inventory

Date: 2026-10-25

Request: bundle user-created DELET_ITEMS_LIST.md under _internal and generate actual module/WordPress/configuration locations on first ZIP-extracted EXE startup, so leftover resources can be located manually. User additionally requested shared/high-risk references in a separate final warning section.

- Filled the initially empty document as a template with generated-section markers and a persistent manual-notes section. Added cleanup_inventory.py: atomic UTF-8 Markdown copies at _internal/DELET_ITEMS_LIST.md and install_records/DELET_ITEMS_LIST.md, with install_records/deletion_inventory.json history. Preserve manual text outside markers, original creation time and previously seen paths with refreshed existence status; reset location-specific history if the portable folder is relocated.
- Inventory covers app-scoped Python environments/module metadata, npm lock metadata and presence, actual WordPress runtime/output locations, host-side plugin folders when present, INI/config paths without contents, selected Node and only the five relevant process-environment overrides. It does not scan arbitrary drives or the registry, collect unrelated environment variables/secrets, or delete/change permissions on any listed resource.
- Added the exact final warning headings requested by the user. External paths, shared selected Node, inherited environment references and external module locations appear only there, separately from normal app-local entries; these are reference-only and not added to cleaner automatic targets. Persistent environment/registry sections explicitly state none created by RegexPad. Virtual WordPress core/plugins are released on process exit.
- Frozen startup initializes the list after portable paths/env are configured; preparation completion/failure, backend readiness, simple export and normal editor close refresh it. The Python module installer also refreshes on success/failure. Inventory errors are logged without breaking startup/download; a writable companion list survives a locked _internal copy. Directory access failures are visible as notes, and uncertain existence is not reported as absent.
- Spec/build.ps1 include the template under _internal. JSON collection excludes generated install records, logs, cache, data and module folders to avoid packaging developer-specific inventory. Source document remains a template, not a machine-specific report. No dependency added.
- Related inventory/packaging/portable/preview pytest: 38 passed; Ruff/Pyright passed. Earlier full worktree pytest: 728 passed before final close/access-error additions; final source/canonical checks and actual ZIP first-run validation follow.

Canonical/source and packaged validation:

- Final full worktree pytest: 730 passed. Full canonical pytest: 725 passed / 5 existing unrelated failures (three frame dictionary/style expectations and two whitespace U+2423 vs U+00B7 expectations). Related inventory/packaging/portable/preview pytest: 38 passed. Ruff and explicit-interpreter Pyright passed in both trees; build.ps1 PowerShell syntax and task-scoped diff checks passed.
- Propagated only the 13 intended source/document/test files: DELET_ITEMS_LIST.md, cleanup_inventory.py, portable_runtime.py, module_installer.py, preview/wordpress_preview.py, regex-pad.spec, build.ps1, tests/test_cleanup_inventory.py, tests/test_pyinstaller_spec.py, README.md, README_jp.md, SCRIPT_STEP.md and main.py. Final SHA-256 equality with D:\PC\Python\regex_pad_project verified; preserved unrelated canonical changes.
- Built the full GUI/helper onedir distribution from canonical sources into build/inventory-release/dist/regex-pad using the required interpreter. Verified the bundled WordPress runtime (234 files), template inclusion and exclusion of generated install_records. Existing dist/regex-pad GUI/helper and original WordPress archives were not replaced or modified.
- Created dist/regex-pad-inventory.zip, 162,850,927 bytes, SHA-256 6967b1b4f37a819da71be54d17854e4f0694861796963b984f2d2bc20e1cdbb0. ZIP integrity and required _internal template passed. Distribute/extract the entire regex-pad directory including _internal.
- Extracted that actual ZIP into an isolated temporary folder and launched its EXE with Qt offscreen. First startup generated both Markdown copies and JSON with the extracted app paths (about 1.7 seconds). Second startup (about 1.2 seconds) refreshed a synthetic Python package/version, INI and plugin paths; preserved manual notes/creation time; put inherited external cache paths only in the final shared-warning section; excluded unrelated environment and INI secret values. Test-owned processes were terminated after assertions. Evidence: build/inventory-release/first-run-verification.json. This is packaged offscreen startup verification, not physical GUI acceptance.
- Created current-source review copies at _internal/DELET_ITEMS_LIST.md and install_records/DELET_ITEMS_LIST.md plus the JSON record; the root DELET_ITEMS_LIST.md remains the reusable template. No real download/install, runtime deletion, permissions change, registry write or persistent environment change was performed. Actual WordPress archives and the existing normal-distribution GUI retained their pre-check hashes.


## Step15-section30 Stable 1.0.0 User Documentation

Date: 2026-10-25

Request: prepare English/Japanese README and standalone usage guides, using a natural stable release label and the supplied English/Japanese UI screenshots.

- Reorganized README.md and README_jp.md around RegexPad, Release: 1.0.0 (Stable), startup, main features, two preview modes, recovery/cleanup and developer entry points. Added docs/HOW_TO_USE.md and docs_jp/HOW_TO_USE_jp.md with equivalent instructions, contents links, menu names, examples, shortcuts and troubleshooting.
- Added the four supplied, unmodified images as docs/images/editor-en.png, css-insertion-en.png, editor-ja.png and color-picker-ja.png; both guides use relative links so the documentation remains portable.
- Matched descriptions to current implementation: block-attribute JSON checking rather than a generic JSON-file command; explicit Regex Rewrite is a text change outside search exclusions; tab close uses recovery snapshots; no linter/preview source auto-repair; current unsaved text is resubmitted for every preview; the ten-second timer starts prepared data only; shared cleanup references remain in the final warning section. Retained developer runtime/build/verification guidance from the previous README in the guides.
- Documentation-only scope: no Python, WordPress core, theme, runtime, About/version metadata or build configuration edits. Existing EXEs/ZIPs are not rebuilt, renamed or replaced. The stable label identifies these four documents' release baseline; this task does not certify new physical GUI or real-site acceptance.
- Worktree verification: all 56 local links/images/anchors resolved; all four documents passed UTF-8/release-label/code-fence checks and all four PNG dimensions/signatures passed. Relevant existing help, regex content, Find/Replace, tab, backup, WordPress status and cleanup inventory pytest: 84 passed. Ruff passed; explicit-interpreter Pyright: 0 errors/0 warnings/0 informations. Removed Markdown trailing hard-break spaces; task-scoped diff check passed. Full pytest was not repeated for this documentation-only change.
- Transfer manifest: README.md, README_jp.md, docs/HOW_TO_USE.md, docs_jp/HOW_TO_USE_jp.md, the four docs/images PNG files above and SCRIPT_STEP.md. Canonical preflight confirmed existing README/record bytes matched and new guide/image paths were absent; preserve all unrelated canonical changes. Canonical validation and final SHA-256 checks follow.

Canonical validation:

- In D:\PC\Python\regex_pad_project, the same focused pytest selection passed all 84 tests. Full Ruff passed; Pyright with the required --pythonpath reported 0 errors/0 warnings/0 informations. Task-scoped diff check passed. Canonical link checking identified that GUTENBERG_BEHAVIOR_REPORT.md exists only in the worktree; references now point to the shared SCRIPT_STEP.md instead of copying an unrequested report. Rechecked all 54 final local Markdown links/images/anchors, UTF-8/release labels/code fences and the four PNGs in both folders. Full pytest and physical GUI acceptance were not repeated for these documents.
- Verified exact SHA-256 equality for the nine-file manifest after the final record append, and verified the four copied PNGs match the user's original attachments. Canonical changes are limited to the requested four documents, their four screenshot assets and this record. No application source, settings, dictionary, backup or build output was transferred. Existing EXE/ZIP artifacts still predate these documentation changes and were not advertised as updated packages.


## Step15-section31 Release Documents Beside the EXE

Date: 2026-10-25

Request: save the English/Japanese plain-text README and license notice at the same level as regex-pad.exe.

- Updated readme.txt and readme_jp.txt as standalone Release: 1.0.0 (Stable) quick starts with UTF-8 BOM/CRLF for Windows text viewers. They cover startup, current explicit-edit versus check/preview behavior, preview lifetimes, recovery, cleanup and the detailed guides. Existing LICENSE.txt is copied byte-for-byte; no license terms or grants were created or changed. The existing filename uses LICENSE, not LICENCE.
- Added Copy-ReleaseDocumentation to build.ps1. On successful build/runtime verification it places readme.txt, readme_jp.txt and LICENSE.txt beside regex-pad.exe. It also includes README.md, README_jp.md, SCRIPT_STEP.md, docs/ and docs_jp/ so guide links and screenshots remain available. Required files/folders are checked before copying. Directory contents merge without nesting docs/docs or deleting existing notes. ZIP creation remains a separate action.
- Updated both Markdown READMEs and both guides to document automatic copying and the separate ZIP step. No change to application Python, WordPress core, runtime preparation, source articles, settings, license content or ZIP/build names.
- Worktree verification: parsed build.ps1 and executed only its copy function twice on an isolated disposable fixture. All 12 document/image files matched source SHA-256, existing dummy EXE/settings/manual notes were preserved, repeated directory placement remained correct, and missing documents caused the expected failure before copying. Packaging pytest: 9 passed. Full Ruff and explicit-interpreter Pyright passed; task-scoped diff check passed. No full PyInstaller execution, full pytest or physical GUI acceptance for this copy-only change.
- Intended source transfer: build.ps1, readme.txt, readme_jp.txt, README.md, README_jp.md, docs/HOW_TO_USE.md, docs_jp/HOW_TO_USE_jp.md and SCRIPT_STEP.md. Preflight confirmed exact equality of existing versions in both trees. Also place the 12 release documents/assets into the existing canonical dist/regex-pad folder using the same copy function; no EXE, runtime or ZIP replacement. Canonical checks and final hashes follow.

Canonical and distribution verification:

- In D:\PC\Python\regex_pad_project, packaging pytest: 9 passed; full Ruff and explicit-interpreter Pyright passed. PowerShell syntax and task-scoped diff checks passed. The actual copy function, extracted from the canonical build.ps1 AST without running its build/deletion operations, placed all 12 document/assets in dist/regex-pad. Both TXT files have a UTF-8 BOM, current release label and correct bilingual text.
- Confirmed 54 local guide/README links, images and anchors resolve in each of the worktree, canonical source and actual distribution folder. Existing license bytes matched between worktree, canonical and dist. GUI EXE, cleaner EXE, old inventory ZIP and source/bundled WordPress ZIP hashes remained unchanged.
- Final eight-file intended source manifest matches worktree/canonical SHA-256. All 12 copied release documents/assets match canonical sources, including the final record update. Source sync excludes settings, unrelated changes and build output. The three requested plain-text/license files are now beside dist/regex-pad/regex-pad.exe, and future build.ps1 runs copy them automatically. This did not rebuild the EXE or update any ZIP; archive the checked full folder separately when producing a new release package.


## Step15-section32 Qt Licensing Notices and Requested Attribution

Date: 2026-10-25

Request: describe PySide6 licensing carefully and end readme.txt with the user's corrected exact text, "I got help from Chat-GPT and Codex."

- Checked official Qt for Python / Qt 6.11 documentation, module licensing and LGPL obligations against installed 6.11.2 package metadata and the actual existing distribution files. Metadata offers LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only; that is not a license declaration for every Qt module. Found Qt6VirtualKeyboard.dll and platforminputcontexts/qtvirtualkeyboardplugin.dll in the actual distribution; official Qt 6.11 docs identify Virtual Keyboard as commercial/GPLv3, not LGPL. No assertion that mere presence automatically relicenses RegexPad's own code.
- Expanded LICENSE.txt while retaining the prior office/internal-use terms for original application code. Explicitly exempt upstream rights from application-only restrictions; make no unverified commercial-entitlement claim, automatic GPL/LGPL relicensing or source-supply written offer. Added bilingual THIRD_PARTY_NOTICES.md separating observed contents, upstream terms and outstanding version/source-provenance, source-delivery, modified-library replacement and module-license checks. This is a targeted Qt notice, not a complete third-party license inventory or compliance certification.
- Downloaded LGPLv3/GPLv3/GPLv2 original texts directly from Qt's pyside-setup v6.11.2 LICENSES paths and preserved their bytes/SHA-256 values under licenses/qt-for-python/. Copied the installed upstream LicenseRef-Qt-Commercial.txt unchanged and recorded provenance/hashes in SOURCES.md; inclusion grants no commercial entitlement. No library binary/source archive was downloaded or modified. Official source locations are references, not a claim that linking to them fulfills all source-delivery duties.
- Updated both TXT READMEs, both Markdown READMEs and both guides with notices/review references. English readme.txt ends with exactly one "I got help from Chat-GPT and Codex." line; the earlier Codex-only wording is absent. Build copy includes THIRD_PARTY_NOTICES.md and licenses/ and fails if required Qt/PySide license files are missing.
- Worktree validation: PowerShell parsing and actual copy-function execution on isolated fixtures passed. Eighteen document/image/license files matched after repeated copies; a missing LGPL text failed before partial writes, with the dummy EXE preserved. Packaging pytest: 9 passed; full Ruff and explicit-interpreter Pyright passed; 74 local links/images/anchors and upstream license hashes passed, as did exact final-line/encoding checks. Full pytest, full rebuild, physical GUI and modified-library replacement tests were not run for this documentation/copy change.
- Canonical transfer manifest: LICENSE.txt, readme.txt, readme_jp.txt, build.ps1, README.md, README_jp.md, docs/HOW_TO_USE.md, docs_jp/HOW_TO_USE_jp.md, SCRIPT_STEP.md, THIRD_PARTY_NOTICES.md and the five licenses/qt-for-python files. Existing-file preflight hashes were captured before edits; new license/notice paths must be absent. Also copy release documents into the actual canonical dist/regex-pad folder without changing its executable/runtime files or ZIP. Final canonical checks follow.

Canonical and packaged-document verification:

- Canonical packaging pytest: 9 passed; full Ruff and explicit-interpreter Pyright passed, with PowerShell parsing and task-scoped diff checks passed. Ran only the canonical document-copy function to update EXE-adjacent files. In each of the worktree, canonical folder and existing distribution, all 74 local links/images/anchors resolved, the exact requested attribution was the single final readme.txt line, and original downloaded LGPL/GPL text hashes matched.
- Final manifest SHA-256 equality: 15 intended source/document/license files between worktree and canonical; 18 release document/assets between canonical and dist/regex-pad. Updated this final record in both source trees and the distribution. Existing GUI/cleaner EXEs, inventory ZIP and original source/bundled WordPress archives retained their previous hashes. No package rebuild or ZIP replacement performed.
- Documentation and attribution are complete within this task. Licensing clearance is not claimed: the observed Virtual Keyboard GPLv3/commercial route, corresponding-source delivery, actual frozen-library replacement mechanism and complete third-party notices still require release-specific resolution. No commercial contract was assumed or acquired; no source offer or GPL relicensing was created on the owner's behalf. Qt official references and raw-text provenance are included in the maintained notices rather than treating a brief README acknowledgment as full compliance.


## Step15-section33 GPLv3 Application Policy and Public Source Guide

Date: 2026-10-25

Request: rewrite license-related documents using the supplied Public-GitHub/GPLv3 advice. After the earlier read-only review, the user explicitly requested applying that basis to the documents; the declared application license is now GPL-3.0-only, replacing the original-code office/internal-use restriction.

- Read-only GitHub connector verification confirmed Flopbrane/regex-mini-pad is Public, while its then-published LICENSE.txt still contained the previous office/internal notice. GitHub's Public setting alone is not a GPL grant. No remote license was edited. Read-only git ls-remote returned no v1.0.0 tag; local documents use that name only as a planned release identifier, not as a published tag matching an old EXE.
- Added root LICENSE as the byte-identical upstream GPLv3 text. Rewrote LICENSE.txt, THIRD_PARTY_NOTICES.md, bilingual TXT/Markdown READMEs and both guides for GNU GPL version 3 only. Clarified permitted use/modification/redistribution (including distribution for a fee) under GPL terms; preserve separately licensed third-party code/materials and recipient rights. This supersedes the previous application-only internal-use notice, without claiming a commercial Qt entitlement or unilaterally changing dependency licenses.
- Added SOURCE_CODE.md with the actual Public repository URL, exact-source/tag/binary release workflow, required build/source inputs and separate dependency-source duties. Public latest-main access, a planned tag, or a top-level source link is not asserted to prove full Corresponding Source delivery. No unverified written source offer. No push, release tag creation, binary rebuild or release publication performed.
- Retained the observed Virtual Keyboard DLL/plugin under the GPLv3 route in the notices. Inspection found no explicit source use; the local PyInstaller QtGui hook collects platforminputcontexts and its TOCs include that plugin/DLL. This does not establish that removal is safe, and no module was removed. Added unchanged OpenWnn NOTICE, PinyinIME NOTICE and TCIME COPYING from Qt Virtual Keyboard v6.11.2 source, with upstream paths and SHA-256 provenance. Describe optional-engine status and do not claim a full enabled-dependency audit.
- Corrected current document/license path references to actual tracked LICENSES capitalization for case-sensitive GitHub/Linux readers. Existing LICENSES/LGPL-3.0.txt and Qt license originals are retained. Build copy now includes root LICENSE, SOURCE_CODE.md and the additional third-party originals, and checks required notice files before copying.
- Worktree verification: 98 case-sensitive local links/images/anchors passed; root GPLv3 and three downloaded third-party originals hash-match upstream copies. All nine application-facing license documents consistently declare GPL-3.0-only; readme.txt retains its single exact final line, "I got help from Chat-GPT and Codex." PowerShell syntax and actual copy-function tests passed twice, with all 25 document/assets matching and a dummy EXE preserved. Packaging pytest: 9 passed; full Ruff and explicit-interpreter Pyright passed. Full pytest, physical GUI and binary/source-correspondence acceptance were not run for this document/copy change.
- Intended canonical manifest: LICENSE, LICENSE.txt, SOURCE_CODE.md, THIRD_PARTY_NOTICES.md, readme.txt, readme_jp.txt, README.md, README_jp.md, both guides, build.ps1, SCRIPT_STEP.md, existing LICENSES/qt-for-python/SOURCES.md provenance, and the four new LICENSES/qt-virtual-keyboard files (17 files including verified unchanged provenance). Preflight hashes guard existing canonical files and absence of new paths. Update the actual dist/regex-pad documents using the same copy function; preserve all executable/runtime/ZIP content. Canonical validation follows.

Canonical and distribution verification:

- Canonical packaging pytest: 9 passed; full Ruff and explicit-interpreter Pyright passed. PowerShell syntax and task-scoped diff checks passed. Copied the maintained documents with only the canonical copy function; root LICENSE and SOURCE_CODE.md are beside the existing EXE. Aligned the distribution directory's existing lowercase licenses name to LICENSES after validating its absolute path stays within dist/regex-pad; no directory contents removed.
- Worktree, canonical and distribution each passed 98 local link/image/anchor checks with exact filename case, exact final English attribution, root GPLv3 byte equality and original Virtual Keyboard third-party notice hashes. Final intended source SHA-256 equality: 17 files (including verified unchanged provenance). Actual distribution documents/assets: 25 files matched canonical sources, including the final record. Existing GUI/cleaner EXEs, inventory ZIP and source/bundled WordPress archives retained their earlier hashes.
- The requested local GPLv3 documentation and build-copy updates are complete. No GitHub files were changed through the connector, no commit/tag/push or Release publication was performed, and no EXE/ZIP was rebuilt. The remote still needs the source/license changes published with the actual matching binary revision; complete corresponding dependency-source and final third-party inventory work remain release tasks. These are not presented as completed by local document edits.

## Step15-section34 Match-Scoped Unicode Normalization Replacement

Date: 2026-11-09

Request: implement `UNICODE_NORMALIZE_SCRIPTS.md` as a dedicated Unicode search/replacement route without changing unrelated features or the existing normal replacement behavior.

- Added `unicode_normalize.py` as a PySide-independent pure transformation module using only Python's standard `unicodedata`. It supports NFC, NFD, NFKC and NFKD. The optional period suffix is limited to a single original circled number from `①` through `⑳` and compatibility forms NFKC/NFKD.
- Extended `SearchOptions` with disabled-by-default Unicode replacement settings. The search engine continues to determine match and exclusion ranges; only replacement generation switches to the normalized matched text when the mode is enabled. Ordinary replacement strings and regex group references retain the existing path when the mode is off.
- Reused the common replacement result path for single replace, replace all, preview and marked replacement. Callback-based replace-all preserves original positions while results may grow, such as `⑩` to `10.`. Empty matches remain excluded by the existing search safeguards.
- Added Find/Replace controls for mode ON/OFF, normalization form and circled-number period suffix, with Japanese and English text. The ordinary replacement input is disabled but not cleared while Unicode mode is active, making the independent route visible; regex recipes switch back to ordinary replacement.
- Added pure-function, search-engine, dialog and main-window tests covering `① ② ⑩ ⑳` to `1. 2. 10. 20.`, nonmatch preservation, full-width digits without a period, mode-OFF regression, single/all replacement, preview, length growth, input state and Undo.
- Worktree focused pytest: 145 passed. Full worktree pytest: 729 passed / 16 unrelated existing failures: 11 missing Gutenberg fixture-file cases, three existing WordPress frame-style expectation differences and two existing visible-space-marker expectation differences. Full Ruff passed. Pyright with the required interpreter supplied through `--pythonpath`: 0 errors, 0 warnings, 0 informations. `git diff --check` passed.

Canonical propagation and validation:

- Preflight confirmed worktree and `D:\PC\Python\regex_pad_project` were both based on `265ad4fd6fd7c88ce7a4cfbdd375370f23e1341e`; canonical tracked files were clean and only the user-supplied `UNICODE_NORMALIZE_SCRIPTS.md` was untracked. That specification file was read but not modified.
- Propagated only `unicode_normalize.py`, `search/search_engine.py`, `dialogs/find_replace_dialog.py`, both application-text JSON files, the four related test files and this record. `main.py`, normalise operations, WordPress code, settings, backups and build output were not changed.
- Canonical focused pytest: 145 passed. Full canonical Ruff passed. Explicit-interpreter Pyright: 0 errors, 0 warnings, 0 informations. Seven Python implementation/test files matched the worktree by exact SHA-256; the two JSON resources had identical UTF-8 content after LF/CRLF normalization while retaining each checkout's existing line-ending convention.
- Packaged EXE rebuilding and physical Windows GUI acceptance were not performed. Source behavior was validated with the existing offscreen Qt tests; the normal application source is available in the canonical project.

## Step15-section35 Unicode Normalization Documentation and Form Guidance

Date: 2026-11-09

Request: add Unicode search/replacement guidance to both READMEs and Regex Help, and explain NFC/NFD/NFKC/NFKD in the Find/Replace interface without overcrowding the form selector.

- Added bilingual README sections with the `[①-⑳]` workflow, match-only behavior, period-suffix conditions, compatibility-normalization caution and a four-row comparison of NFC, NFD, NFKC and NFKD.
- Added matching English/Japanese Regex Help rows. Selecting the new circled-number example inserts `[①-⑳]`; the row explains which forms convert the characters and shows the `1.朝 2.昼 10.まとめ` result.
- Kept the normalization combo entries short. Added a separate word-wrapped explanation label below the selector, enabled only with Unicode normalization replacement. Japanese and English text summarize canonical composition/decomposition and compatibility composition/decomposition, including `① → 1` for NFKC.
- No Unicode conversion, matching, replacement, WordPress or file-handling logic changed. The follow-up touched only the two READMEs, Find/Replace presentation, four bilingual resource files, two related tests and this record.
- Offscreen Qt layout verification at the natural Japanese dialog size produced a 533 x 643 dialog and a visible 409 x 23 word-wrapped guidance label. This checks layout calculation, not physical Windows font/DPI acceptance.

Validation and canonical propagation:

- Worktree focused pytest: 160 passed. Focused Ruff passed; explicit-interpreter Pyright reported 0 errors, 0 warnings and 0 informations; `git diff --check` passed.
- Applied the same narrow changes to `D:\PC\Python\regex_pad_project`, preserving `UNICODE_NORMALIZE_SCRIPTS.md` and all unrelated files. Canonical focused pytest: 160 passed; full Ruff passed; explicit-interpreter Pyright reported 0 errors, 0 warnings and 0 informations; `git diff --check` passed apart from informational existing checkout line-ending warnings.
- The packaged EXE was not rebuilt. Physical GUI acceptance remains separate; source and bundled-resource changes are available in the canonical project.

## Step15-section36 Unicode Replacement Visual Separation

Date: 2026-11-09

Request: clarify whether the Unicode normalization checkbox should sit beside the regular-expression checkbox or be visually separated as a special replacement mode.

- Chose a horizontal separator above Unicode normalization replacement. Placing the long bilingual checkbox beside Regular expression would crowd the row and incorrectly suggest that Unicode normalization is merely a subordinate regex option; the separator preserves the Unicode checkbox, normalization form, explanation and circled-number option as one distinct replacement group.
- Added a three-pixel sunken `QFrame` line spanning both form columns. No labels, settings, search options or normalization behavior changed.
- Offscreen Japanese layout verification: natural dialog size 533 x 652; visible separator 511 x 3. Worktree and canonical related pytest: 93 passed in each. Focused/worktree and full/canonical Ruff passed; explicit-interpreter Pyright reported 0 errors, 0 warnings and 0 informations; diff checks passed apart from existing canonical JSON line-ending notices.
- Propagated only `dialogs/find_replace_dialog.py`, `tests/test_find_replace_dialog.py` and this record to `D:\PC\Python\regex_pad_project`. No EXE rebuild or physical Windows GUI acceptance was performed.

## Step15-section37 README Stable 1.1.0 Label

Date: 2026-11-09

Request: update the English and Japanese README versions after adding Unicode normalization replacement.

- Preserved the established README naming style and changed `Release: 1.0.0 (Stable)` to `Release: 1.1.0 (Stable)`; the Japanese stable label now also reads `1.1.0`.
- Aligned the README release dates to November 9, 2026 / 2026年11月9日 and changed the documented planned tag from `v1.0.0` to `v1.1.0`. The text still states that the tag is planned and does not claim an existing EXE was built from it.
- Changed only `README.md`, `README_jp.md` and this record in both the worktree and `D:\PC\Python\regex_pad_project`. No application/About metadata, build configuration, Git tag, commit, EXE or ZIP was changed.
- Verified both READMEs contain `1.1.0` and `v1.1.0` with no remaining `1.0.0`. Related document pytest: 5 passed in both trees. Canonical full Ruff passed; explicit-interpreter Pyright reported 0 errors, 0 warnings and 0 informations; diff checks passed apart from informational existing JSON line-ending notices.

## Step15-section38 Full-Width HTML Syntax Linter

Date: 2026-11-10

Request: detect accidental full-width HTML punctuation, based on a real editing case where `＜span style="color: #65FFCD">文章</span>` could be treated as visible text and escaped by WordPress after draft saving.

- Added a read-only Linter rule for tag-like text containing full-width `＜`, `＞`, `＝`, `＂`, `＇` or `／`. The Japanese diagnostic for the reported case is: `HTMLタグと思われる箇所に全角の \`＜\` があります。半角の \`<\` を使用してください。`
- Added a separate diagnostic for U+3000 used in HTML syntax, including `<p　class="...">` inside WordPress core blocks. It identifies U+3000 and recommends U+0020 so the invisible difference remains understandable.
- The scanner examines only HTML-like tag syntax. ASCII-quoted attribute values such as `title="日本語　文章"` remain valid, and example text inside comments, `code`, `pre`, `textarea`, `script`, `style`, `title` and `xmp` is excluded. Existing valid half-width `<span style="color: #65FFCD">文章</span>` remains clean.
- Added Japanese and English messages plus regressions for the reported broken/fixed forms, full-width closing punctuation, WordPress paragraph-block spacing, translated output, exclusions and non-mutation. The existing unmatched `</span>` warning may also appear for the malformed opener; the new warning points directly to the full-width cause on the opening line.
- Worktree validation: focused HTML-Linter pytest 253 passed; full pytest 740 passed / 16 existing failures (11 absent Gutenberg fixture cases, three frame-style expectations and two visible-space-marker expectations). Full Ruff passed; explicit-interpreter Pyright reported 0 errors, 0 warnings and 0 informations.
- Canonical validation: focused HTML-Linter pytest 253 passed; full pytest 751 passed / five existing unrelated failures (three frame-style expectations and two visible-space-marker expectations). Full Ruff passed; explicit-interpreter Pyright reported 0 errors, 0 warnings and 0 informations.
- Propagated only `search/html_typo_lint.py`, both application-text JSON resources, `tests/test_html_typo_lint.py` and this record to `D:\PC\Python\regex_pad_project`, preserving unrelated Unicode-normalization and user changes. No EXE rebuild or physical Windows/WordPress acceptance was performed.
