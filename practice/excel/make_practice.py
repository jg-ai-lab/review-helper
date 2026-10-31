"""납품 연습용 가상 꽃집 주문 파일 3개와 정답지(ANSWER.md)를 만드는 스크립트.

사용법: python make_practice.py
같은 폴더에 2026-08_주문.xlsx, 2026-09_주문.xlsx, 2026-10_주문.xlsx, ANSWER.md를 만듭니다.
모든 이름·번호는 가상이며 전화번호는 010-0000-XXXX 형식만 씁니다.
"""
import random
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

from openpyxl import Workbook

HERE = Path(__file__).parent
YEAR = 2026
PRICES = {"장미 꽃다발": 35000, "프리지아 꽃다발": 25000, "꽃바구니": 50000, "몬스테라 화분": 30000}
ALIASES = {
    "장미 꽃다발": ["장미 꽃다발", "장미꽃다발", "장미 꽃다발 ", "장미다발"],
    "프리지아 꽃다발": ["프리지아 꽃다발", "프리지어 꽃다발", "프리지아"],
    "꽃바구니": ["꽃바구니", "꽃 바구니", "바구니"],
    "몬스테라 화분": ["몬스테라 화분", "화분(몬스테라)", "몬스테라"],
}
PAYMENTS = ["카드", "카드결제", "card", "현금", "계좌이체", "이체"]
CUSTOMERS = [
    ("김하늘", "1021"), ("이서준", "1187"), ("박지민", "1254"), ("최유나", "1330"),
    ("정민호", "1412"), ("한소율", "1578"), ("오태윤", "1639"), ("윤채원", "1795"),
]


def phone(tail, style):
    return ["010-0000-" + tail, "0100000" + tail, "010 0000 " + tail, "010.0000." + tail][style % 4]


def make_orders(rng, month, n):
    days = sorted(rng.randint(1, 30) for _ in range(n - 1)) + [30]
    orders = []
    for day in days:
        name, tail = rng.choice(CUSTOMERS)
        product = rng.choice(list(PRICES))
        qty = rng.choice([1, 1, 1, 2])
        orders.append({"date": date(YEAR, month, day), "name": name, "tail": tail,
                       "product": product, "qty": qty, "pay": rng.choice(PAYMENTS)})
    return orders


def alias(rng, product):
    return rng.choice(ALIASES[product])


def write_aug(rng, orders, issues, final):
    wb = Workbook()
    ws = wb.active
    ws.title = "주문"
    ws.append(["주문일", "고객명", "연락처", "상품", "수량", "금액", "결제"])
    dup_at, typo_at = 6, 11
    for i, o in enumerate(orders):
        amount = PRICES[o["product"]] * o["qty"]
        shown = amount * 10 if i == typo_at else amount
        ws.append([o["date"], o["name"], phone(o["tail"], i), alias(rng, o["product"]),
                   o["qty"], shown, o["pay"]])
        ws.cell(ws.max_row, 1).number_format = "yyyy-mm-dd"
        final.append(o)
        if i == typo_at:
            issues.append(("8월", ws.max_row, "금액 오타", f"{shown:,}원 → 단가×수량 {amount:,}원"))
        if i == dup_at:
            ws.append([c.value for c in ws[ws.max_row]])
            issues.append(("8월", ws.max_row, "중복 행", "바로 윗 행과 같음 → 제외"))
    ws.append(["합계", None, None, None, f"=SUM(E2:E{ws.max_row})", f"=SUM(F2:F{ws.max_row})", None])
    issues.append(("8월", ws.max_row, "합계 행", "데이터가 아님 → 제외"))
    wb.save(HERE / "2026-08_주문.xlsx")


def date_text(d, style):
    return [f"{d.month}/{d.day}", f"{d.year}.{d.month}.{d.day}", f"{d.year}년 {d.month}월 {d.day}일",
            d.isoformat()][style % 4]


def write_sep(rng, orders, issues, final):
    wb = Workbook()
    ws = wb.active
    ws.title = "9월"
    ws.append(["9월 주문 내역 (사장님 정리용)"])
    ws.append([])
    ws.append(["날짜", "품목", "개수", "결제금액", "이름", "전화", "결제방법"])
    blank_qty_at, blank_name_at = 4, 9
    for i, o in enumerate(orders):
        amount = PRICES[o["product"]] * o["qty"]
        qty = None if i == blank_qty_at else o["qty"]
        name = None if i == blank_name_at else o["name"]
        ws.append([date_text(o["date"], i), alias(rng, o["product"]), qty, f"{amount:,}원",
                   name, phone(o["tail"], i + 1), o["pay"]])
        final.append(o)
        if i == blank_qty_at:
            issues.append(("9월", ws.max_row, "수량 빈칸",
                           f"금액÷단가로 {o['qty']}개 추정 가능 → 반영하되 확인 필요로 표시"))
        if i == blank_name_at:
            issues.append(("9월", ws.max_row, "이름 빈칸", "전화번호로 같은 고객 확인 가능 → 확인 필요로 표시"))
    wb.save(HERE / "2026-09_주문.xlsx")


