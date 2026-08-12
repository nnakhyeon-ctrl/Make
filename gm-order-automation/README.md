# GM 발주 자동화

버튼 클릭 한 번으로 **문서 파일(엑셀/CSV/HTML) 불러오기 → Excel 현황 생성 → DB 반영**까지
자동으로 처리하는 데스크톱 GUI 프로그램입니다.

> GM SupplyPower 사이트에 직접 로그인해 문서를 조회/다운로드하는 기능은 포함하지 않습니다.
> 실제 사이트의 로그인 폼·조회 화면 구조(선택자, URL 등)를 알 수 없어 정확한 자동화 코드를
> 작성할 수 없기 때문입니다. 대신 GM SupplyPower에서 **미리 다운로드해 둔 문서 파일**을
> 프로그램에 넣어주면, 그 이후 과정(집계 → Excel → DB)을 자동으로 처리합니다.
> 사이트 자동 로그인/조회까지 필요하시면 실제 로그인 화면과 문서 목록 화면의 스크린샷 또는
> HTML을 알려주세요. `core/` 아래에 `login.py` 같은 자동화 단계를 추가로 붙일 수 있습니다.

## 실행 방법

```bash
cd gm-order-automation
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## 사용 방법

1. **파일 불러오기** — GM SupplyPower 등에서 받은 `.xlsx / .xls / .csv / .htm / .html`
   파일을 선택합니다. (창에 파일을 끌어다 놓아도 됩니다)
2. **전체 자동실행** — 파일 읽기 → 데이터 검증 → Excel 생성 → DB 반영을 순서대로 자동 실행하고
   진행률/통계/로그를 작은 진행창에 표시합니다.
3. **Excel 생성** / **DB 반영** — 전체 실행 없이 해당 단계만 개별로 다시 실행할 수 있습니다.
4. **결과 폴더 열기** / **다운로드 폴더 열기** — 생성된 Excel 파일, 원본 문서 폴더를 바로 엽니다.

## 입력 파일 컬럼 매핑

원본 파일의 헤더(열 제목)가 회사마다 다를 수 있어 `config/column_mapping.json`에서
별칭(alias)을 관리합니다. 예: `"doc_no": ["문서번호", "발주번호", "PO Number", ...]`.
사용하는 원본 파일의 실제 헤더가 매핑에 없으면 이 파일에 추가해 주세요. 매핑되지 않은
컬럼은 버리지 않고 각 문서의 부가 정보(extra)로 보존됩니다.

## 데이터 저장 위치

- 원본 파일 기본 폴더: `data/downloads/`
- 생성된 Excel: `data/exports/발주현황_YYYYMMDD_HHMMSS.xlsx`
- SQLite DB: `data/gm_orders.db` (`runs`, `documents` 테이블)
  - `documents` 테이블은 `문서번호` 기준으로 upsert(있으면 갱신, 없으면 추가)되어
    "DB 반영" 버튼을 여러 번 눌러도 중복 저장되지 않습니다.

## 폴더 구조

```
gm-order-automation/
  main.py                 # 앱 진입점
  config/
    settings.py            # 경로/상수
    column_mapping.json     # 입력 파일 헤더 -> 표준 필드 매핑
  core/
    models.py                # Document 데이터 모델
    file_importer.py          # xlsx/csv/html 파일 파싱
    excel_export.py            # Excel 현황 생성
    database.py                 # SQLite 저장(runs/documents)
    automation_worker.py         # 파이프라인 오케스트레이션(QThread)
  gui/
    main_window.py            # 메인 런처 창(버튼)
    progress_dialog.py         # 실행 중 진행률/로그 창
    widgets.py                  # StatCard, StepDot 위젯
  data/
    downloads/                 # 입력 파일 기본 폴더
    exports/                    # 생성된 Excel 폴더
```

## 요구 사항

- Python 3.10 이상
- PySide6, pandas, openpyxl, lxml (requirements.txt 참고)
