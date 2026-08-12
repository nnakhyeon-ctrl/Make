from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

STEP_COLORS = {
    "pending": "#9AA5B1",
    "active": "#2F80ED",
    "done": "#27AE60",
    "fail": "#EB5757",
}


class StatCard(QFrame):
    def __init__(self, title: str, value: str = "0", subtitle: str = "", color: str = "#2F80ED"):
        super().__init__()
        self.setObjectName("statCard")
        self.setStyleSheet(
            "#statCard { background: #F7F8FA; border: 1px solid #E3E6EA; border-radius: 8px; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #6B7280; font-size: 12px;")

        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: 700;")

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setStyleSheet("color: #9AA5B1; font-size: 11px;")

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.subtitle_label)

    def set_value(self, value: str, subtitle: str | None = None):
        self.value_label.setText(value)
        if subtitle is not None:
            self.subtitle_label.setText(subtitle)


class StepDot(QFrame):
    def __init__(self, label: str):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.dot = QLabel("●")
        self.dot.setStyleSheet(f"color: {STEP_COLORS['pending']}; font-size: 14px;")

        self.text = QLabel(label)
        self.text.setStyleSheet("color: #374151; font-size: 12px;")

        layout.addWidget(self.dot, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.text, alignment=Qt.AlignmentFlag.AlignVCenter)

    def set_status(self, status: str):
        color = STEP_COLORS.get(status, STEP_COLORS["pending"])
        self.dot.setStyleSheet(f"color: {color}; font-size: 14px;")