def write_oct(rng, orders, sep_last, issues, final):
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["주문일", "고객명", "연락처", "상품", "수량", "금액", "결제", "메모"])
    serial = lambda d: (d - date(1899, 12, 30)).days
    for i, o in enumerate(orders):
        if i in (4, 10):
            ws.append([])
            issues.append(("10월", ws.max_row, "빈 행", "제외"))
        amount = PRICES[o["product"]] * o["qty"]
        ws.append([serial(o["date"]), o["name"], phone(o["tail"], i + 2), alias(rng, o["product"]),
                   o["qty"], amount, o["pay"], None])
        final.append(o)
        if i == 2:
            s = sep_last
            ws.append([serial(s["date"]), s["name"], phone(s["tail"], 0), alias(rng, s["product"]),
                       s["qty"], PRICES[s["product"]] * s["qty"], s["pay"], "9월 거 옮겨 적음"])
            issues.append(("10월", ws.max_row, "다른 파일과 중복", "9월 파일 마지막 주문(9/30)과 같음 → 제외"))
        if i == 7:
            c = dict(o, qty=-1)
            ws.append([serial(o["date"]), o["name"], phone(o["tail"], 1), alias(rng, o["product"]),
                       -1, -PRICES[o["product"]], o["pay"], "취소"])
            final.append(c)
            issues.append(("10월", ws.max_row, "취소(음수)", "환불로 보고 합계에서 차감, 확인 필요로 표시"))
        if i == 12:
            ws.append([serial(o["date"]), o["name"], phone(o["tail"], 3), "연말 리스", 1, 45000, "카드", None])
            issues.append(("10월", ws.max_row, "알 수 없는 상품",
                           "가격표에 없음 → 합계에서 빼고 사장님께 질문"))
    issues.append(("10월", "A열 전체", "날짜가 숫자", "엑셀 날짜 일련번호(예: 46296) → 날짜 형식으로 변환"))
    wb.save(HERE / "2026-10_주문.xlsx")


def write_answer(issues, final):
    rows = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for o in final:
        cell = rows[o["date"].month][o["product"]]
        cell[0] += o["qty"]
        cell[1] += PRICES[o["product"]] * o["qty"]
    lines = [
        "# 정답지 · 먼저 보지 마세요",
        "",
        "`make_practice.py`가 자동으로 만든 파일입니다. 직접 정리를 끝낸 뒤 결과를 맞춰 보세요.",
        "",
        "## 심어 둔 문제",
        "",
        "| 파일 | 행 | 구분 | 처리 기준 |",
        "| --- | --- | --- | --- |",
    ]
    lines += [f"| {f} | {r} | {k} | {d} |" for f, r, k, d in issues]
    lines += [
        "",
        "공통: 연락처는 `010-0000-XXXX`로, 상품명은 가격표 이름으로, 결제는 카드·현금·계좌이체로 통일합니다.",
        "",
        "## 정리 후 기대 결과",
        "",
        f"정리된 주문 행 수: **{len(final)}행** (취소 1행 포함, 알 수 없는 상품 1행 제외)",
        "",
        "| 월 | 상품 | 수량 | 매출 |",
        "| --- | --- | --- | --- |",
    ]
    total = 0
    for m in sorted(rows):
        for p in PRICES:
            if p in rows[m]:
                q, a = rows[m][p]
                total += a
                lines.append(f"| {m}월 | {p} | {q} | {a:,}원 |")
    lines += ["", f"전체 매출 합계: **{total:,}원**", ""]
    (HERE / "ANSWER.md").write_text("\n".join(lines), encoding="utf-8")
    return len(final), total


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    rng = random.Random(20261101)
    aug, sep, oct_ = (make_orders(rng, m, 16) for m in (8, 9, 10))
    issues, final = [], []
    write_aug(rng, aug, issues, final)
    write_sep(rng, sep, issues, final)
    write_oct(rng, oct_, sep[-1], issues, final)
    n, total = write_answer(issues, final)
    print(f"파일 3개 생성, 심어 둔 문제 {len(issues)}건, 기대 결과 {n}행 · {total:,}원")


if __name__ == "__main__":
    main()
