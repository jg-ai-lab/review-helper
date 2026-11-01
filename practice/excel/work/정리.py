"""꽃집 8~10월 주문 파일 3개를 합쳐 정리 결과 엑셀을 만든다 (납품 연습).

사용법: python 정리.py   → 꽃집_주문정리_2026-08_10.xlsx (정리된 주문 / 월별 상품 요약 / 확인 필요)
원본은 읽기만 하고 고치지 않는다.
"""
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill

HERE = Path(__file__).parent
PRICES = {"장미 꽃다발": 35000, "프리지아 꽃다발": 25000, "꽃바구니": 50000, "몬스테라 화분": 30000}
PRODUCT = {  # 공백을 뺀 표기 → 정식 상품명
    "장미꽃다발": "장미 꽃다발", "장미다발": "장미 꽃다발",
    "프리지아꽃다발": "프리지아 꽃다발", "프리지어꽃다발": "프리지아 꽃다발", "프리지아": "프리지아 꽃다발",
    "꽃바구니": "꽃바구니", "바구니": "꽃바구니",
    "몬스테라화분": "몬스테라 화분", "화분(몬스테라)": "몬스테라 화분", "몬스테라": "몬스테라 화분",
}
PAY = {"카드": "카드", "카드결제": "카드", "card": "카드", "현금": "현금", "계좌이체": "계좌이체", "이체": "계좌이체"}
issues = []  # (원본 파일, 행 번호, 문제, 처리)


def note(src, row, problem, action):
    issues.append((src, row, problem, action))


def to_date(v, src, row):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, (int, float)):  # 엑셀 날짜 일련번호
        return date(1899, 12, 30) + timedelta(days=int(v))
    s = str(v).strip()
    m = re.match(r"(?:(\d{4})\D+)?(\d{1,2})\D+(\d{1,2})", s)
    if m:
        return date(int(m.group(1) or 2026), int(m.group(2)), int(m.group(3)))
    note(src, row, f"날짜를 읽을 수 없음: {v}", "확인 필요")
    return None


def to_int(v):
    if v is None or v == "":
        return None
    return int(re.sub(r"[^\d-]", "", str(v)))


def phone(v):
    d = re.sub(r"\D", "", str(v or ""))
    return f"{d[:3]}-{d[3:7]}-{d[7:]}" if len(d) == 11 else (v or "")


def read(path, sheet_header_row, cols):
    """cols: 원본 열 이름 → 표준 열 이름."""
    ws = load_workbook(path, data_only=False).worksheets[0]
    head = [c.value for c in ws[sheet_header_row]]
    idx = {std: head.index(src) for src, std in cols.items()}
    rows = []
    for r in range(sheet_header_row + 1, ws.max_row + 1):
        vals = [c.value for c in ws[r]]
        if all(v in (None, "") for v in vals):
            note(path.name, r, "빈 행", "삭제")
            continue
        if str(vals[0]).strip() == "합계":
            note(path.name, r, "합계 행(수식)", "삭제, 요약 시트에서 다시 계산")
            continue
        rec = {std: vals[i] for std, i in idx.items()}
        rec["메모"] = vals[head.index("메모")] if "메모" in head else None
        rec["src"], rec["row"] = path.name, r
        rows.append(rec)
    return rows


