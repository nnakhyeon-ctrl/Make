#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
유상사급 일별 출고수량 채우기
--------------------------------
원본(Sheet1)의 출고수량(I열)을 [인도처 + 자재(품번) + 출고일]로 매칭해
입력 템플릿(유상사급)의 일자 칸(N열=01일 ~ AR열=31일)에 합산 기입한다.

파이썬 표준 라이브러리만 사용한다(openpyxl/pandas 등 외부 패키지 불필요).
매달 원본·템플릿 파일만 바꿔서 그대로 재실행하면 된다.

사용법
  python3 fill_daily_shipment.py 템플릿.xlsx --source 원본.xlsx
  (Sheet1과 유상사급 시트가 한 파일에 같이 있으면 --source 생략)

핵심 규칙
- 원본에서 "출고일이 실제 날짜인 행"만 사용한다. 날짜가 비어 있거나
  날짜가 아닌 행(소계/합계/머리글)은 전부 제외한다.
- 인도처·자재는 텍스트로 비교한다(앞뒤 공백 제거, 숫자 강제변환 안 함).
  단, 숫자로 저장된 품번(12345.0)과 문자 품번("12345")이 같게 매칭되도록
  정수형 실수는 소수점을 떼어 문자열로 정규화한다.
- 같은 (인도처+자재+같은 날짜)에 여러 건이면 출고수량을 합산한다.
- 채우는 값은 출고수량(I열)이다. 금액이 아니다.
- 입력 템플릿에서 인도처(C)와 자재(E)가 모두 있는 "데이터 행"만 채운다.
  머리글/소계/합계/빈 행은 건드리지 않는다.
- 데이터 행의 일자 칸(N~AR) 중 매칭된 날짜는 합산값, 매칭 없는 빈칸은 0.
- 일자 칸 외의 셀·서식·수식은 절대 건드리지 않는다(행 XML을 부분 치환하는
  방식이라 나머지는 원본 그대로 보존된다).
