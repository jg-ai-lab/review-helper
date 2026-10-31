"""가상 카페 매출 기록(before.csv)을 정리해 after.xlsx를 만드는 예시 스크립트.

사용법: python clean_sales.py before.csv after.xlsx
"""
import csv
import re
import sys
from collections import defaultdict

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

YEAR = 2026
MENU = {"아메리카노": 4000, "카페라테": 4500, "오늘의 스콘": 3500}
ALIASES = {
    "아메리카노": "아메리카노", "아아": "아메리카노", "americano": "아메리카노",
    "아이스아메리카노": "아메리카노",
    "카페라테": "카페라테", "카페라떼": "카페라테", "라떼": "카페라테",
    "오늘의스콘": "오늘의 스콘", "스콘": "오늘의 스콘",
}
PAYMENTS = {"카드": "카드", "카드결제": "카드", "card": "카드", "현금": "현금", "계좌이체": "계좌이체"}


def parse_date(text):
    nums = [int(n) for n in re.findall(r"\d+", text)]
    if len(nums) == 2:
        nums = [YEAR] + nums
    y, m, d = nums
    return f"{y:04d}-{m:02d}-{d:02d}"


def parse_won(text):
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def clean(rows):
    cleaned, issues, seen = [], [], set()
    for line_no, row in enumerate(rows, start=2):
        key = tuple(v.strip() for v in row.values())
        if key in seen:
            issues.append((line_no, "중복 행", "같은 내용이 이미 있어 제외"))
            continue
        seen.add(key)

        menu = ALIASES.get(re.sub(r"\s+", "", row["메뉴"]).lower())
        if menu is None:
            issues.append((line_no, "알 수 없는 메뉴", row["메뉴"]))
            continue
        price = parse_won(row["단가"])
        note = ""
        if price is None:
            price, note = MENU[menu], "단가 비어 있음 → 메뉴판 가격 적용"
        elif price != MENU[menu]:
            note = f"단가 {price:,}원 → 메뉴판 가격 {MENU[menu]:,}원으로 수정"
            price = MENU[menu]
        qty_text = row["수량"].strip()
        if not qty_text:
            issues.append((line_no, "수량 없음", "확인 전까지 합계에서 제외"))
            continue
        qty = int(qty_text)
        if qty < 0:
            note = "음수 수량 → 환불로 보고 합계에 반영"
        if note:
            issues.append((line_no, "확인 필요", note))
        cleaned.append({
            "날짜": parse_date(row["날짜"]), "메뉴": menu, "단가": price, "수량": qty,
            "금액": price * qty, "결제": PAYMENTS.get(row["결제"].strip().lower(), row["결제"]),
        })
    cleaned.sort(key=lambda r: r["날짜"])
    return cleaned, issues


def summarize(cleaned):
    by_menu = defaultdict(lambda: [0, 0])
    for r in cleaned:
        by_menu[r["메뉴"]][0] += r["수량"]
        by_menu[r["메뉴"]][1] += r["금액"]
    return by_menu


def write_xlsx(path, cleaned, issues, by_menu):
    bold, head = Font(bold=True), PatternFill("solid", fgColor="E9E9DC")
    wb = Workbook()

    def sheet(ws, header, rows, widths):
        ws.append(header)
        for c in ws[1]:
            c.font, c.fill = bold, head
        for r in rows:
            ws.append(r)
        for col, w in zip("ABCDEF", widths):
            ws.column_dimensions[col].width = w
        ws.freeze_panes = "A2"

    ws = wb.active
    ws.title = "정리된 매출"
    sheet(ws, list(cleaned[0]), [list(r.values()) for r in cleaned], [12, 12, 10, 8, 10, 10])
    for row in ws.iter_rows(min_row=2, min_col=3, max_col=5):
        for c in row:
            c.number_format = "#,##0"

    summary = [[m, q, a] for m, (q, a) in by_menu.items()]
    summary.append(["합계", sum(r[1] for r in summary), sum(r[2] for r in summary)])
    ws = wb.create_sheet("메뉴별 요약")
    sheet(ws, ["메뉴", "판매 수량", "매출"], summary, [14, 12, 12])
    for c in ws["C"][1:]:
        c.number_format = "#,##0"
    for c in ws[ws.max_row]:
        c.font = bold

    sheet(wb.create_sheet("확인 필요"), ["원본 행", "구분", "내용"], issues, [10, 16, 44])
    wb.save(path)


def main(src, dst):
    sys.stdout.reconfigure(encoding="utf-8")
    with open(src, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    cleaned, issues = clean(rows)
    by_menu = summarize(cleaned)
    write_xlsx(dst, cleaned, issues, by_menu)
    print(f"원본 {len(rows)}행 → 정리 {len(cleaned)}행, 확인 필요 {len(issues)}건")
    for m, (q, a) in by_menu.items():
        print(f"  {m}: {q}개 {a:,}원")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
