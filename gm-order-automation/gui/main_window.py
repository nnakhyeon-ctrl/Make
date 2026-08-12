import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from config.settings import APP_TITLE, DOWNLOADS_DIR, EXPORTS_DIR, SUPPORTED_EXTENSIONS
from core.file_importer import import_files
from gui.progress_dialog import ProgressDialog

BUTTON_STYLE = """
QPushButton {
    background: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 6px;
    padding: 18px 10px;
    font-size: 13px;
    font-weight: 600;
    color: #1F2937;
}
QPushButton:hover { background: #F3F4F6; }
QPushButton:pressed { background: #E5E7EB; }
QPushButton:disabled { color: #B0B7C0; }
"""


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setFixedWidth(360)
        self.setAcceptDrops(True)

        self.selected_files: list[str] = []
        self.documents = []
        self.last_excel_path: str | None = None

        layout = QVBoxLayout(self)

        title = QLabel(APP_TITLE)
        title.setStyleSheet("font-size: 16px; font-weight: 700; padding-bottom: 4px;")
        layout.addWidget(title)

        self.file_label = QLabel("불러온 파일이 없습니다. (파일을 이 창에 끌어놓아도 됩니다)")
        self.file_label.setWordWrap(True)
        self.file_label.setStyleSheet("color: #6B7280; font-size: 11px; padding-bottom: 6px;")
        layout.addWidget(self.file_label)

        grid = QGridLayout()
        grid.setSpacing(10)

        self.btn_load = QPushButton("파일\n불러오기")
        self.btn_run_all = QPushButton("전체\n자동실행")
        self.btn_excel = QPushButton("Excel\n생성")
        self.btn_db = QPushButton("DB\n반영")
        self.btn_open_folder = QPushButton("결과 폴더\n열기")
        self.btn_open_db_folder = QPushButton("다운로드 폴더\n열기")

        for btn in (self.btn_load, self.btn_run_all, self.btn_excel,
                    self.btn_db, self.btn_open_folder, self.btn_open_db_folder):
            btn.setStyleSheet(BUTTON_STYLE)
            btn.setMinimumHeight(72)

        grid.addWidget(self.btn_load, 0, 0)
        grid.addWidget(self.btn_run_all, 0, 1)
        grid.addWidget(self.btn_excel, 1, 0)
        grid.addWidget(self.btn_db, 1, 1)
        grid.addWidget(self.btn_open_folder, 2, 0)
        grid.addWidget(self.btn_open_db_folder, 2, 1)

        layout.addLayout(grid)

        self.btn_load.clicked.connect(self.on_load_files)
        self.btn_run_all.clicked.connect(self.on_run_all)
        self.btn_excel.clicked.connect(self.on_generate_excel)
        self.btn_db.clicked.connect(self.on_save_db)
        self.btn_open_folder.clicked.connect(lambda: self._open_folder(EXPORTS_DIR))
        self.btn_open_db_folder.clicked.connect(lambda: self._open_folder(DOWNLOADS_DIR))

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls()]
        valid = [p for p in paths if p.lower().endswith(SUPPORTED_EXTENSIONS)]
        if valid:
            self.selected_files = valid
            self._update_file_label()

    def _update_file_label(self):
        if not self.selected_files:
            self.file_label.setText("불러온 파일이 없습니다. (파일을 이 창에 끌어놓아도 됩니다)")
            return
        names = ", ".join(Path(p).name for p in self.selected_files)
        self.file_label.setText(f"선택된 파일 ({len(self.selected_files)}건): {names}")

    def on_load_files(self):
        filt = "지원 파일 (*.xlsx *.xls *.csv *.htm *.html)"
        files, _ = QFileDialog.getOpenFileNames(
            self, "불러올 파일 선택", str(DOWNLOADS_DIR), filt
        )
        if files:
            self.selected_files = files
            self._update_file_label()

    def _ensure_files(self) -> bool:
        if not self.selected_files:
            QMessageBox.warning(self, APP_TITLE, "먼저 '파일 불러오기'로 처리할 파일을 선택해 주세요.")
            return False
        return True

    def on_run_all(self):
        if not self._ensure_files():
            return
        dialog = ProgressDialog(self, self.selected_files, mode="full")
        dialog.start()
        dialog.exec()
        if dialog.result_payload:
            self.documents = dialog.result_payload.get("documents", self.documents)
            self.last_excel_path = dialog.result_payload.get("excel_path")

    def on_generate_excel(self):
        if not self._ensure_files():
            return
        documents = self.documents or self._parse_files_or_warn()
        if documents is None:
            return
        dialog = ProgressDialog(self, self.selected_files, mode="excel", documents=documents)
        dialog.start()
        dialog.exec()
        if dialog.result_payload:
            self.last_excel_path = dialog.result_payload.get("excel_path")

    def on_save_db(self):
        if not self._ensure_files():
            return
        documents = self.documents or self._parse_files_or_warn()
        if documents is None:
            return
        dialog = ProgressDialog(self, self.selected_files, mode="db", documents=documents)
        dialog.start()
        dialog.exec()

    def _parse_files_or_warn(self):
        try:
            documents = import_files(self.selected_files)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, APP_TITLE, f"파일을 읽는 중 오류가 발생했습니다:\n{exc}")
            return None
        self.documents = documents
        return documents

    def _open_folder(self, path):
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        if sys.platform.startswith("win"):
            os.startfile(path)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