"""

import argparse
import datetime as dt
import os
import re
import sys
import zipfile
from collections import defaultdict

# ============ 열/시트 설정 (필요 시 여기만 수정) ============
SRC_SHEET_DEFAULT = "Sheet1"      # 원본 시트명
DST_SHEET_DEFAULT = "유상사급"     # 입력 템플릿 시트명

# 원본(Sheet1) 열 (엑셀 열문자)
SRC_INDOCHEO_COL = "B"   # 인도처
SRC_DATE_COL = "C"       # 출고일
SRC_MATERIAL_COL = "E"   # 자재(품번)
SRC_QTY_COL = "I"        # 출고수량

# 입력(유상사급) 열
DST_INDOCHEO_COL = "C"   # 인도처
DST_MATERIAL_COL = "E"   # 자재
DAY_COL_BASE = 13        # day d -> 열 인덱스(13+d). N=14=1일 ... AR=44=31일
DAY_MIN, DAY_MAX = 1, 31
# ==========================================================

CELL_RE = re.compile(r'<c r="([A-Z]+)(\d+)"([^>]*?)(/>|>(.*?)</c>)', re.DOTALL)
ROW_SPLIT_RE = re.compile(r'(<row r="(\d+)"[^>]*?)(/>|>(.*?)</row>)', re.DOTALL)


def col_idx_to_letter(idx):
    letters = ""
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def unescape_xml(s):
    return (
        s.replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&apos;", "'")
        .replace("&amp;", "&")
    )


def load_shared_strings(z, prefix="xl/"):
    try:
        data = z.read(prefix + "sharedStrings.xml").decode("utf-8")
    except KeyError:
        return []
    strings = []
    for si in re.findall(r"<si>(.*?)</si>", data, re.DOTALL):
        texts = re.findall(r"<t[^>]*>(.*?)</t>", si, re.DOTALL)
        strings.append(unescape_xml("".join(texts)))
    return strings


def sheet_path_for_name(z, target_name, prefix="xl/"):
    wb_xml = z.read(prefix + "workbook.xml").decode("utf-8")
    rels_xml = z.read(prefix + "_rels/workbook.xml.rels").decode("utf-8")
    rid_to_target = dict(re.findall(r'<Relationship[^>]*Id="([^"]+)"[^>]*Target="([^"]+)"', rels_xml))
    sheets = re.findall(r'<sheet[^>]*name="([^"]+)"[^>]*r:id="([^"]+)"', wb_xml)
    names = []
    for name, rid in sheets:
        uname = unescape_xml(name)
        names.append(uname)
        if uname.strip() == target_name.strip():
            target = rid_to_target.get(rid, "")
            if target and not target.startswith("/"):
                target = prefix + target
            return target, names
    return None, names


def parse_row_cells(row_body, shared):
    """row_body: <row ...> 태그의 '>' 다음부터 '</row>' 전까지(자체닫힘이면 '').
    반환: 열문자 -> 값(문자열, t="s"면 공유문자열에서 이미 해석됨)."""
    cells = {}
    for m in CELL_RE.finditer(row_body):
        col, _rownum, attrs, _tail, inner = m.groups()
        inner = inner or ""
        t_match = re.search(r't="([^"]+)"', attrs)
        ctype = t_match.group(1) if t_match else None
        if ctype == "s":
            vm = re.search(r"<v>(.*?)</v>", inner, re.DOTALL)
            if vm:
                idx = int(vm.group(1))
                cells[col] = shared[idx] if idx < len(shared) else ""
        elif ctype == "inlineStr":
            texts = re.findall(r"<t[^>]*>(.*?)</t>", inner, re.DOTALL)
            cells[col] = unescape_xml("".join(texts))
        else:
            vm = re.search(r"<v>(.*?)</v>", inner, re.DOTALL)
            if vm:
                cells[col] = unescape_xml(vm.group(1))
    return cells


def norm_key(v):
    """인도처·자재를 텍스트 키로 정규화(앞뒤 공백 제거, 정수형 실수는 소수점 제거)."""
    if v is None:
        return ""
    s = str(v).strip()
    if s == "":
        return ""
    try:
        f = float(s)
        if f.is_integer():
            return str(int(f))
        return s
    except ValueError:
        return s


def to_day(v):
    """셀 값이 실제 날짜면 일(1~31)을 반환, 날짜가 아니면 None."""
    if v is None:
        return None
    s = str(v).strip()
    if s == "":
        return None
    m = re.search(r"(\d{4})\s*[-/.]\s*(\d{1,2})\s*[-/.]\s*(\d{1,2})", s)
    if m:
        try:
            return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3))).day
        except ValueError:
            return None
    try:
        n = float(s)
    except ValueError:
        return None
    if 20000 <= n <= 80000:  # 엑셀 일련번호(대략 1954~2119년)
        return (dt.datetime(1899, 12, 30) + dt.timedelta(days=n)).day
    return None


def coerce_num(v):
    """출고수량을 숫자로. 콤마·공백 허용, 비숫자·빈값은 0."""
    if v is None:
        return 0.0
    s = str(v).replace(",", "").strip()
    if s == "":
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def tidy_qty(x):
    """정수에 가까우면 int로, 아니면 반올림해 실수로."""
    xr = round(x, 6)
    if abs(xr - round(xr)) < 1e-9:
        return int(round(xr))
    return xr


def iter_rows(sheet_xml):
    for m in ROW_SPLIT_RE.finditer(sheet_xml):
        rownum = int(m.group(2))
        tail = m.group(3)
        body = m.group(4) if tail != "/>" else ""
        yield rownum, body


def replace_cell_in_row(row_full_text, row_num, col_letter, new_value):
    """<c r="{col}{row}" .../> 셀의 값을 new_value로 치환(서식 s= 속성은 유지)."""
    ref = f"{col_letter}{row_num}"
    pat = re.compile(r'<c r="' + re.escape(ref) + r'"([^>]*?)(/>|>(.*?)</c>)', re.DOTALL)
    m = pat.search(row_full_text)
    if not m:
        raise ValueError(f"셀 {ref}을(를) 템플릿 행에서 찾지 못했습니다(예상과 다른 시트 구조).")
    attrs = re.sub(r'\s*t="[^"]*"', "", m.group(1))  # 텍스트 타입이었으면 숫자로 되돌림
    new_cell = f'<c r="{ref}"{attrs}><v>{new_value}</v></c>'
    return row_full_text[: m.start()] + new_cell + row_full_text[m.end():]


def main():
    ap = argparse.ArgumentParser(description="유상사급 일별 출고수량 채우기")
    ap.add_argument("input", help="유상사급 시트가 든 xlsx(채울 대상 템플릿)")
    ap.add_argument("--source", help="Sheet1(원본)이 든 별도 xlsx. 생략 시 input 파일 안에서 찾음.")
    ap.add_argument("--output", help="결과 저장 경로. 생략 시 원본명_filled.xlsx")
    ap.add_argument("--src-sheet", default=SRC_SHEET_DEFAULT, help=f"원본 시트명(기본 {SRC_SHEET_DEFAULT})")
    ap.add_argument("--dst-sheet", default=DST_SHEET_DEFAULT, help=f"템플릿 시트명(기본 {DST_SHEET_DEFAULT})")
    args = ap.parse_args()

    if not os.path.exists(args.input):
        sys.exit(f"입력 파일이 없습니다: {args.input}")

    src_path = args.source if args.source else args.input
    if not os.path.exists(src_path):
        sys.exit(f"원본 파일이 없습니다: {src_path}")

    with zipfile.ZipFile(src_path) as zsrc:
        shared_src = load_shared_strings(zsrc)
        src_sheet_path, src_names = sheet_path_for_name(zsrc, args.src_sheet)
        if src_sheet_path is None:
            sys.exit(f"원본 시트 '{args.src_sheet}'를 찾지 못했습니다. 있는 시트: {src_names}")
        src_xml = zsrc.read(src_sheet_path).decode("utf-8")

    # ---- 1) 원본에서 (인도처, 자재, 일) -> 출고수량 합산 ----
    sums = defaultdict(float)
    used_rows = 0
    skipped_nondate = 0
    skipped_nokey = 0
    for _rownum, body in iter_rows(src_xml):
        cells = parse_row_cells(body, shared_src)
        day = to_day(cells.get(SRC_DATE_COL))
        if day is None:
            skipped_nondate += 1
            continue
        if not (DAY_MIN <= day <= DAY_MAX):
            continue
        ind = norm_key(cells.get(SRC_INDOCHEO_COL))
        mat = norm_key(cells.get(SRC_MATERIAL_COL))
        if not ind or not mat:
            skipped_nokey += 1
            continue
        sums[(ind, mat, day)] += coerce_num(cells.get(SRC_QTY_COL))
        used_rows += 1

    # ---- 2) 템플릿 로드 ----
    with zipfile.ZipFile(args.input) as ztpl:
        shared_dst = load_shared_strings(ztpl)
        dst_sheet_path, dst_names = sheet_path_for_name(ztpl, args.dst_sheet)
        if dst_sheet_path is None:
            sys.exit(f"템플릿 시트 '{args.dst_sheet}'를 찾지 못했습니다. 있는 시트: {dst_names}")
        dst_xml = ztpl.read(dst_sheet_path).decode("utf-8")

    # ---- 3) 템플릿 머리글 행 감지 ----
    # 위에서부터 인도처(C)·자재(E)가 모두 채워진 첫 행을 머리글로 본다.
    hdr_row = None
    hdr_c = hdr_e = ""
    for rownum, body in iter_rows(dst_xml):
        cells = parse_row_cells(body, shared_dst)
        c = norm_key(cells.get(DST_INDOCHEO_COL))
        e = norm_key(cells.get(DST_MATERIAL_COL))
        if c and e:
            hdr_row, hdr_c, hdr_e = rownum, c, e
            break
    if hdr_row is None:
        sys.exit(f"템플릿 '{args.dst_sheet}'에서 인도처/자재 머리글 행을 찾지 못했습니다.")

    # ---- 4) 템플릿 데이터 행의 일자 칸(N~AR) 채우기 ----
    data_rows = 0
    matched_cells = 0
    zero_cells = 0
    matched_keys = set()

    def process_row(m):
        nonlocal data_rows, matched_cells, zero_cells
        rownum = int(m.group(2))
        tail = m.group(3)
        if rownum <= hdr_row or tail == "/>":
            return m.group(0)
        cells = parse_row_cells(m.group(4), shared_dst)
        ind = norm_key(cells.get(DST_INDOCHEO_COL))
        mat = norm_key(cells.get(DST_MATERIAL_COL))
        if not ind or not mat:
            return m.group(0)  # 소계/합계/빈행 → 건드리지 않음
        if ind == hdr_c and mat == hdr_e:
            return m.group(0)  # 반복된 머리글 → 건드리지 않음
        data_rows += 1
        row_full = m.group(0)
        for day in range(DAY_MIN, DAY_MAX + 1):
            col_letter = col_idx_to_letter(DAY_COL_BASE + day)
            key = (ind, mat, day)
            if key in sums:
                val = tidy_qty(sums[key])
                matched_cells += 1
                matched_keys.add(key)
            else:
                val = 0
                zero_cells += 1
            row_full = replace_cell_in_row(row_full, rownum, col_letter, val)
        return row_full

    new_dst_xml = ROW_SPLIT_RE.sub(process_row, dst_xml)

    # ---- 5) 저장: 템플릿 zip을 그대로 복사하고 시트 XML 한 항목만 교체 ----
    if args.output:
        out_path = args.output
    else:
        stem, ext = os.path.splitext(args.input)
        out_path = f"{stem}_filled{ext or '.xlsx'}"

    tmp_path = out_path + ".tmp"
    with zipfile.ZipFile(args.input, "r") as zin, zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == dst_sheet_path:
                data = new_dst_xml.encode("utf-8")
            zout.writestr(item, data)
    os.replace(tmp_path, out_path)

    # ---- 6) 콘솔 요약 ----
    total_src_qty = sum(sums.values())
    filled_qty = sum(sums[k] for k in matched_keys)
    unmatched_keys = [k for k in sums if k not in matched_keys]
    print("=" * 60)
    print("유상사급 일별 출고수량 채우기 완료")
    print("=" * 60)
    print(f"원본 시트           : {args.src_sheet}")
    print(f"템플릿 시트         : {args.dst_sheet}  "
          f"(일자 칸 {col_idx_to_letter(DAY_COL_BASE+DAY_MIN)}~{col_idx_to_letter(DAY_COL_BASE+DAY_MAX)})")
    print(f"원본 사용 행(날짜有) : {used_rows}")
    print(f"원본 제외(날짜無)   : {skipped_nondate}  (소계/합계/머리글)")
    if skipped_nokey:
        print(f"원본 제외(키無)     : {skipped_nokey}  (인도처/자재 공백)")
    print(f"집계 키 수          : {len(sums)}  (인도처+자재+일)")
    print(f"템플릿 데이터 행    : {data_rows}")
    print(f"매칭 기입 셀        : {matched_cells}")
    print(f"0 기입 셀           : {zero_cells}")
    print(f"원본 총 출고수량    : {tidy_qty(total_src_qty)}")
    print(f"템플릿 기입 수량합  : {tidy_qty(filled_qty)}")
    if abs(total_src_qty - filled_qty) > 1e-6:
        print(f"  ※ 차이 {tidy_qty(total_src_qty - filled_qty)} — 템플릿에 없는 (인도처+자재) 키가 있음")
        for (ind, mat, day) in sorted(unmatched_keys)[:20]:
            print(f"     미매칭 원본키: 인도처={ind} / 자재={mat} / {day}일 = {tidy_qty(sums[(ind,mat,day)])}")
        if len(unmatched_keys) > 20:
            print(f"     ... 외 {len(unmatched_keys)-20}건")
    else:
        print("  ✓ 원본 총량과 템플릿 기입 총량 일치")
    print(f"\n저장: {out_path}")


if __name__ == "__main__":
    main()
