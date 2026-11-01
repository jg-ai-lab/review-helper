"""서비스 E 데모용 가상 거래명세서 12장·영수증 8장과 정답지를 만드는 스크립트.

사용법: python make_docs.py
docs/ 폴더에 문서 그림(E01.png~E20.png), 인쇄용 인쇄용_20장.pdf, 정답.xlsx, 정답.json을 만듭니다.
모든 상호·주소는 가상입니다. 사업자번호는 실제로 쓰이지 않는 000으로 시작하고,
전화번호는 010-0000-XXXX 형식만 씁니다.
"""
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
OUT = HERE / "docs"
SEED = 20261101
DPI = 150
A4 = (1240, 1754)  # 150dpi A4
FONT = "C:/Windows/Fonts/malgun.ttf"
BOLD = "C:/Windows/Fonts/malgunbd.ttf"

BUYER = ("샘플카페(가상)", "000-00-00001", "가상시 샘플구 연습로 12")
SUPPLIERS = [
    ("가상유업 대리점", "000-11-10234", "가상시 우유구 목장로 3", [
        ("흰우유", "1L", 2600), ("저지방우유", "1L", 2800), ("생크림", "500ml", 6900), ("연유", "500g", 4300)]),
    ("샘플원두상사", "000-12-20871", "가상시 커피구 로스팅길 45", [
        ("원두 블렌드A", "1kg", 24000), ("원두 디카페인", "1kg", 29000), ("원두 싱글오리진", "500g", 18500)]),
    ("연습포장재", "000-13-31552", "가상시 포장구 상자로 8", [
        ("종이컵 13oz", "1000개", 42000), ("컵뚜껑", "1000개", 23000), ("컵홀더", "1000개", 19000),
        ("빨대", "500개", 6500), ("포장봉투 소", "100장", 5200)]),
    ("가상제과 도매", "000-14-42609", "가상시 빵구 오븐로 21", [
        ("크루아상 생지", "10개", 12000), ("베이글", "6개", 9600), ("마들렌", "12개", 14400), ("스콘 생지", "10개", 11000)]),
    ("샘플시럽유통", "000-15-50113", "가상시 단맛구 시럽길 6", [
        ("바닐라 시럽", "1L", 13500), ("헤이즐넛 시럽", "1L", 13500), ("카라멜 소스", "2kg", 16800), ("초코 파우더", "1kg", 15200)]),
]
STORES = [
    ("연습마트 샘플점", "000-21-60001", "가상시 샘플구 장보기로 100", [
        ("생수 2L", 1200), ("설탕 1kg", 2480), ("레몬", 990), ("키친타월", 6900), ("고무장갑", 2500),
        ("주방세제", 4300), ("얼음컵", 1500), ("바나나", 3980)]),
    ("가상다이소 연습점", "000-22-60002", "가상시 샘플구 천원길 7", [
        ("행주", 1000), ("수세미", 2000), ("유리병", 3000), ("라벨스티커", 1000), ("집게", 2000), ("계량컵", 3000)]),
    ("샘플철물", "000-23-60003", "가상시 샘플구 공구로 2", [
        ("건전지 AA", 4500), ("멀티탭", 12000), ("케이블타이", 2500), ("전구", 6000)]),
]


def font(size, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT, size)


def won(n):
    return f"{n:,}"


