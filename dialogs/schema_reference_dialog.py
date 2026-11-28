"""同梱スキーマの参考表を表示するダイアログを提供する。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
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
        self.browsers = (self.html_browser, self.css_browser, self.wordpress_browser)
        self.selected_sections = [0] * self.tab_widget.count()
        self.section_label = QLabel(self)
        self.section_selector = QComboBox(self)
        self.section_label.setBuddy(self.section_selector)
        section_layout = QHBoxLayout()
        section_layout.addWidget(self.section_label)
        section_layout.addWidget(self.section_selector, 1)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close,
            self,
        )
        self.button_box.rejected.connect(self.close)

        layout = QVBoxLayout()
        layout.addLayout(section_layout)
        layout.addWidget(self.tab_widget, 1)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        self.apply_language()
        self.tab_widget.currentChanged.connect(self._show_tab_sections)
        self.section_selector.currentIndexChanged.connect(self._select_section)

    def apply_language(self) -> None:
        """現在のアプリ言語で、生成したすべての表を読み直す。"""
        language_code = "en" if self.translator.language_code == "en" else "ja"
        self.topics = load_schema_help_topics(
            self.standards_path,
            language_code,
        )
        self.setWindowTitle(self.translator.text("schema_reference.title"))
        self.section_label.setText(self.translator.text("schema_reference.category"))
        for index, (browser, topic) in enumerate(zip(self.browsers, self.topics, strict=True)):
            self.tab_widget.setTabText(index, topic.title)
            if self.selected_sections[index] > len(topic.sections):
                self.selected_sections[index] = 0
            browser.setMarkdown(topic.markdown(self.selected_sections[index]))
        self._show_tab_sections(self.tab_widget.currentIndex())
        self.button_box.button(QDialogButtonBox.StandardButton.Close).setText(
            self.translator.text("schema_reference.close")
        )

    def _show_tab_sections(self, tab_index: int) -> None:
        """現在のタブの分類を一覧し、前に選んだ分類を表示する。"""
        if tab_index < 0:
            return
        sections = self.topics[tab_index].sections
        with QSignalBlocker(self.section_selector):
            self.section_selector.clear()
            self.section_selector.addItem(self.translator.text("schema_reference.all_categories"))
            self.section_selector.addItems([section.title for section in sections])
            self.section_selector.setCurrentIndex(self.selected_sections[tab_index])
        self.section_selector.setEnabled(bool(sections))

    def _select_section(self, section_index: int) -> None:
        """選択された分類だけで参考表を描き直す。"""
        tab_index = self.tab_widget.currentIndex()
        if tab_index < 0 or section_index < 0:
            return
        self.selected_sections[tab_index] = section_index
        self.browsers[tab_index].setMarkdown(self.topics[tab_index].markdown(section_index))

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
