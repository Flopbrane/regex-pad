from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from scripts.build_wordpress_class_reference import (
    ClassEvidence,
    _class_entry,
    _ClassHtmlParser,
    _record_css,
)

REFERENCE_PATH = (
    Path(__file__).resolve().parent.parent
    / "dictionaries"
    / "standards"
    / "wordpress_class_tag_reference.json"
)
SERIALIZATION_REFERENCE_PATH = (
    Path(__file__).resolve().parent.parent
    / "dictionaries"
    / "standards"
    / "wordpress_block_serialization_reference.json"
)


def test_reference_contains_verified_table_classes_and_business_sample() -> None:
    reference = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    classes = reference["classes"]

    assert reference["schema_version"] == 1
    assert reference["summary"]["class_count"] == len(classes)
    assert len(classes) >= 4_000
    assert classes["has-fixed-layout"]["tag_scope"] == "strict"
    assert classes["has-fixed-layout"]["allowed_tags"] == ["table"]
    assert classes["wp-block-table"]["allowed_tags"] == ["figure"]
    assert classes["wp-block-group"]["tag_scope"] == "strict"
    assert classes["wp-block-group"]["allowed_tags"] == [
        "article",
        "aside",
        "div",
        "footer",
        "header",
        "main",
        "section",
    ]
    assert "div" in classes["wp-block-group"]["observed_html_tags"]
    assert "div" in classes["has-accent-2-background-color"]["observed_html_tags"]
    for class_name in (
        "has-base-color",
        "has-text-color",
        "has-background",
        "has-link-color",
    ):
        assert classes[class_name]["tag_scope"] == "advisory"
        assert classes[class_name]["allowed_tags"] == ["*"]
        assert "table" in classes[class_name]["observed_html_tags"]

    assert "blog-officelist" in classes
    assert "business_sample_css" in classes["blog-officelist"]["source_groups"]


def test_serialization_reference_records_verified_group_class_and_style_rules() -> None:
    reference = json.loads(SERIALIZATION_REFERENCE_PATH.read_text(encoding="utf-8"))
    group_rules = reference["blocks"]["group"]
    paragraph_rules = reference["blocks"]["paragraph"]

    assert reference["status"] == "verified_examples_only"
    assert group_rules["required_classes"] == ["wp-block-group"]
    assert {
        rule["json_path"] for rule in group_rules["attribute_class_rules"]
    } == {"backgroundColor", "fontSize"}
    assert "style.spacing.blockGap" in group_rules["verified_non_inline_paths"]
    assert any(
        rule == {
            "json_path": "style.spacing.padding.left",
            "css_property": "padding-left",
            "value_transform": "wordpress_preset_variable",
        }
        for rule in group_rules["style_rules"]
    )
    assert any(
        rule["json_path"] == "style.border.top.width"
        and rule["css_property"] == "border-top-width"
        for rule in paragraph_rules["style_rules"]
    )


def test_generator_keeps_css_tag_evidence_advisory_until_core_save_is_audited() -> None:
    classes: dict[str, ClassEvidence] = defaultdict(ClassEvidence)

    _record_css(
        "table.sample-table { width: 100%; } .shared-color { color: red; }",
        "sample.css",
        "business_sample_css",
        classes,
    )
    parser = _ClassHtmlParser("sample.html", "business_sample_html", classes)
    parser.feed('<table class="sample-table shared-color"></table>')
    parser.close()

    table_entry = _class_entry(classes["sample-table"])
    shared_entry = _class_entry(classes["shared-color"])
    assert table_entry["tag_scope"] == "advisory"
    assert table_entry["selector_tags"] == ["table"]
    assert table_entry["observed_html_tags"] == ["table"]
    assert shared_entry["allowed_tags"] == ["*"]