def make_statement(rng, n, day):
    name, bizno, addr, catalog = rng.choice(SUPPLIERS)
    lines = []
    for item, spec, price in rng.sample(catalog, rng.randint(2, len(catalog))):
        qty = rng.choice([1, 1, 2, 2, 3, 4, 5, 6, 10])
        lines.append({"품목": item, "규격": spec, "수량": qty, "단가": price, "금액": qty * price,
                      "세액": qty * price // 10})
    supply = sum(l["금액"] for l in lines)
    tax = sum(l["세액"] for l in lines)
    return {"문서번호": f"E{n:02d}", "종류": "거래명세서", "날짜": day.isoformat(), "거래처": name,
            "사업자번호": bizno, "주소": addr, "품목": lines, "공급가액": supply, "세액": tax, "합계": supply + tax}


def make_receipt(rng, n, day):
    name, bizno, addr, catalog = rng.choice(STORES)
    lines = []
    for item, price in rng.sample(catalog, rng.randint(2, min(6, len(catalog)))):
        qty = rng.choice([1, 1, 1, 2, 2, 3])
        lines.append({"품목": item, "규격": "", "수량": qty, "단가": price, "금액": qty * price, "세액": 0})
    total = sum(l["금액"] for l in lines)
    tax = round(total / 11)
    t = f"{rng.randint(9, 21):02d}:{rng.randint(0, 59):02d}"
    return {"문서번호": f"E{n:02d}", "종류": "영수증", "날짜": day.isoformat(), "시각": t, "거래처": name,
            "사업자번호": bizno, "주소": addr, "품목": lines, "공급가액": total - tax, "세액": tax, "합계": total,
            "결제": rng.choice(["신용카드", "신용카드", "현금"])}


def draw_statement(d):
    img = Image.new("RGB", A4, "white")
    g = ImageDraw.Draw(img)
    L, R = 90, A4[0] - 90
    g.text((R, 60), d["문서번호"], font=font(26, True), fill="#888", anchor="ra")
    g.text((A4[0] // 2, 130), "거 래 명 세 서", font=font(52, True), fill="black", anchor="mm")
    g.text((A4[0] // 2, 185), "(공급받는자 보관용)", font=font(22), fill="#444", anchor="mm")
    y = 240
    g.text((L, y), f"거래일자: {d['날짜'].replace('-', '. ')}.", font=font(26), fill="black")
    y += 60
    half = (L + R) // 2
    for x0, x1, who, (nm, no, ad) in [(L, half - 10, "공급자", (d["거래처"], d["사업자번호"], d["주소"])),
                                       (half + 10, R, "공급받는자", BUYER)]:
        g.rectangle([x0, y, x1, y + 170], outline="black", width=2)
        g.text((x0 + 16, y + 12), who, font=font(22, True), fill="black")
        g.text((x0 + 16, y + 52), f"상호: {nm}", font=font(24), fill="black")
        g.text((x0 + 16, y + 90), f"등록번호: {no}", font=font(24), fill="black")
        g.text((x0 + 16, y + 128), f"주소: {ad}", font=font(20), fill="black")
    y += 210
    cols = [("품목", L, 330), ("규격", 330, 480), ("수량", 480, 580), ("단가", 580, 760),
            ("공급가액", 760, 960), ("세액", 960, R)]
    rh = 54
    rows = d["품목"] + [None] * (10 - len(d["품목"]))
    g.rectangle([L, y, R, y + rh], fill="#eeeeee", outline="black", width=2)
    for name, x0, x1 in cols:
        g.text(((x0 + x1) // 2, y + rh // 2), name, font=font(24, True), fill="black", anchor="mm")
    for i, line in enumerate(rows):
        ry = y + rh * (i + 1)
        g.rectangle([L, ry, R, ry + rh], outline="black", width=1)
        if line:
            vals = [line["품목"], line["규격"], str(line["수량"]), won(line["단가"]), won(line["금액"]), won(line["세액"])]
            for (name, x0, x1), v in zip(cols, vals):
                if name in ("품목", "규격"):
                    g.text((x0 + 12, ry + rh // 2), v, font=font(24), fill="black", anchor="lm")
                else:
                    g.text((x1 - 12, ry + rh // 2), v, font=font(24), fill="black", anchor="rm")
    for _, x0, _ in cols[1:]:
        g.line([x0, y, x0, y + rh * 11], fill="black", width=1)
    y += rh * 11 + 30
    for label, v in [("공급가액 합계", d["공급가액"]), ("세액 합계", d["세액"]), ("합계 금액", d["합계"])]:
        g.text((R - 300, y), label, font=font(26, label == "합계 금액"), fill="black", anchor="ra")
        g.text((R, y), f"{won(v)}원", font=font(26, label == "합계 금액"), fill="black", anchor="ra")
        y += 48
    g.text((L, A4[1] - 110), "※ 서비스 E 데모용 가상 문서입니다. 실제 거래가 아닙니다.", font=font(20), fill="#777")
    return img


def draw_receipt(d):
    w, h = 620, 1150
    img = Image.new("RGB", (w, h), "white")
    g = ImageDraw.Draw(img)
    x, y = 30, 30
    g.text((w // 2, y), d["거래처"], font=font(34, True), fill="black", anchor="ma")
    y += 60
    for t in [f"사업자 {d['사업자번호']}", d["주소"], "TEL 010-0000-" + d["사업자번호"][-4:]]:
        g.text((w // 2, y), t, font=font(20), fill="black", anchor="ma")
        y += 32
    y += 10
    g.text((x, y), f"[매출] {d['날짜']} {d['시각']}", font=font(22), fill="black")
    y += 40
    g.line([x, y, w - x, y], fill="black", width=2)
    y += 12
    g.text((x, y), "상품명", font=font(22, True), fill="black")
    g.text((380, y), "수량", font=font(22, True), fill="black", anchor="ra")
    g.text((w - x, y), "금액", font=font(22, True), fill="black", anchor="ra")
    y += 38
    g.line([x, y, w - x, y], fill="black", width=1)
    y += 12
    for line in d["품목"]:
        g.text((x, y), line["품목"], font=font(24), fill="black")
        g.text((380, y), str(line["수량"]), font=font(24), fill="black", anchor="ra")
        g.text((w - x, y), won(line["금액"]), font=font(24), fill="black", anchor="ra")
        y += 34
        g.text((x + 16, y), f"@{won(line['단가'])}", font=font(18), fill="#555")
        y += 32
    g.line([x, y, w - x, y], fill="black", width=1)
    y += 14
    for label, v, b in [("과세물품가액", d["공급가액"], False), ("부가세", d["세액"], False), ("합 계", d["합계"], True)]:
        g.text((x, y), label, font=font(28 if b else 22, b), fill="black")
        g.text((w - x, y), won(v), font=font(28 if b else 22, b), fill="black", anchor="ra")
        y += 46 if b else 36
    y += 10
    g.text((x, y), f"결제수단: {d['결제']}", font=font(22), fill="black")
    y += 60
    g.text((w // 2, y), "가상 문서 · 실제 거래 아님", font=font(18), fill="#777", anchor="ma")
    img = img.crop((0, 0, w, y + 60))
    page = Image.new("RGB", A4, "white")
    left = (A4[0] - w) // 2
    page.paste(img, (left, 120))
    pg = ImageDraw.Draw(page)
    pg.rectangle([left - 1, 119, left + w, 120 + img.height], outline="#ccc")  # 자르는 선
    pg.text((A4[0] - 90, 60), d["문서번호"], font=font(26, True), fill="#888", anchor="ra")
    return page


def save_answer(docs):
    wb = Workbook()
    ws = wb.active
    ws.title = "문서"
    head = ["문서번호", "종류", "날짜", "거래처", "사업자번호", "품목 수", "공급가액", "세액", "합계"]
    ws.append(head)
    for d in docs:
        ws.append([d["문서번호"], d["종류"], d["날짜"], d["거래처"], d["사업자번호"], len(d["품목"]),
                   d["공급가액"], d["세액"], d["합계"]])
    ws2 = wb.create_sheet("품목")
    ws2.append(["문서번호", "줄", "품목", "규격", "수량", "단가", "금액"])
    for d in docs:
        for i, l in enumerate(d["품목"], 1):
            ws2.append([d["문서번호"], i, l["품목"], l["규격"], l["수량"], l["단가"], l["금액"]])
    for sheet in (ws, ws2):
        for c in sheet[1]:
            c.font = Font(bold=True)
        for col in sheet.columns:
            sheet.column_dimensions[col[0].column_letter].width = 14
        for row in sheet.iter_rows(min_row=2):
            for c in row:
                if isinstance(c.value, int) and c.column > 4:
                    c.number_format = "#,##0"
    wb.save(OUT / "정답.xlsx")
    (OUT / "정답.json").write_text(json.dumps(docs, ensure_ascii=False, indent=1), encoding="utf-8")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    rng = random.Random(SEED)
    OUT.mkdir(exist_ok=True)
    start = date(2026, 10, 1)
    days = sorted(start + timedelta(days=rng.randint(0, 30)) for _ in range(20))
    docs = [make_statement(rng, i + 1, days[i]) if i < 12 else make_receipt(rng, i + 1, days[i]) for i in range(20)]
    pages = []
    for d in docs:
        page = draw_statement(d) if d["종류"] == "거래명세서" else draw_receipt(d)
        page.save(OUT / f"{d['문서번호']}.png", dpi=(DPI, DPI))
        pages.append(page)
    pages[0].save(OUT / "인쇄용_20장.pdf", save_all=True, append_images=pages[1:], resolution=DPI)
    save_answer(docs)
    items = sum(len(d["품목"]) for d in docs)
    print(f"문서 {len(docs)}장, 품목 줄 {items}개, 합계 {won(sum(d['합계'] for d in docs))}원 → {OUT}")


if __name__ == "__main__":
    main()
