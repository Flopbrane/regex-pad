# Dictionary Format

RegexPad keeps bundled snippet dictionaries in this folder. Bundled dictionaries are read-only during normal use; user dictionaries are loaded from the folder selected in Options.

From the Search/Replace Preset editor, **Edit insertion dictionaries** opens a
field/JSON editor for `html_dict.json`, `markdown_dict.json`,
`wordpress_html_dict.json`, and `paragraph_insert_dict.json`. Saving validates
the candidate and writes a user copy in `user_dictionaries/` beside the app,
or in the user dictionary folder configured in Options. The bundled copy and
Linter references (`lint_reference.json` and `standards/`) are not edited.

## Tag Snippet Dictionaries

The following bundled files use the same snippet format:

- `html_dict.json`
- `markdown_dict.json`
- `wordpress_html_dict.json`

Each item is an object with these required fields:

```json
{
  "label_key": "tag.html.paragraph",
  "hint_key": "tag.hint.html.paragraph",
  "template": "<p>{selection}{cursor}</p>"
}
```

- `label_key`: translation key for the visible snippet name.
- `hint_key`: translation key for the hover hint and picker hint.
- `template`: inserted text.
- `parameters`: optional structured metadata for editable values in the snippet.

Supported placeholders:

- `{selection}`: selected text, or empty text when there is no selection.
- `{cursor}`: final cursor position after insertion. Use at most one.

Validation rejects missing required keys, empty required values, duplicate `label_key` values within one dictionary, duplicate `{cursor}` placeholders, broken placeholders, unknown placeholders, and missing Japanese or English translation keys.

Optional `parameters` entries use this minimum format:

```json
{
  "name": "href",
  "required": true,
  "kind": "url",
  "description_key": "tag.parameter.href"
}
```

- `name`: required non-empty identifier for the editable value.
- `required`: optional boolean. Defaults to `false`.
- `kind`: optional non-empty string such as `text`, `url`, `number`, or `choice`. Defaults to `text`.
- `description_key`: optional translation key for future guided editing and lint hints.

Validation rejects non-list `parameters`, non-object parameter entries, empty parameter names, duplicate parameter names within one snippet, non-boolean `required` values, empty `kind` values, non-string `description_key` values, and missing translations for non-empty `description_key` values.

Current policy for user dictionaries:

- User dictionaries use the same `label_key` / `hint_key` format as bundled dictionaries.
- Direct `label` / `hint` text is not accepted yet.
- Direct labels may be reconsidered later for plugin-like dictionaries, but that needs a separate format decision so localization behavior stays predictable.

## Paragraph Insertion Dictionary

`paragraph_insert_dict.json` is the single source for the right-click **Paragraph Split** insertion route. Its operation keys match the visible command-key suffixes:

- `insert_spacer`
- `insert_html`
- `decorated_block`

Every operation contains:

- `search`: regular expression for text on which the insertion may run.
- `exclude`: optional regular expression that blocks overlapping input.
- `replacement`: exact inserted template. `{selection}` receives transformed selected text, `{cursor}` sets the final cursor, and declared parameters such as `{height}` come from `default_parameters`.
- `content_transform`: the non-presentational transform (`none`, `code`, or `decorated`). Search and replacement strings used by these transforms are under `grammar` in the same JSON file.
- `selection`: whether non-empty selection is allowed, whether it expands to complete lines, and the separate search/exclusion rules for an empty cursor position.
- `error_key`: bilingual application-text key used by the insertion Linter when the operation is unavailable.

The `grammar` object also supplies the WordPress paragraph-block search, `<p>` content search, paragraph replacement template, block separator, `<br>` cleanup rules, and structural diagnostic keys. Python owns range safety, cursor placement and Undo grouping; it does not own completed WordPress block text.

`shortcut_insertions` supplies the fixed text for `F8`, `F9`, `Ctrl+B`, `Ctrl+U`, and the text-color shortcuts. `{selection}` places selected text, `{cursor}` marks where the caret ends up, and `{value}` receives the selected color. `inline_underline` defaults to `<u style="">{selection}{cursor}</u>`. The shortcut keys, selection handling, and Undo grouping remain in Python. An older user dictionary without this section uses the bundled templates; a user dictionary can override individual entries.

When a selected user-dictionary folder contains `paragraph_insert_dict.json`, Paragraph Split uses it. If that optional file is absent, RegexPad uses the bundled paragraph dictionary so existing user-dictionary folders remain compatible.

## Typo Lint Reference

`lint_reference.json` is not a snippet dictionary. It is loaded once at startup into a cache and is used by HTML / WordPress typo linting.

It contains:

- `wordpress_core_blocks`: valid WordPress core block names such as `paragraph`, `group`, and `list-item`.
- `wordpress_block_attributes`: valid `{}` JSON parameter names for each WordPress core block.
- `html_tags`: valid HTML tag names.
- `html_attributes`: valid HTML attribute names.
- `global_html_attributes`: valid attributes that can appear on ordinary HTML tags.
- `html_attributes_by_tag`: valid tag-specific HTML attributes such as `href` for `a` and `src` for `img`.
- `allowed_attribute_prefixes`: prefixes such as `aria-` and `data-`.

