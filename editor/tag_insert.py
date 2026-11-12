from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SELECTION_PLACEHOLDER = "{selection}"
CURSOR_PLACEHOLDER = "{cursor}"
VALID_PLACEHOLDERS = {"selection", "cursor"}
PLACEHOLDER_PATTERN = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
WORDPRESS_GROUP_LABEL_KEY = "tag.group.wordpress_html"
WORDPRESS_MODE_NORMAL_KEY = "tag.wordpress_mode.normal"
WORDPRESS_MODE_BUSINESS_KEY = "tag.wordpress_mode.business"
WORDPRESS_MODE_HIGH_SECURITY_KEY = "tag.wordpress_mode.high_security"
WORDPRESS_MODE_LABEL_KEYS = (
    WORDPRESS_MODE_NORMAL_KEY,
    WORDPRESS_MODE_BUSINESS_KEY,
    WORDPRESS_MODE_HIGH_SECURITY_KEY,
)
WORDPRESS_BUSINESS_EXCLUDED_LABEL_KEYS = {
    "tag.wordpress.html_code_box",
    "tag.wordpress.image_row_html_block",
    "tag.wordpress.float_left_image_block",
    "tag.wordpress.float_right_image_block",
}
WORDPRESS_HIGH_SECURITY_LABEL_KEYS = {
    "tag.wordpress.paragraph_block",
    "tag.wordpress.heading2_block",
    "tag.wordpress.heading3_block",
    "tag.wordpress.soft_subheading_paragraph",
    "tag.wordpress.list_block",
    "tag.wordpress.quote_block",
    "tag.wordpress.code_block",
    "tag.wordpress.preformatted_block",
    "tag.wordpress.separator_block",
    "tag.wordpress.decorative_separator_block",
    "tag.wordpress.spacer_block",
    "tag.wordpress.link_block",
    "tag.wordpress.custom_frame_block",
    "tag.wordpress.notice_frame_block",
    "tag.wordpress.info_frame_block",
    "tag.wordpress.important_frame_block",
    "tag.wordpress.table_block",
    "tag.wordpress.columns_2_text_block",
    "tag.wordpress.columns_3_text_block",
}
WORDPRESS_DICTIONARY_FILE_NAME = "wordpress_html_dict.json"


@dataclass(frozen=True)
class TagSnippetParameter:
    name: str
    required: bool = False
    kind: str = "text"
    description_key: str = ""


@dataclass(frozen=True)
class TagSnippet:
    label_key: str
    hint_key: str
    template: str
    parameters: tuple[TagSnippetParameter, ...] = ()
    default_selection: str = ""

    def render(self, selected_text: str) -> tuple[str, int]:
        replacement_text = selected_text if selected_text else self.default_selection
        rendered_text = self.template.replace(SELECTION_PLACEHOLDER, replacement_text)
        cursor_position = rendered_text.find(CURSOR_PLACEHOLDER)
        if cursor_position == -1:
            return rendered_text, len(rendered_text)
        return rendered_text.replace(CURSOR_PLACEHOLDER, ""), cursor_position


@dataclass(frozen=True)
class TagSnippetGroup:
    label_key: str
    snippets: tuple[TagSnippet, ...]


def tag_snippet_groups(
    dictionaries_path: Path | None = None,
    resources_path: Path | None = None,
) -> tuple[TagSnippetGroup, ...]:
    dictionaries_path = (
        dictionaries_path or Path(__file__).resolve().parent.parent / "dictionaries"
    )
    resources_path = resources_path or Path(__file__).resolve().parent.parent / "resources"
    groups = (
        TagSnippetGroup(
            "tag.group.html",
            _load_snippets_from_json(dictionaries_path / "html_dict.json"),
        ),
        TagSnippetGroup(
            "tag.group.markdown",
            _load_snippets_from_json(dictionaries_path / "markdown_dict.json"),
        ),
        TagSnippetGroup(
            WORDPRESS_GROUP_LABEL_KEY,
            _load_snippets_from_json(dictionaries_path / "wordpress_html_dict.json"),
        ),
    )
    _validate_translation_keys(groups, resources_path)
    return groups


def ordered_tag_snippet_groups(
    save_file_path: Path | None,
    dictionaries_path: Path | None = None,
) -> tuple[TagSnippetGroup, ...]:
    groups = tag_snippet_groups(dictionaries_path)
    preferred_label_key = _preferred_group_label_key(save_file_path)
    if preferred_label_key is None:
        return groups
    return tuple(
        sorted(
            groups,
            key=lambda group: 0 if group.label_key == preferred_label_key else 1,
        )
    )


