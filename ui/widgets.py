"""Shared reusable widgets."""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QLabel


class CollapsibleBanner(QFrame):
    """A purple instruction banner with a ▼/▶ toggle to show/hide the body."""

    def __init__(self, title: str, body_html: str, collapsed: bool = False, parent=None):
        super().__init__(parent)
        self._collapsed = collapsed
        self.setObjectName("CollapsibleBanner")
        self.setStyleSheet(
            "#CollapsibleBanner {"
            " background: #ede8f8; border: 1px solid #b89ee0;"
            " border-left: 4px solid #5a3a8e; border-radius: 4px;"
            "}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 8)
        layout.setSpacing(4)

        header = QHBoxLayout()
        header.setSpacing(6)

        self._toggle_btn = QPushButton()
        self._toggle_btn.setFlat(True)
        self._toggle_btn.setFixedSize(18, 18)
        self._toggle_btn.setStyleSheet(
            "QPushButton { color: #5a3a8e; font-size: 11px; font-weight: bold;"
            " background: transparent; border: none; padding: 0; }"
            "QPushButton:hover { color: #9063CD; }"
        )
        self._toggle_btn.clicked.connect(self._toggle)

        title_label = QLabel(f"<b style='color:#3d2570;font-size:12px;'>{title}</b>")
        title_label.setStyleSheet("background: transparent;")

        header.addWidget(self._toggle_btn)
        header.addWidget(title_label, stretch=1)
        layout.addLayout(header)

        self._body = QLabel(body_html)
        self._body.setWordWrap(True)
        self._body.setStyleSheet(
            "color: #3d2570; font-size: 12px; background: transparent;"
        )
        layout.addWidget(self._body)

        self._apply_state()

    def _toggle(self):
        self._collapsed = not self._collapsed
        self._apply_state()

    def _apply_state(self):
        self._toggle_btn.setText("▶" if self._collapsed else "▼")
        self._body.setVisible(not self._collapsed)
