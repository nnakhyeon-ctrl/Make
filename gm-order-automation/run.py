import argparse
import sys
from pathlib import Path

from config.settings import DOWNLOADS_DIR, SUPPORTED_EXTENSIONS
from core import database
from core.excel_export import export_documents
from core.file_importer import import_files


def discover_files() -> list[str]:
    return [
        str(p) for p in sorted(DOWNLOADS_DIR.iterdir())
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    ]


def main():
    parser = argparse.ArgumentParser(
        description="GM 발주 자동화 - 원본 파일을 읽어 Excel 생성 및 DB 반영까지 자동 실행합니다."
    )
    parser.add_argument(
        "files", nargs="*",
        help="처리할 원본 파일 경로(들). 생략하면 data/downloads 폴더의 모든 지원 파일을 사용합니다.",
    )
    args = parser.parse_args()

    files = args.files or discover_files()
    if not files:
        print(f"처리할 파일이 없습니다. '{DOWNLOADS_DIR}' 폴더에 이번 달 원본 파일을 넣거나, "
              f"python run.py <파일경로> 형태로 직접 지정해 주세요.")
        sys.exit(1)

    missing = [f for f in files if not Path(f).exists()]
    if missing:
        print("다음 파일을 찾을 수 없습니다:")
        for f in missing:
            print(f"  - {f}")
        sys.exit(1)

    print(f"[1/4] 파일 읽기 ({len(files)}건)")
    for f in files:
        print(f"  - {f}")
    documents = import_files(files)

    print("[2/4] 데이터 검증")
    valid = [d for d in documents if d.is_valid()]
    fail_count = len(documents) - len(valid)
    print(f"  정상 {len(valid)}건 / 실패 {fail_count}건")

    print("[3/4] Excel 생성")
    excel_path = export_documents(valid)
    print(f"  -> {excel_path}")

    print("[4/4] DB 반영")
    run_id = database.start_run(files)
    db_count = database.upsert_documents(valid, run_id)
    database.finish_run(run_id, len(documents), fail_count)
    print(f"  {db_count}건 반영 완료")

    print(f"\n완료. 총 {len(documents)}건 처리 (실패 {fail_count}건), Excel: {excel_path.name}")


if __name__ == "__main__":
    main()