Add entries here when RegexPad should treat a tag, block, or attribute spelling as valid.

### WordPress class / HTML tag reference

`standards/wordpress_class_tag_reference.json` is generated from the bundled
WordPress core block CSS, the saved business-site sample under `sample/`, and
verified WordPress HTML examples. It records each discovered class with:

- `tag_scope`: `strict` only when WordPress core save output confirms the tag;
  otherwise `advisory`.
- `allowed_tags`: tags enforced by the Linter for a strict entry, or `*` for an
  advisory entry.
- `selector_tags`: tags explicitly paired with the class in CSS selectors.
- `observed_html_tags`: tags on which saved HTML actually used the class.
- source groups, source files, evidence counts, and audited core-save sources.

Custom class names remain valid. Absence from this reference is not a warning.
Advisory entries are not treated as an exhaustive tag allowlist. The Linter
currently checks only strict relationships, including `has-fixed-layout` on
`table`, `wp-block-table` on `figure`, and `wp-block-group` on the root tags
supported by the core Group block.

`standards/wordpress_block_serialization_reference.json` is the verified
per-block JSON-to-HTML correspondence table. It records only relationships
observed in accepted saved block examples. The current Group entry covers its
root class, `backgroundColor` and `fontSize` classes, border/spacing inline
styles, preset-variable conversion, and the JSON paths such as `layout` and
`style.spacing.blockGap` that the verified example does not repeat inline.
The Paragraph entry records the border styles proven by the decorated Group
children. These rules support Linter consistency checks and can later supply
class-insertion hints; they are not inferred from one site's CSS.

The verified Button entry distinguishes three HTML targets: the outer
`wp-block-buttons` container, the child `wp-block-button` wrapper, and the
inner `a`/`button` element carrying `wp-block-button__link`. Its confirmed
rules cover text/background/link/font-size classes and the link element's
border width. `style.dimensions.width` is recorded as present in JSON but not
repeated as an inline style in that saved example.

The verified Quote entry uses a `blockquote.wp-block-quote` root and records
its background classes, four corner radii, three one-pixel sides, and the
left border's preset color and width. Its child Paragraph evidence adds
background classes and four margin properties to the Paragraph rules. The
separate Pullquote entry uses `figure.wp-block-pullquote` and records its
background, overall border width, and corner radii; its inner `blockquote`,
`p`, and `cite` are saved by the Pullquote block itself rather than as child
WordPress block comments.

The two verified Accordion examples record the complete parent chain
`accordion > accordion-item > accordion-heading / accordion-panel`, the
heading's nested toggle/title/icon elements, background and font-size classes,
and the demonstrated heading border width. `has-icon` and `has-icon-right` are
recorded as observed default-context classes rather than unconditional classes:
the core context may hide the icon or move it to the left.

The verified Columns example records `columns > column` as the required parent
chain and preserves three different child cases: Paragraph, Separator, and
Buttons/Button. The default Separator is saved as
`hr.wp-block-separator.has-alpha-channel-opacity`. WordPress core also permits
the Separator's `tagName` to be `div`, so both `hr` and `div` remain valid for
the two separator-specific classes. Width, vertical alignment, gap, and other
Columns decoration rules are intentionally not inferred from this undecorated
example.

The verified decorated Paragraph example records text/background/link/font
classes, the boolean `fitText` class, border widths, four-sided margin and
padding, and the demonstrated typography properties. The link hover preset is
stored in block JSON but is not repeated as an inline declaration in the saved
Paragraph HTML, so it is recorded as a verified non-inline path.

Regenerate the checked-in reference with the required Python interpreter:

```powershell
D:\Dev\venvs\venv_txt_edit312\Scripts\python.exe scripts\build_wordpress_class_reference.py `
  --wordpress-zip runtime\wordpress-preview\wordpress.zip `
  --sample-dir "sample\AIに気軽に触って♪3 - キャリカク_files" `
  --extra-html "docs_jp\example of the correct approach to table core control.wp_html" `
  --extra-html "tests\group_block_flex_nowrap_correct.wp_html" `
  --extra-html "tests\group_block_decorated_correct.wp_html" `
  --extra-html "tests\button_block_decorated_correct.wp_html" `
  --extra-html "tests\quote_block_decorated_correct.wp_html" `
  --extra-html "tests\pullquote_block_decorated_correct.wp_html" `
  --extra-html "tests\accordion_block_background_font_correct.wp_html" `
  --extra-html "tests\accordion_block_border_correct.wp_html" `
  --extra-html "tests\columns_block_mixed_content_correct.wp_html" `
  --extra-html "tests\paragraph_block_decorated_correct.wp_html" `
  --source-root . `
  --output dictionaries\standards\wordpress_class_tag_reference.json
```
