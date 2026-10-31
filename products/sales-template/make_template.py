"""'작은 가게 월 매출 정리' 엑셀 템플릿을 만드는 스크립트.

사용법: python make_template.py
같은 폴더에 판매용 빈 템플릿(월매출정리_템플릿.xlsx)과
가상 데이터가 들어간 예시(월매출정리_예시.xlsx)를 만듭니다.
매크로 없이 엑셀 수식만 써서 엑셀·구글 시트에서 그대로 열립니다.
"""
import random
import sys
from datetime import date, timedelta
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

HERE = Path(__file__).parent
ROWS = 1000          # 매출입력 행 수
ITEMS = 30           # 품목 최대 개수
PAYMENTS = ["카드", "현금", "계좌이체", "기타"]
SAMPLE_ITEMS = [("아메리카노", 4000), ("카페라테", 4500), ("바닐라라테", 5000),
                ("오늘의 스콘", 3500), ("치즈케이크", 6000), ("원두 200g", 15000)]

BOLD = Font(bold=True)
TITLE = Font(bold=True, size=14)
HEAD = PatternFill("solid", fgColor="E9E9DC")
AUTO = PatternFill("solid", fgColor="F3F3F3")
INPUT = PatternFill("solid", fgColor="FFF6D5")
THIN = Border(bottom=Side(style="thin", color="BBBBBB"))
WON = '#,##0"원"'

ITEM_RANGE = f"품목!$A$2:$A${ITEMS + 1}"
PRICE_RANGE = f"품목!$A$2:$B${ITEMS + 1}"
LAST = ROWS + 1
COL = {k: f"매출입력!${c}$2:${c}${LAST}" for k, c in
       {"date": "A", "item": "B", "qty": "C", "amount": "E", "pay": "F"}.items()}


def header(ws, names, widths):
    ws.append(names)
    for c in ws[1]:
        c.font, c.fill, c.alignment = BOLD, HEAD, Alignment(horizontal="center")
    for i, w in enumerate(widths):
        ws.column_dimensions[chr(65 + i)].width = w
    ws.freeze_panes = "A2"


def guide_sheet(wb):
    ws = wb.active
    ws.title = "사용법"
    ws.column_dimensions["A"].width = 90
    lines = [
        ("작은 가게 월 매출 정리", TITLE),
        ("", None),
        ("1. [품목] 시트에 파는 상품과 가격을 적습니다. (최대 30개)", None),
        ("2. [매출입력] 시트에 날짜·품목·수량·결제 방식을 적습니다. 품목과 결제는 목록에서 고릅니다.", None),
        ("   단가와 금액은 자동으로 계산됩니다. 회색 칸은 고치지 마세요.", None),
        ("3. [월별 요약] 시트 노란 칸에 연도와 월을 넣으면 그 달 품목별·결제별 매출이 나옵니다.", None),
        ("   아래쪽에는 그해 1~12월 매출 표와 그래프가 나옵니다.", None),
        ("", None),
        ("자주 묻는 것", BOLD),
        ("· 환불·취소는 수량을 음수(-1)로 적으면 매출에서 빠집니다.", None),
        ("· 가격이 바뀌면 [품목]에서 새 이름(예: 아메리카노(11월~))으로 추가하세요. 기존 가격을 고치면 지난 매출도 바뀝니다.", None),
        ("· 1,000행이 넘으면 마지막 행을 복사해 아래로 붙여 넣으면 됩니다. 요약 수식은 1,001행까지만 계산합니다.", None),
        ("· 매크로가 없어 엑셀, 구글 시트, 한셀에서 열 수 있습니다.", None),
        ("", None),
        ("이 파일은 매출 기록용이며 세무·회계 신고 자료를 대신하지 않습니다.", Font(italic=True, color="777777")),
    ]
    for text, font in lines:
        ws.append([text])
        if font:
            ws.cell(ws.max_row, 1).font = font


def items_sheet(wb, items):
    ws = wb.create_sheet("품목")
    header(ws, ["품목", "단가"], [22, 12])
    for i in range(ITEMS):
        name, price = items[i] if i < len(items) else (None, None)
        ws.append([name, price])
        ws.cell(i + 2, 2).number_format = WON
        for c in ws[i + 2]:
            c.fill = INPUT


def entry_sheet(wb, rows):
    ws = wb.create_sheet("매출입력")
    header(ws, ["날짜", "품목", "수량", "단가 (자동)", "금액 (자동)", "결제", "메모"],
           [12, 18, 8, 12, 13, 10, 24])
    for r in range(2, LAST + 1):
        d, item, qty, pay = rows[r - 2] if r - 2 < len(rows) else (None, None, None, None)
        ws.cell(r, 1, d).number_format = "yyyy-mm-dd"
        ws.cell(r, 2, item)
        ws.cell(r, 3, qty)
        ws.cell(r, 4, f'=IF(B{r}="","",IFERROR(VLOOKUP(B{r},{PRICE_RANGE},2,FALSE),"품목 확인"))')
        ws.cell(r, 5, f'=IF(OR(B{r}="",C{r}="",NOT(ISNUMBER(D{r}))),"",D{r}*C{r})')
        ws.cell(r, 6, pay)
        for c in (4, 5):
            ws.cell(r, c).number_format = WON
            ws.cell(r, c).fill = AUTO

    for formula, col, msg in [(f"={ITEM_RANGE}", "B", "[품목] 시트에 있는 이름을 고르세요."),
                              (f'"{",".join(PAYMENTS)}"', "F", "목록에서 고르세요.")]:
        dv = DataValidation(type="list", formula1=formula, allow_blank=True,
                            showErrorMessage=True, errorTitle="목록에 없는 값", error=msg)
        dv.add(f"{col}2:{col}{LAST}")
        ws.add_data_validation(dv)
    dv = DataValidation(type="date", operator="greaterThan", formula1="DATE(2000,1,1)",
                        allow_blank=True, showErrorMessage=True, errorTitle="날짜 형식",
                        error="2026-10-01처럼 날짜로 입력하세요.")
    dv.add(f"A2:A{LAST}")
    ws.add_data_validation(dv)


