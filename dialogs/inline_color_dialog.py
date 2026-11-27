"""インライン色見本の値を変更する色選択パネル。"""

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QColorDialog, QDialogButtonBox, QLabel, QWidget

from localization.translator import Translator


class InlineColorDialog(QColorDialog):
    """元の色を表示し、適用を押したときだけ選択を確定する。"""

    def __init__(self, code: str, translator: Translator, parent: QWidget) -> None:
        """変更前の色と、選んだ色を適用するための操作を表示する。"""
        super().__init__(parent)
        self.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog)
        self.setCurrentColor(QColor(code))
        self.setWindowTitle(translator.text("inline_color.title"))
        original = QLabel(translator.text("inline_color.original", code=code), self)
        original.setStyleSheet(f"border-left: 18px solid {QColor(code).name()}; padding-left: 6px;")
        layout = self.layout()
        if layout is not None:
            layout.addWidget(original)
        buttons = self.findChild(QDialogButtonBox)
        if buttons is not None:
            apply_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
            cancel_button = buttons.button(QDialogButtonBox.StandardButton.Cancel)
            if apply_button is not None:
                apply_button.setText(translator.text("inline_color.apply"))
            if cancel_button is not None:
                cancel_button.setText(translator.text("inline_color.cancel"))