def clean(rec):
    src, r = rec["src"], rec["row"]
    out = {"날짜": to_date(rec["날짜"], src, r), "고객명": (rec["고객명"] or "").strip(), "연락처": phone(rec["연락처"])}
    raw = str(rec["상품"] or "").strip()
    out["상품"] = PRODUCT.get(raw.replace(" ", ""), raw)
    qty, amt = to_int(rec["수량"]), to_int(rec["금액"])
    price = PRICES.get(out["상품"])
    if price is None:
        note(src, r, f"가격표에 없는 상품: {raw} ({amt:,}원)", "정리·요약에서 빼고 사장님께 확인")
        return None
    if qty is None and price and amt and amt % price == 0:
        qty = amt // price
        note(src, r, "수량 빈 칸", f"금액÷단가로 {qty}개로 채움")
    if price and qty and amt != qty * price and qty > 0:
        note(src, r, f"금액 {amt:,}원이 수량×단가({qty * price:,}원)와 다름", f"{qty * price:,}원으로 고침(입력 실수로 보임)")
        amt = qty * price
    out["수량"], out["금액"] = qty, amt
    pay = str(rec["결제"] or "").strip()
    out["결제"] = PAY.get(pay, pay)
    out["src"], out["row"], out["메모"] = src, r, rec.get("메모")
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    std = {"주문일": "날짜", "고객명": "고객명", "연락처": "연락처", "상품": "상품", "수량": "수량", "금액": "금액", "결제": "결제"}
    rows = read(HERE / "2026-08_주문.xlsx", 1, std)
    rows += read(HERE / "2026-09_주문.xlsx", 3, {"날짜": "날짜", "이름": "고객명", "전화": "연락처", "품목": "상품",
                                                 "개수": "수량", "결제금액": "금액", "결제방법": "결제"})
    rows += read(HERE / "2026-10_주문.xlsx", 1, std)
    orders = [o for o in (clean(r) for r in rows) if o]

    # 고객명 빈 칸: 같은 연락처의 다른 주문에서 찾는다
    by_phone = {o["연락처"]: o["고객명"] for o in orders if o["고객명"]}
    for o in orders:
        if not o["고객명"] and o["연락처"] in by_phone:
            o["고객명"] = by_phone[o["연락처"]]
            note(o["src"], o["row"], "고객명 빈 칸", f"같은 연락처의 다른 주문으로 '{o['고객명']}' 채움")

    # 취소 행: 같은 날·같은 고객·같은 상품 주문에서 빼고 합친다
    for c in [o for o in orders if (o["수량"] or 0) < 0]:
        base = next(o for o in orders if o is not c and o["날짜"] == c["날짜"] and o["고객명"] == c["고객명"]
                    and o["상품"] == c["상품"] and (o["수량"] or 0) > 0)
        base["수량"] += c["수량"]
        base["금액"] += c["금액"]
        orders.remove(c)
        note(c["src"], c["row"], f"취소 행({c['수량']}개, {c['금액']:,}원, 메모 '{c['메모']}')",
             f"{base['row']}행 주문에서 빼서 {base['수량']}개 {base['금액']:,}원으로 합침")

    # 다른 달 파일에 옮겨 적은 주문: 날짜가 파일의 달과 다르고 원래 달에 같은 주문이 있으면 삭제
    for o in list(orders):
        month = int(o["src"][5:7])
        if o["날짜"] and o["날짜"].month != month:
            twin = [x for x in orders if x is not o and x["src"] != o["src"] and
                    all(x[k] == o[k] for k in ("날짜", "고객명", "상품", "수량", "금액"))]
            if twin:
                orders.remove(o)
                note(o["src"], o["row"], f"{o['날짜']} 주문(메모 '{o['메모']}')이 {twin[0]['src']} {twin[0]['row']}행과 같음",
                     "중복으로 보고 삭제")

    # 완전히 같은 주문(모든 칸 동일): 하나만 남기고 질문
    seen = {}
    for o in list(orders):
        key = tuple(o[k] for k in ("날짜", "고객명", "연락처", "상품", "수량", "금액", "결제"))
        if key in seen:
            orders.remove(o)
            note(o["src"], o["row"], f"{seen[key]}행과 모든 칸이 같음", "중복 입력으로 보고 삭제(사장님 확인 필요)")
        else:
            seen[key] = o["row"]
    # 비슷한 주문(같은 날·고객·상품·수량, 결제만 다름): 남기고 질문
    for i, a in enumerate(orders):
        for b in orders[i + 1:]:
            if all(a[k] == b[k] for k in ("날짜", "고객명", "상품", "수량")):
                note(b["src"], b["row"], f"{a['row']}행과 날짜·고객·상품·수량이 같고 결제만 다름({a['결제']}/{b['결제']})",
                     "두 건 모두 남김(실제 두 번 주문인지 확인 필요)")

    orders.sort(key=lambda o: (o["날짜"], o["src"], o["row"]))
    save(orders)
    total = sum(o["금액"] for o in orders)
    print(f"주문 {len(orders)}건, 합계 {total:,}원, 확인 필요 {len(issues)}건")
    for m in (8, 9, 10):
        print(f"  {m}월: {sum(1 for o in orders if o['날짜'].month == m)}건 "
              f"{sum(o['금액'] for o in orders if o['날짜'].month == m):,}원")


def save(orders):
    wb = Workbook()
    bold, head = Font(bold=True), PatternFill("solid", fgColor="E7EEDF")
    ws = wb.active
    ws.title = "정리된 주문"
    ws.append(["날짜", "고객명", "연락처", "상품", "수량", "금액", "결제"])
    for o in orders:
        ws.append([o["날짜"], o["고객명"], o["연락처"], o["상품"], o["수량"], o["금액"], o["결제"]])
    for c in ws["A"][1:]:
        c.number_format = "yyyy-mm-dd"
    for c in ws["F"][1:]:
        c.number_format = "#,##0"
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    s = wb.create_sheet("월별 상품 요약")
    products = list(PRICES) + sorted({o["상품"] for o in orders} - set(PRICES))
    months = sorted({o["날짜"].month for o in orders})
    s.append(["상품"] + [f"{m}월 수량" for m in months] + [f"{m}월 매출" for m in months] + ["합계 수량", "합계 매출"])
    agg = defaultdict(lambda: [0, 0])
    for o in orders:
        agg[(o["상품"], o["날짜"].month)][0] += o["수량"]
        agg[(o["상품"], o["날짜"].month)][1] += o["금액"]
    for p in products:
        q = [agg[(p, m)][0] for m in months]
        a = [agg[(p, m)][1] for m in months]
        s.append([p] + q + a + [sum(q), sum(a)])
    n = s.max_row
    s.append(["합계"] + [f"=SUM({c.column_letter}2:{c.column_letter}{n})" for c in s[1][1:]])
    for row in s.iter_rows(min_row=2):
        for c in row[1:]:
            c.number_format = "#,##0"

    q = wb.create_sheet("확인 필요")
    q.append(["원본 파일", "행 번호", "문제", "처리한 방법"])
    for it in sorted(issues, key=lambda x: (x[0], x[1])):
        q.append(list(it))
    for sheet in wb.worksheets:
        for c in sheet[1]:
            c.font, c.fill = bold, head
        for col in sheet.columns:
            sheet.column_dimensions[col[0].column_letter].width = 14
    q.column_dimensions["C"].width = 60
    q.column_dimensions["D"].width = 45
    wb.save(HERE / "꽃집_주문정리_2026-08_10.xlsx")


if __name__ == "__main__":
    main()
