from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from core.automation_worker import AutomationWorker, STEPS_DB, STEPS_EXCEL, STEPS_FULL
from gui.widgets import StatCard, StepDot

STEP_SETS = {"full": STEPS_FULL, "excel": STEPS_EXCEL, "db": STEPS_DB}


class ProgressDialog(QDialog):
    def __init__(self, parent, files, mode="full", documents=None):
        super().__init__(parent)
        self.setWindowTitle("실행 중")
        self.setMinimumWidth(480)
        self.setModal(True)
        self.result_payload = None

        layout = QVBoxLayout(self)

        self.status_label = QLabel("자동화를 준비하는 중입니다.")
        self.status_label.setStyleSheet("font-size: 13px; font-weight: 600;")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        stats_row = QHBoxLayout()
        self.card_total = StatCard("처리 문서", "0", "건", "#2F80ED")
        self.card_fail = StatCard("실패", "0", "건", "#EB5757")
        self.card_db = StatCard("DB 반영", "0", "건", "#27AE60")
        for card in (self.card_total, self.card_fail, self.card_db):
            stats_row.addWidget(card)
        layout.addLayout(stats_row)

        steps_row = QHBoxLayout()
        self.step_dots = {}
        for name in STEP_SETS.get(mode, STEPS_FULL):
            dot = StepDot(name)
            self.step_dots[name] = dot
            steps_row.addWidget(dot)
        steps_row.addStretch()
        layout.addLayout(steps_row)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet(
            "background: #111827; color: #D1FAE5; font-family: Consolas, monospace; font-size: 11px;"
        )
        self.log_view.setFixedHeight(160)
        layout.addWidget(self.log_view)

        self.close_button = QPushButton("닫기")
        self.close_button.setEnabled(False)
        self.close_button.clicked.connect(self.accept)
        layout.addWidget(self.close_button, alignment=Qt.AlignmentFlag.AlignRight)

        self.worker = AutomationWorker(files, mode=mode, documents=documents)
        self.worker.log.connect(self._on_log)
        self.worker.progress.connect(self._on_progress)
        self.worker.stats.connect(self._on_stats)
        self.worker.step_changed.connect(self._on_step)
        self.worker.finished_ok.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)

    def start(self):
        self.worker.start()

    def _on_log(self, text: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_view.appendPlainText(f"{timestamp}  {text}")

    def _on_progress(self, percent: int, message: str):
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)

    def _on_stats(self, data: dict):
        if "total" in data:
            self.card_total.set_value(str(data["total"]))
        if "fail" in data:
            self.card_fail.set_value(str(data["fail"]))
        if "db" in data:
            self.card_db.set_value(str(data["db"]))

    def _on_step(self, name: str, status: str):
        dot = self.step_dots.get(name)
        if dot:
            dot.set_status(status)

    def _on_finished(self, payload: dict):
        self.result_payload = payload
        self.status_label.setText("완료되었습니다.")
        self.close_button.setEnabled(True)
        if "db_count" in payload:
            self.card_db.set_value(str(payload["db_count"]))

    def _on_failed(self, message: str):
        self.status_label.setText(f"오류 발생: {message}")
        self.close_button.setEnabled(True)
        for dot in self.step_dots.values():
            if dot.dot.styleSheet().find("#2F80ED") != -1:
                dot.set_status("fail")
