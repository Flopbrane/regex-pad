from __future__ import annotations

import os
import sys

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, Qt
from PySide6.QtGui import QImage, QMouseEvent, QPainter, QWheelEvent
from PySide6.QtWidgets import QApplication, QPlainTextEdit

from editor.text_editor import TextEditor

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def app() -> QApplication:
    application = QApplication.instance()
    if application is None:
        application = QApplication(sys.argv)
    assert isinstance(application, QApplication)
    return application


def test_visible_whitespace_marks_are_empty_by_default(app: QApplication) -> None:
    _ = app
    editor = TextEditor()
    editor.setPlainText("a b\tc\n")

    assert editor.visible_whitespace_marks() == []


def test_visible_whitespace_marks_follow_individual_options(
    app: QApplication,
) -> None:
    _ = app
    editor = TextEditor()
    editor.setPlainText("a b\tc\nwide　space")

    editor.set_visible_whitespace_options(
        spaces_enabled=True,
        tabs_enabled=False,
        newlines_enabled=True,
    )

    assert [
        (mark.text_position, mark.marker) for mark in editor.visible_whitespace_marks()
    ] == [
        (1, "·"),
        (5, "↵"),
        (10, "□"),
    ]


def test_visible_whitespace_options_do_not_modify_text(app: QApplication) -> None:
    _ = app
    editor = TextEditor()
    source_text = "a b\tc\n"
    editor.setPlainText(source_text)

    editor.set_visible_whitespace_options(
        spaces_enabled=True,
        tabs_enabled=True,
        newlines_enabled=True,
    )

    assert editor.toPlainText() == source_text
    assert [
        (mark.text_position, mark.marker) for mark in editor.visible_whitespace_marks()
    ] == [
        (1, "·"),
        (3, "→"),
        (5, "↵"),
    ]


def test_visible_whitespace_marker_colors_are_configurable(
    app: QApplication,
) -> None:
    _ = app
    editor = TextEditor()

    editor.set_visible_whitespace_marker_colors(
        space_color="#d9d9d9",
        tab_color="#b6f2a5",
        newline_color="#ff9900",
    )

    assert editor._visible_whitespace_marker_color(" ") == "#d9d9d9"
    assert editor._visible_whitespace_marker_color("\u3000") == "#d9d9d9"
    assert editor._visible_whitespace_marker_color("\t") == "#b6f2a5"
    assert editor._visible_whitespace_marker_color("\n") == "#ff9900"


def test_editor_colors_apply_to_stylesheet_and_html_highlighter(
    app: QApplication,
) -> None:
    _ = app
    editor = TextEditor()

    editor.set_editor_colors(
        background_color="#101820",
        text_color="#f0f6ff",
        html_tag_color="#33ccff",
        wordpress_core_block_color="#99aabb",
    )

    assert editor.editor_background_color == "#101820"
    assert editor.editor_text_color == "#f0f6ff"
    assert editor.html_tag_color == "#33ccff"
    assert editor.wordpress_core_block_color == "#99aabb"
    assert "background-color: #101820" in editor.styleSheet()
    assert "color: #f0f6ff" in editor.styleSheet()


def test_visible_whitespace_paint_path_renders(app: QApplication) -> None:
    editor = TextEditor()
    source_text = "a b\tc\n"
    editor.setPlainText(source_text)
    editor.resize(320, 160)
    editor.set_visible_whitespace_options(
        spaces_enabled=True,
        tabs_enabled=True,
        newlines_enabled=True,
    )
    editor.show()
    app.processEvents()

    image = QImage(
        editor.viewport().size(),
        QImage.Format.Format_ARGB32,
    )
    editor.viewport().render(image)

    assert editor.toPlainText() == source_text