def wordpress_tag_snippet(
    label_key: str,
    dictionaries_path: Path | None = None,
) -> TagSnippet:
    """Load one WordPress snippet by label key from the active dictionary."""
    dictionaries_path = (
        dictionaries_path or Path(__file__).resolve().parent.parent / "dictionaries"
    )
    load_file_path = dictionaries_path / WORDPRESS_DICTIONARY_FILE_NAME
    for snippet in _load_snippets_from_json(load_file_path):
        if snippet.label_key == label_key:
            return snippet
    raise ValueError(
        f"WordPress dictionary item was not found: {label_key!r} ({load_file_path})"
    )


def tag_snippet_category_key(group_label_key: str, snippet: TagSnippet) -> str:
    label_key = snippet.label_key
    if group_label_key == "tag.group.html":
        return _html_category_key(label_key)
    if group_label_key == "tag.group.markdown":
        return _markdown_category_key(label_key)
    if group_label_key == WORDPRESS_GROUP_LABEL_KEY:
        return _wordpress_category_key(label_key)
    return "tag.category.utility"


def wordpress_mode_label_keys() -> tuple[str, ...]:
    return WORDPRESS_MODE_LABEL_KEYS


def wordpress_snippets_for_mode(
    snippets: tuple[TagSnippet, ...],
    mode_label_key: str,
) -> tuple[TagSnippet, ...]:
    return tuple(
        snippet for snippet in snippets if mode_label_key in wordpress_mode_keys(snippet)
    )


def wordpress_mode_keys(snippet: TagSnippet) -> tuple[str, ...]:
    mode_keys = [WORDPRESS_MODE_NORMAL_KEY]
    if snippet.label_key not in WORDPRESS_BUSINESS_EXCLUDED_LABEL_KEYS:
        mode_keys.append(WORDPRESS_MODE_BUSINESS_KEY)
    if snippet.label_key in WORDPRESS_HIGH_SECURITY_LABEL_KEYS:
        mode_keys.append(WORDPRESS_MODE_HIGH_SECURITY_KEY)
    return tuple(mode_keys)


def _preferred_group_label_key(save_file_path: Path | None) -> str | None:
    if save_file_path is None:
        return None

    suffixes = [suffix.lower() for suffix in save_file_path.suffixes]
    file_name = save_file_path.name.lower()
    if file_name.endswith(".wp.html"):
        return WORDPRESS_GROUP_LABEL_KEY
    if ".md" in suffixes or ".markdown" in suffixes:
        return "tag.group.markdown"
    if ".html" in suffixes or ".htm" in suffixes:
        return "tag.group.html"
    return None


def _html_category_key(label_key: str) -> str:
    if label_key in {
        "tag.html.paragraph",
        "tag.html.heading1",
        "tag.html.heading2",
        "tag.html.heading3",
        "tag.html.heading4",
        "tag.html.header",
        "tag.html.main",
    }:
        return "tag.category.basic"
    if label_key in {
        "tag.html.strong",
        "tag.html.emphasis",
        "tag.html.blockquote",
        "tag.html.small",
        "tag.html.mark",
    }:
        return "tag.category.text"
    if label_key in {
        "tag.html.link",
        "tag.html.link_blank",
        "tag.html.image",
        "tag.html.figure",
        "tag.html.video",
        "tag.html.audio",
    }:
        return "tag.category.link_image"
    if label_key in {
        "tag.html.unordered_list",
        "tag.html.ordered_list",
    }:
        return "tag.category.lists"
    if label_key in {
        "tag.html.code",
        "tag.html.pre_code",
    }:
        return "tag.category.code"
    if label_key in {
        "tag.html.div",
        "tag.html.span",
        "tag.html.details",
        "tag.html.table_2x2",
        "tag.html.nav",
        "tag.html.section",
        "tag.html.article",
        "tag.html.aside",
        "tag.html.footer",
        "tag.html.form_basic",
        "tag.html.button",
    }:
        return "tag.category.layout"
    return "tag.category.utility"


