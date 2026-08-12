from PySide6.QtCore import QThread, Signal

from core import database
from core.excel_export import export_documents
from core.file_importer import import_files
from core.models import Document

STEPS_FULL = ["파일 읽기", "데이터 검증", "Excel 생성", "DB 반영"]
STEPS_EXCEL = ["Excel 생성"]
STEPS_DB = ["DB 반영"]


class AutomationWorker(QThread):
    log = Signal(str)
    progress = Signal(int, str)
    stats = Signal(dict)
    step_changed = Signal(str, str)  # step name, status: active|done|fail
    finished_ok = Signal(dict)
    failed = Signal(str)

    def __init__(self, files: list[str], mode: str = "full", documents: list[Document] | None = None):
        super().__init__()
        self.files = files
        self.mode = mode
        self.documents: list[Document] = documents or []

    def _emit_step(self, name: str, status: str):
        self.step_changed.emit(name, status)

    def run(self):
        try:
            if self.mode == "full":
                self._run_full()
            elif self.mode == "excel":
                self._run_excel_only()
            elif self.mode == "db":
                self._run_db_only()
            else:
                raise ValueError(f"알 수 없는 실행 모드: {self.mode}")
        except Exception as exc:  # noqa: BLE001
            self.log.emit(f"[ERROR] {exc}")
            self.failed.emit(str(exc))

    def _run_full(self):
        total_steps = len(STEPS_FULL)
        self.log.emit(f"자동화 시작. 대상 파일 {len(self.files)}건.")

        self._emit_step("파일 읽기", "active")
        self.progress.emit(int(1 / total_steps * 100), "파일을 읽는 중입니다.")
        documents = import_files(self.files)
        self.documents = documents
        self.log.emit(f"파일 읽기 완료: {len(documents)}건 로드")
        self._emit_step("파일 읽기", "done")

        self._emit_step("데이터 검증", "active")
        self.progress.emit(int(2 / total_steps * 100), "데이터를 검증하는 중입니다.")
        valid = [d for d in documents if d.is_valid()]
        fail_count = len(documents) - len(valid)
        self.stats.emit({"total": len(documents), "fail": fail_count})
        self.log.emit(f"데이터 검증 완료: 정상 {len(valid)}건 / 실패 {fail_count}건")
        self._emit_step("데이터 검증", "done")

        self._emit_step("Excel 생성", "active")
        self.progress.emit(int(3 / total_steps * 100), "Excel 파일을 생성하는 중입니다.")
        excel_path = export_documents(valid)
        self.log.emit(f"Excel 생성 완료: {excel_path}")
        self._emit_step("Excel 생성", "done")

        self._emit_step("DB 반영", "active")
        self.progress.emit(int(4 / total_steps * 100), "DB에 반영하는 중입니다.")
        run_id = database.start_run([f for f in self.files])
        db_count = database.upsert_documents(valid, run_id)
        database.finish_run(run_id, len(documents), fail_count)
        self.log.emit(f"DB 반영 완료: {db_count}건")
        self._emit_step("DB 반영", "done")

        self.progress.emit(100, "완료")
        self.stats.emit({"total": len(documents), "fail": fail_count, "db": db_count})
        self.finished_ok.emit({
            "total": len(documents),
            "fail": fail_count,
            "excel_path": str(excel_path),
            "db_count": db_count,
            "documents": valid,
        })

    def _run_excel_only(self):
        self._emit_step("Excel 생성", "active")
        self.progress.emit(50, "Excel 파일을 생성하는 중입니다.")
        valid = [d for d in self.documents if d.is_valid()]
        excel_path = export_documents(valid)
        self.log.emit(f"Excel 생성 완료: {excel_path}")
        self._emit_step("Excel 생성", "done")
        self.progress.emit(100, "완료")
        self.finished_ok.emit({"excel_path": str(excel_path), "total": len(valid)})

    def _run_db_only(self):
        self._emit_step("DB 반영", "active")
        self.progress.emit(50, "DB에 반영하는 중입니다.")
        valid = [d for d in self.documents if d.is_valid()]
        run_id = database.start_run([f for f in self.files] or ["manual"])
        db_count = database.upsert_documents(valid, run_id)
        database.finish_run(run_id, len(valid), 0)
        self.log.emit(f"DB 반영 완료: {db_count}건")
        self._emit_step("DB 반영", "done")
        self.progress.emit(100, "완료")
        self.finished_ok.emit({"db_count": db_count, "total": len(valid)})
