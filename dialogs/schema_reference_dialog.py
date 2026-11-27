"""同梱スキーマの参考表を表示するダイアログを提供する。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from dialogs.schema_help import load_schema_help_topics
from localization.translator import Translator

WINDOW_GAP = 8


class SchemaReferenceDialog(QDialog):
    """HTML、CSS、WordPressのスキーマから生成した表をモードレスで表示する。"""

    def __init__(
        self,
        standards_path: Path,
        translator: Translator,
        parent: QWidget | None = None,
    ) -> None:
        """言語、参照資料、表示タブを初期化する。"""
        super().__init__(parent)
        self.standards_path = standards_path
        self.translator = translator
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.resize(980, 680)

        self.tab_widget = QTabWidget(self)
        self.html_browser = self._create_browser()
        self.css_browser = self._create_browser()
        self.wordpress_browser = self._create_browser()
        self.tab_widget.addTab(self.html_browser, "")
        self.tab_widget.addTab(self.css_browser, "")
        self.tab_widget.addTab(self.wordpress_browser, "")

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close,
            self,
        )
        self.button_box.rejected.connect(self.close)

        layout = QVBoxLayout()
        layout.addWidget(self.tab_widget, 1)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        self.apply_language()

    def apply_language(self) -> None:
        """現在のアプリ言語で、生成したすべての表を読み直す。"""
        language_code = "en" if self.translator.language_code == "en" else "ja"
        html_topic, css_topic, wordpress_topic = load_schema_help_topics(
            self.standards_path,
            language_code,
        )
        html_title, html_body = html_topic
        css_title, css_body = css_topic
        wordpress_title, wordpress_body = wordpress_topic

        self.setWindowTitle(self.translator.text("schema_reference.title"))
        self.tab_widget.setTabText(0, html_title)
        self.tab_widget.setTabText(1, css_title)
        self.tab_widget.setTabText(2, wordpress_title)
        self.html_browser.setMarkdown(html_body)
        self.css_browser.setMarkdown(css_body)
        self.wordpress_browser.setMarkdown(wordpress_body)
        self.button_box.button(QDialogButtonBox.StandardButton.Close).setText(
            self.translator.text("schema_reference.close")
        )

    def place_next_to(self, target: QWidget) -> None:
        """画面に余裕があれば、参考表のウインドウをエディターの横へ置く。"""
        screen = target.screen()
        if screen is None:
            return
        available = screen.availableGeometry()
        target_frame = target.frameGeometry()
        reference_frame = self.frameGeometry()

        right_x = target_frame.right() + WINDOW_GAP
        left_x = target_frame.left() - reference_frame.width() - WINDOW_GAP
        if right_x + reference_frame.width() <= available.right() + 1:
            x = right_x
        elif left_x >= available.left():
            x = left_x
        else:
            x = max(
                available.left(),
                min(target_frame.center().x(), available.right() - reference_frame.width() + 1),
            )
        y = max(
            available.top(),
            min(target_frame.top(), available.bottom() - reference_frame.height() + 1),
        )
        self.move(x, y)

    def _create_browser(self) -> QTextBrowser:
        """参考表を表示するテキストブラウザーを作る。"""
        browser = QTextBrowser(self)
        browser.setOpenExternalLinks(False)
        return browser