def _markdown_category_key(label_key: str) -> str:
    if label_key in {
        "tag.markdown.heading1",
        "tag.markdown.heading2",
        "tag.markdown.heading3",
        "tag.markdown.heading4",
        "tag.markdown.bold",
        "tag.markdown.italic",
        "tag.markdown.strikethrough",
    }:
        return "tag.category.text"
    if label_key in {
        "tag.markdown.link",
        "tag.markdown.image",
    }:
        return "tag.category.link_image"
    if label_key in {
        "tag.markdown.inline_code",
        "tag.markdown.code_block",
        "tag.markdown.code_block_python",
        "tag.markdown.code_block_html",
        "tag.markdown.code_block_css",
        "tag.markdown.code_block_javascript",
        "tag.markdown.code_block_json",
        "tag.markdown.code_block_powershell",
        "tag.markdown.code_block_bash",
        "tag.markdown.code_block_sql",
    }:
        return "tag.category.code"
    if label_key in {
        "tag.markdown.quote",
        "tag.markdown.bullet",
        "tag.markdown.numbered",
        "tag.markdown.task_unchecked",
        "tag.markdown.task_checked",
    }:
        return "tag.category.lists"
    if label_key in {
        "tag.markdown.table_2x2",
        "tag.markdown.table_3x2",
    }:
        return "tag.category.layout"
    return "tag.category.utility"


def _wordpress_category_key(label_key: str) -> str:
    if label_key in {
        "tag.wordpress.paragraph_block",
        "tag.wordpress.heading2_block",
        "tag.wordpress.heading3_block",
        "tag.wordpress.soft_subheading_paragraph",
        "tag.wordpress.list_block",
        "tag.wordpress.quote_block",
    }:
        return "tag.category.text"
    if label_key in {
        "tag.wordpress.link_block",
    }:
        return "tag.category.link_image"
    if label_key in {
        "tag.wordpress.image_block",
        "tag.wordpress.media_text_left_block",
        "tag.wordpress.media_text_right_block",
        "tag.wordpress.gallery_3_block",
        "tag.wordpress.columns_3_images_block",
        "tag.wordpress.image_row_html_block",
        "tag.wordpress.float_left_image_block",
        "tag.wordpress.float_right_image_block",
        "tag.wordpress.video_block",
        "tag.wordpress.audio_block",
    }:
        return "tag.category.media"
    if label_key in {
        "tag.wordpress.code_block",
        "tag.wordpress.preformatted_block",
        "tag.wordpress.html_code_box",
    }:
        return "tag.category.code"
    if label_key in {
        "tag.wordpress.separator_block",
        "tag.wordpress.decorative_separator_block",
        "tag.wordpress.spacer_block",
        "tag.wordpress.buttons_block",
        "tag.wordpress.custom_frame_block",
        "tag.wordpress.notice_frame_block",
        "tag.wordpress.info_frame_block",
        "tag.wordpress.important_frame_block",
        "tag.wordpress.table_block",
        "tag.wordpress.details_html_block",
        "tag.wordpress.columns_2_text_block",
        "tag.wordpress.columns_3_text_block",
    }:
        return "tag.category.layout"
    return "tag.category.utility"


def _load_snippets_from_json(load_file_path: Path) -> tuple[TagSnippet, ...]:
    load_data = json.loads(load_file_path.read_text(encoding="utf-8"))
    if not isinstance(load_data, list):
        raise TypeError(f"Dictionary must contain a list: {load_file_path}")

    snippets: list[TagSnippet] = []
    seen_label_keys: dict[str, int] = {}
    for index, item in enumerate(load_data, start=1):
        if not isinstance(item, dict):
            raise TypeError(
                "Dictionary item must be an object: "
                f"{_dictionary_item_context(load_file_path, index)}"
            )
        snippet = _snippet_from_dict(item, load_file_path, index)
        if snippet.label_key in seen_label_keys:
            raise ValueError(
                "Dictionary item has duplicated label_key "
                f"{snippet.label_key!r}: "
                f"{_dictionary_item_context(load_file_path, index)} "
                f"(first seen at item #{seen_label_keys[snippet.label_key]})"
            )
        seen_label_keys[snippet.label_key] = index
        snippets.append(snippet)
    return tuple(snippets)


def _snippet_from_dict(
    item: dict[str, Any],
    load_file_path: Path,
    index: int,
) -> TagSnippet:
    context = _dictionary_item_context(load_file_path, index)
    missing_keys = [
        key for key in ("label_key", "hint_key", "template") if key not in item
    ]
    if missing_keys:
        raise ValueError(
            "Dictionary item is missing required key(s) "
            f"{', '.join(missing_keys)}: {context}"
        )
    label_key = item.get("label_key")
    hint_key = item.get("hint_key")
    template = item.get("template")
    if (
        not isinstance(label_key, str)
        or not isinstance(hint_key, str)
        or not isinstance(template, str)
    ):
        raise TypeError(
            "Dictionary item requires string label_key, hint_key, and template: "
            f"{context}"
        )
    if not label_key.strip() or not hint_key.strip() or not template:
        raise ValueError(
            "Dictionary item requires non-empty label_key, hint_key, and template: "
            f"{context}"
        )
    parameters = _parameters_from_dict(item, context)
    default_selection = item.get("default_selection", "")
    if not isinstance(default_selection, str):
        raise TypeError(
            "Dictionary item default_selection must be a string: "
            f"{context}"
        )
    _validate_template_placeholders(template, context)
    return TagSnippet(label_key, hint_key, template, parameters, default_selection)


