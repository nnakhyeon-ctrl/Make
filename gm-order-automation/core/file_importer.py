import json
from pathlib import Path

import pandas as pd

from config.settings import COLUMN_MAPPING_PATH
from core.models import Document


def _load_column_mapping() -> dict:
    with open(COLUMN_MAPPING_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    lookup = {}
    for field_name, aliases in raw.items():
        for alias in aliases:
            lookup[alias.strip().lower()] = field_name
    return lookup


def _read_any(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(path, dtype=str).fillna("")
    if suffix == ".csv":
        return pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("")
    if suffix in (".htm", ".html"):
        tables = pd.read_html(path)
        if not tables:
            raise ValueError(f"{path.name}: 표(table)를 찾을 수 없습니다.")
        return tables[0].astype(str).fillna("")
    raise ValueError(f"지원하지 않는 파일 형식입니다: {suffix}")


def import_file(path: str | Path) -> list[Document]:
    path = Path(path)
    mapping = _load_column_mapping()
    df = _read_any(path)

    normalized_cols = {}
    for col in df.columns:
        key = str(col).strip().lower()
        normalized_cols[col] = mapping.get(key, None)

    documents = []
    for _, row in df.iterrows():
        doc = Document(source_file=path.name)
        extra = {}
        for col, field_name in normalized_cols.items():
            value = str(row[col]).strip()
            if field_name:
                setattr(doc, field_name, value)
            else:
                extra[str(col)] = value
        doc.extra = extra
        if doc.is_valid():
            documents.append(doc)
    return documents


def import_files(paths: list[str | Path]) -> list[Document]:
    documents: list[Document] = []
    for path in paths:
        documents.extend(import_file(path))
    return documents