def test_visible_whitespace_paint_uses_local_utf16_positions(
    app: QApplication, monkeypatch: pytest.MonkeyPatch,
) -> None:
    editor = TextEditor()
    editor.resize(320, 160)
    editor.setPlainText("😀 a\nβ\tc\n")
    editor.set_visible_whitespace_options(
        spaces_enabled=True, tabs_enabled=True, newlines_enabled=True,
    )
    editor.show()
    app.processEvents()

    positions: set[tuple[int, str]] = set()
    original_paint = editor._paint_visible_whitespace_marker

    def record_marker(
        painter: QPainter, event_rect: QRect, cursor_position: int,
        marker: str, character: str,
    ) -> None:
        positions.add((cursor_position, character))
        original_paint(painter, event_rect, cursor_position, marker, character)

    monkeypatch.setattr(editor, "_paint_visible_whitespace_marker", record_marker)
    monkeypatch.setattr(
        editor, "toPlainText", lambda: pytest.fail("Painting copied the whole document"),
    )
    monkeypatch.setattr(
        editor, "text_position_to_cursor_position",
        lambda _position: pytest.fail("Painting scanned the whole document"),
    )
    image = QImage(editor.viewport().size(), QImage.Format.Format_ARGB32)
    editor.viewport().render(image)

    assert {(2, " "), (4, "\n"), (6, "\t"), (8, "\n")} <= positions


def test_fixed_column_wrap_overrides_wrap_mode_without_modifying_text(
    app: QApplication,
) -> None:
    _ = app
    editor = TextEditor()
    source_text = "abcdefghijklmnopqrstuvwxyz"
    editor.setPlainText(source_text)

    editor.set_word_wrap_enabled(False)
    editor.set_fixed_column_wrap_options(enabled=True, column=12)

    assert editor.toPlainText() == source_text
    assert editor.fixed_column_wrap_enabled is True
    assert editor.fixed_column_wrap_column == 12
    assert editor.lineWrapMode() == QPlainTextEdit.LineWrapMode.WidgetWidth
    assert editor.fixed_column_wrap_pixel_width() > 0

    editor.set_fixed_column_wrap_options(enabled=False, column=12)

    assert editor.lineWrapMode() == QPlainTextEdit.LineWrapMode.NoWrap


def test_fixed_wrap_scrolls_with_wheel_on_blank_margin_and_side_areas(
    app: QApplication,
) -> None:
    editor = TextEditor()
    source_text = ("x" * 120 + "\n") * 80
    editor.resize(1000, 300)
    editor.setPlainText(source_text)
    editor.set_fixed_column_wrap_options(enabled=True, column=20)
    editor.show()
    app.processEvents()

    scroll_bar = editor.verticalScrollBar()
    assert scroll_bar.maximum() > 0
    assert editor.viewport().geometry().right() + 100 < editor.width()
    targets = (
        (editor.viewport(), editor.viewport().rect().center()),
        (editor, QPoint(editor.viewport().geometry().right() + 100, 150)),
        (editor.line_number_area, editor.line_number_area.rect().center()),
        (editor.search_marker_area, editor.search_marker_area.rect().center()),
    )
    for target, point in targets:
        scroll_bar.setValue(0)
        global_point = target.mapToGlobal(point)
        wheel = QWheelEvent(
            QPointF(point), QPointF(global_point), QPoint(0, 0), QPoint(0, -120),
            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.ScrollUpdate, False,
        )
        QApplication.sendEvent(target, wheel)
        app.processEvents()
        assert scroll_bar.value() > 0
    assert editor.toPlainText() == source_text


def test_line_number_area_click_selects_line(app: QApplication) -> None:
    editor = TextEditor()
    editor.setPlainText("first\nsecond\nthird")
    editor.resize(320, 160)
    editor.show()
    app.processEvents()

    y_position = _block_center_y(editor, 1)
    event = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(4, y_position),
        QPointF(4, y_position),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )

    editor.line_number_area.mousePressEvent(event)

    assert editor.textCursor().selectedText() == "second"


def test_line_head_click_selects_line_when_line_numbers_hidden(
    app: QApplication,
) -> None:
    editor = TextEditor()
    editor.setPlainText("first\nsecond\nthird")
    editor.resize(320, 160)
    editor.set_line_numbers_enabled(False)
    editor.show()
    app.processEvents()

    y_position = _block_center_y(editor, 1)
    event = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(1, y_position),
        QPointF(1, y_position),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )

    editor.mousePressEvent(event)

    assert editor.textCursor().selectedText() == "second"


def _block_center_y(editor: TextEditor, block_number: int) -> float:
    block = editor.document().findBlockByNumber(block_number)
    block_geometry = editor.blockBoundingGeometry(block).translated(
        editor.contentOffset()
    )
    block_rect = editor.blockBoundingRect(block)
    return block_geometry.top() + (block_rect.height() / 2)