def _parameters_from_dict(
    item: dict[str, Any],
    context: str,
) -> tuple[TagSnippetParameter, ...]:
    raw_parameters = item.get("parameters", [])
    if not isinstance(raw_parameters, list):
        raise TypeError(f"Dictionary item parameters must be a list: {context}")

    parameters: list[TagSnippetParameter] = []
    seen_names: set[str] = set()
    for index, raw_parameter in enumerate(raw_parameters, start=1):
        parameter_context = f"{context} parameter #{index}"
        if not isinstance(raw_parameter, dict):
            raise TypeError(f"Dictionary parameter must be an object: {parameter_context}")

        name = raw_parameter.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                "Dictionary parameter requires non-empty name: "
                f"{parameter_context}"
            )
        clean_name = name.strip()
        if clean_name in seen_names:
            raise ValueError(
                "Dictionary parameter has duplicated name "
                f"{clean_name!r}: {parameter_context}"
            )
        seen_names.add(clean_name)

        required = raw_parameter.get("required", False)
        if not isinstance(required, bool):
            raise TypeError(
                "Dictionary parameter required must be true or false: "
                f"{parameter_context}"
            )

        kind = raw_parameter.get("kind", "text")
        description_key = raw_parameter.get("description_key", "")
        if not isinstance(kind, str) or not kind.strip():
            raise ValueError(
                "Dictionary parameter kind must be a non-empty string: "
                f"{parameter_context}"
            )
        if not isinstance(description_key, str):
            raise TypeError(
                "Dictionary parameter description_key must be a string: "
                f"{parameter_context}"
            )

        parameters.append(
            TagSnippetParameter(
                name=clean_name,
                required=required,
                kind=kind.strip(),
                description_key=description_key.strip(),
            )
        )
    return tuple(parameters)


def _validate_template_placeholders(template: str, context: str) -> None:
    cursor_count = template.count(CURSOR_PLACEHOLDER)
    if cursor_count > 1:
        raise ValueError(f"Dictionary item has duplicated cursor placeholder: {context}")

    broken_placeholders = [
        placeholder
        for placeholder in ("selection", "cursor")
        if (
            f"{{{placeholder}" in template
            and f"{{{placeholder}}}" not in template
        )
        or (
            f"{placeholder}}}" in template
            and f"{{{placeholder}}}" not in template
        )
    ]
    if broken_placeholders:
        raise ValueError(
            "Dictionary item has broken placeholder(s) "
            f"{', '.join(broken_placeholders)}: {context}"
        )

    unknown_placeholders = sorted(
        {
            placeholder
            for placeholder in PLACEHOLDER_PATTERN.findall(template)
            if placeholder not in VALID_PLACEHOLDERS
        }
    )
    if unknown_placeholders:
        raise ValueError(
            "Dictionary item has unknown placeholder(s) "
            f"{', '.join(unknown_placeholders)}: {context}"
        )


def _validate_translation_keys(
    groups: tuple[TagSnippetGroup, ...],
    resources_path: Path,
) -> None:
    required_keys = {
        group.label_key
        for group in groups
    } | {
        key
        for group in groups
        for snippet in group.snippets
        for key in (snippet.label_key, snippet.hint_key)
    } | {
        parameter.description_key
        for group in groups
        for snippet in group.snippets
        for parameter in snippet.parameters
        if parameter.description_key
    }
    for language_code in ("ja", "en"):
        resource_path = resources_path / f"app_text_{language_code}.json"
        resource_data = json.loads(resource_path.read_text(encoding="utf-8"))
        if not isinstance(resource_data, dict):
            raise TypeError(f"Translation resource must contain an object: {resource_path}")
        missing_keys = sorted(key for key in required_keys if key not in resource_data)
        if missing_keys:
            raise ValueError(
                "Dictionary translation key(s) are missing from "
                f"{resource_path}: {', '.join(missing_keys)}"
            )


def _dictionary_item_context(load_file_path: Path, index: int) -> str:
    return f"{load_file_path} item #{index}"