def sumifs(target, *conds):
    return f"SUMIFS({target},{','.join(conds)})"


def summary_sheet(wb, year, month):
    ws = wb.create_sheet("월별 요약")
    for col, w in zip("ABCDE", [16, 12, 14, 12, 14]):
        ws.column_dimensions[col].width = w
    ws["A1"] = "월별 매출 요약"
    ws["A1"].font = TITLE
    ws["A3"], ws["B3"], ws["C3"], ws["D3"] = "연도", year, "월", month
    for ref in ("B3", "D3"):
        ws[ref].fill, ws[ref].font = INPUT, BOLD
    ws["A4"] = '=TEXT(DATE(B3,D3,1),"yyyy-mm")&" 매출"'
    ws["A4"].font = Font(color="777777")
    start, end = '">="&DATE($B$3,$D$3,1)', '"<"&EDATE(DATE($B$3,$D$3,1),1)'
    in_month = (COL["date"], start, COL["date"], end)

    ws.append([])
    ws.append(["품목", "판매 수량", "매출"])
    top = ws.max_row
    for c in ws[top][:3]:
        c.font, c.fill = BOLD, HEAD
    for i in range(ITEMS):
        r = top + 1 + i
        ws.cell(r, 1, f'=IF(품목!A{i + 2}="","",품목!A{i + 2})')
        ws.cell(r, 2, f'=IF(A{r}="","",{sumifs(COL["qty"], COL["item"], f"A{r}", *in_month)})')
        ws.cell(r, 3, f'=IF(A{r}="","",{sumifs(COL["amount"], COL["item"], f"A{r}", *in_month)})')
        ws.cell(r, 3).number_format = WON
    total = top + ITEMS + 1
    ws.cell(total, 1, "합계").font = BOLD
    ws.cell(total, 2, f"=SUM(B{top + 1}:B{total - 1})").font = BOLD
    ws.cell(total, 3, f"=SUM(C{top + 1}:C{total - 1})").font = BOLD
    ws.cell(total, 3).number_format = WON
    for c in ws[total][:3]:
        c.border = THIN

    # 결제 방식별 (오른쪽)
    ws.cell(top, 4, "결제").font = BOLD
    ws.cell(top, 5, "매출").font = BOLD
    ws.cell(top, 4).fill = ws.cell(top, 5).fill = HEAD
    for i, p in enumerate(PAYMENTS):
        r = top + 1 + i
        ws.cell(r, 4, p)
        ws.cell(r, 5, f"={sumifs(COL['amount'], COL['pay'], f'D{r}', *in_month)}").number_format = WON

    # 연간 추이
    yr = total + 2
    ws.cell(yr, 1, '=B3&"년 월별 매출"').font = BOLD
    ws.cell(yr + 1, 1, "월").font = BOLD
    ws.cell(yr + 1, 2, "매출").font = BOLD
    for m in range(1, 13):
        r = yr + 1 + m
        ws.cell(r, 1, f"{m}월")
        ws.cell(r, 2, "=" + sumifs(COL["amount"], COL["date"], f'">="&DATE($B$3,{m},1)',
                                   COL["date"], f'"<"&EDATE(DATE($B$3,{m},1),1)')).number_format = WON
    chart = BarChart()
    chart.title, chart.legend = "월별 매출", None
    chart.y_axis.numFmt = "#,##0"
    chart.add_data(Reference(ws, min_col=2, min_row=yr + 1, max_row=yr + 13), titles_from_data=True)
    chart.set_categories(Reference(ws, min_col=1, min_row=yr + 2, max_row=yr + 13))
    chart.width, chart.height = 16, 7
    ws.add_chart(chart, f"D{yr}")
    return top, total


def sample_rows():
    rng = random.Random(20261101)
    rows, day = [], date(2026, 9, 1)
    while day <= date(2026, 10, 31):
        for _ in range(rng.randint(3, 6)):
            name, _ = rng.choice(SAMPLE_ITEMS)
            rows.append((day, name, rng.choice([1, 1, 1, 2, 3]), rng.choice(["카드"] * 4 + ["현금", "계좌이체"])))
        day += timedelta(days=1)
    rows.append((date(2026, 10, 15), "아메리카노", -1, "카드"))
    return rows


def build(path, items, rows, year, month):
    wb = Workbook()
    guide_sheet(wb)
    items_sheet(wb, items)
    entry_sheet(wb, rows)
    summary_sheet(wb, year, month)
    wb.active = wb.sheetnames.index("매출입력") if rows else 0
    wb.save(path)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    build(HERE / "월매출정리_템플릿.xlsx", [], [], 2026, 11)
    rows = sample_rows()
    build(HERE / "월매출정리_예시.xlsx", SAMPLE_ITEMS, rows, 2026, 10)
    oct_total = sum(dict(SAMPLE_ITEMS)[i] * q for d, i, q, _ in rows if d.month == 10)
    print(f"템플릿·예시 생성. 예시 {len(rows)}행, 10월 매출 기대값 {oct_total:,}원")


if __name__ == "__main__":
    main()
