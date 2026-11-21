"""Regression checks for dragging a compact input beyond its viewport."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6 import QtCore, QtGui, QtTest, QtWidgets

from dialogs.regex_input_edit import RegexInputEdit


@pytest.fixture(scope="module")
def app() -> QtWidgets.QApplication:
    application = QtWidgets.QApplication.instance()
    if application is None:
        application = QtWidgets.QApplication([])
    assert isinstance(application, QtWidgets.QApplication)
    return application


def settle(app: QtWidgets.QApplication) -> None:
    """Allow the queued layout and height updates to finish."""
    for _ in range(5):
        app.processEvents()


@pytest.mark.parametrize("regex_enabled", [False, True])
def test_single_line_has_no_scroll_step_past_its_only_block(app, regex_enabled) -> None:
    edit = RegexInputEdit()
    try:
        edit.resize(300, edit.height())
        edit.set_regex_highlighting_enabled(regex_enabled)
        edit.setText(r"line-(\d+)")
        edit.show()
        settle(app)
        assert edit.verticalScrollBar().maximum() == 0
        assert edit.firstVisibleBlock().isValid()
    finally:
        edit.close()


def test_drag_outside_keeps_input_visible_and_editable(app) -> None:
    edit = RegexInputEdit()
    text = r"line-(\d+)"
    original_mouse_position = QtGui.QCursor.pos()
    try:
        edit.resize(300, edit.height())
        edit.setText(text)
        edit.show()
        edit.activateWindow()
        edit.setFocus()
        settle(app)
        edit.setCursorPosition(len(text))
        viewport = edit.viewport()
        QtTest.QTest.mousePress(
            viewport, QtCore.Qt.MouseButton.LeftButton,
            pos=edit.cursorRect().center(),
        )
        outside = QtCore.QPointF(viewport.width() + 40, viewport.height() + 40)
        QtGui.QCursor.setPos(viewport.mapToGlobal(outside.toPoint()))
        move_event = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseMove,
            outside,
            QtCore.QPointF(viewport.mapToGlobal(outside.toPoint())),
            QtCore.Qt.MouseButton.NoButton,
            QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.KeyboardModifier.NoModifier,
        )
        QtWidgets.QApplication.sendEvent(viewport, move_event)
        QtTest.QTest.qWait(200)
        settle(app)
        assert edit.firstVisibleBlock().isValid()
        QtTest.QTest.mouseRelease(
            viewport, QtCore.Qt.MouseButton.LeftButton, pos=outside.toPoint(),
        )
        settle(app)
        assert edit.text() == text
        assert edit.firstVisibleBlock().isValid()
        assert viewport.rect().intersects(edit.cursorRect())
        edit.setCursorPosition(len(text))
        QtTest.QTest.keyClicks(edit, "X")
        assert edit.text() == text + "X"
    finally:
        edit.close()
        QtGui.QCursor.setPos(original_mouse_position)


def test_legacy_tight_height_cannot_leave_an_invalid_first_block(app) -> None:
    edit = RegexInputEdit()
    try:
        edit.setText("sample")
        edit.show()
        settle(app)
        # Recreate the old fixed padding, even after the sizing fix.
        edit.setFixedHeight(edit.fontMetrics().lineSpacing() + 12)
        settle(app)
        edit.verticalScrollBar().setValue(edit.verticalScrollBar().maximum())
        settle(app)
        assert edit.firstVisibleBlock().isValid()
        assert edit.text() == "sample"
    finally:
        edit.close()


def test_multiline_input_still_scrolls_to_later_blocks(app) -> None:
    edit = RegexInputEdit()
    text = "\n".join(f"line {number}" for number in range(20))
    try:
        edit.setText(text)
        edit.show()
        settle(app)
        scroll_bar = edit.verticalScrollBar()
        assert scroll_bar.maximum() > 0
        scroll_bar.setValue(scroll_bar.maximum())
        settle(app)
        assert edit.firstVisibleBlock().isValid()
        assert edit.firstVisibleBlock().blockNumber() > 0
        assert edit.text() == text
    finally:
        edit.close()
