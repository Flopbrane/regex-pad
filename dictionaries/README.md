# Dictionary Format

RegexPad keeps bundled snippet dictionaries in this folder. Bundled dictionaries are read-only during normal use; user dictionaries are loaded from the folder selected in Options.

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
