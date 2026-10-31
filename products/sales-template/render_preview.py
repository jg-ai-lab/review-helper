"""템플릿 판매용 미리보기 이미지 3장을 HTML로 만들고 Edge 헤드리스로 PNG 캡처합니다.

사용법(저장소 루트에서): python products/sales-template/render_preview.py
결과: products/sales-template/preview/preview-0N.png (1304×976)
숫자는 월매출정리_예시.xlsx와 같은 가상 데이터(make_template.sample_rows)에서 계산합니다.
"""
import pathlib
import sys
from collections import defaultdict
from datetime import date

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "preview"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "marketing" / "kmong"))
from make_template import PAYMENTS, SAMPLE_ITEMS, sample_rows  # noqa: E402
from render_details import CSS, e, shoot  # noqa: E402

TAG = "엑셀 템플릿 · 작은 가게 월 매출 정리"
NOTE = "가상 카페 데이터 예시입니다 · 숫자는 함께 드리는 예시 파일과 같아요 · 매크로 없음"
SHEET = """.sheet{width:100%;border-collapse:collapse;font-size:14px;background:#fff;margin-top:18px}
.sheet th,.sheet td{border:1px solid #d9d4ca;padding:5px 9px;white-space:nowrap}
.sheet th{background:#e9e9dc;font-weight:700}.sheet .rn{background:#f1efe9;color:#9a8f80;width:28px;text-align:center;font-size:12px}
.sheet .auto{background:#f3f3f3;color:#55504a}.sheet .total td{font-weight:700;border-top:2px solid #8a8070}
.pick{background:#fff6d5;font-weight:700}.call{font-size:13px;color:#685e51;margin-top:10px}"""
PRICE = dict(SAMPLE_ITEMS)


def won(n):
    return f"{n:,}원"


def page(name, title, sub, body):
    doc = (f'<!doctype html><html lang="ko"><meta charset="utf-8"><title>{e(title)}</title>'
           f"<style>{CSS}{SHEET}</style><span class=tag>{e(TAG)}</span><h1>{e(title)}</h1>"
           f"<p class=sub>{e(sub)}</p>{body}<div class=note>{e(NOTE)}</div></html>")
    path = OUT / f"{name}.html"
    path.write_text(doc, encoding="utf-8", newline="\n")
    return path


def entry_page(rows):
    oct_rows = [r for r in rows if r[0] >= date(2026, 10, 1)][:7]
    trs = ""
    for n, (d, item, qty, pay) in enumerate(oct_rows, 2):
        trs += (f"<tr><td class=rn>{n}</td><td>{d.isoformat()}</td><td>{e(item)}</td><td class=num>{qty}</td>"
                f"<td class='num auto'>{won(PRICE[item])}</td><td class='num auto'>{won(PRICE[item] * qty)}</td>"
                f"<td>{e(pay)}</td></tr>")
    table = ("<table class=sheet><tr><th class=rn></th><th>날짜</th><th>품목 ▾</th><th>수량</th>"
             "<th>단가 (자동)</th><th>금액 (자동)</th><th>결제 ▾</th></tr>" + trs + "</table>")
    return page("preview-01", "기록은 네 칸만 적으면 돼요", "날짜·품목·수량·결제를 넣으면 단가와 금액은 자동 계산",
                table + "<p class=call>▾ 품목과 결제는 목록에서 골라요 · 회색 칸은 자동으로 채워져요</p>")


def summary_page(rows):
    by_item, by_pay = defaultdict(lambda: [0, 0]), defaultdict(int)
    for d, item, qty, pay in rows:
        if (d.year, d.month) == (2026, 10):
            by_item[item][0] += qty
            by_item[item][1] += PRICE[item] * qty
            by_pay[pay] += PRICE[item] * qty
    items = "".join(f"<tr><td>{e(i)}</td><td class=num>{by_item[i][0]}</td><td class=num>{won(by_item[i][1])}</td></tr>"
                    for i, _ in SAMPLE_ITEMS)
    total = (f"<tr class=total><td>합계</td><td class=num>{sum(v[0] for v in by_item.values())}</td>"
             f"<td class=num>{won(sum(v[1] for v in by_item.values()))}</td></tr>")
    pays = "".join(f"<tr><td>{p}</td><td class=num>{won(by_pay[p])}</td></tr>" for p in PAYMENTS)
    body = ('<div style="display:flex;gap:10px;align-items:center;margin-top:12px;font-size:15px">'
            '연도 <span class="box pick" style="padding:4px 12px">2026</span> 월 '
            '<span class="box pick" style="padding:4px 12px">10</span> <span style="color:#685e51">← 이 두 칸만 바꾸면 돼요</span></div>'
            '<div style="display:grid;grid-template-columns:3fr 2fr;gap:14px">'
            f"<table class=sheet><tr><th>품목</th><th>판매 수량</th><th>매출</th></tr>{items}{total}</table>"
            f"<table class=sheet style='align-self:start'><tr><th>결제</th><th>매출</th></tr>{pays}</table></div>")
    return page("preview-02", "연도·월만 넣으면 요약 끝", "품목별 판매 수량과 매출, 결제 방식별 매출을 한 번에", body)


def chart_page(rows):
    month = defaultdict(int)
    for d, item, qty, _ in rows:
        month[d.month] += PRICE[item] * qty
    top = max(month.values())
    bars = ""
    for m in range(1, 13):
        v = month.get(m, 0)
        h = round(170 * v / top)
        label = f"{v / 10000:.0f}만" if v else ""
        bars += (f'<div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;gap:4px">'
                 f'<span style="font-size:11px;color:#685e51">{label}</span>'
                 f'<div style="width:70%;height:{h}px;background:#5b6b4a;border-radius:4px 4px 0 0"></div>'
                 f'<span style="font-size:12px">{m}월</span></div>')
    body = (f'<div class=box style="margin-top:18px;padding:16px 18px 8px;height:240px;display:flex;gap:6px">{bars}</div>'
            "<p class=call>입력한 매출이 자동으로 1~12월 표와 막대그래프로 정리돼요 (예시는 1~10월 데이터)</p>")
    return page("preview-03", "한 해 흐름도 그래프로", "어느 달이 바빴는지 바로 보여요", body)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(exist_ok=True)
    rows = sample_rows()
    pngs = [shoot(p) for p in (entry_page(rows), summary_page(rows), chart_page(rows))]
    print([p.name for p in pngs])
