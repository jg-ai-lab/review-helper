"""크몽 상세 이미지(2~5장)를 HTML로 만들고 Edge 헤드리스로 PNG 캡처합니다.

사용법(저장소 루트에서): python marketing/kmong/render_details.py
결과: marketing/kmong/{web,excel}-0N.png (1304×976)와 1~5장을 세로로 이은 {web,excel}-detail.png (652폭)
"""
import csv
import html
import pathlib
import subprocess
import sys

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "marketing" / "kmong"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
sys.path.insert(0, str(ROOT / "samples" / "excel"))
from clean_sales import clean, summarize  # noqa: E402

e = html.escape
CSS = """*{box-sizing:border-box;margin:0}html,body{width:652px;height:488px;overflow:hidden}
body{background:#f7f1e7;color:#362f26;font-family:"Malgun Gothic",system-ui,sans-serif;padding:46px 50px;position:relative}
.tag{display:inline-block;font-size:13px;font-weight:700;background:#363e2f;color:#f7f1e7;padding:5px 12px;border-radius:999px}
h1{font-size:34px;letter-spacing:-1.2px;margin:14px 0 6px;line-height:1.25}.sub{font-size:16px;color:#685e51}
.box{background:#fffaf2;border:1px solid #d6ccbd;border-radius:14px}
table.box{width:100%;border-collapse:separate;border-spacing:0}table.box td{border-bottom:1px solid #ece4d6}table.box tr:last-child td{border-bottom:0}
.note{position:absolute;left:50px;bottom:18px;font-size:11px;color:#9a8f80}
.num{text-align:right;font-variant-numeric:tabular-nums}"""


def page(name, tag, title, sub, body, note):
    doc = (f'<!doctype html><html lang="ko"><meta charset="utf-8"><title>{e(title)}</title>'
           f"<style>{CSS}</style><span class=tag>{e(tag)}</span><h1>{e(title)}</h1>"
           f"<p class=sub>{e(sub)}</p>{body}<div class=note>{e(note)}</div></html>")
    path = OUT / f"{name}.html"
    path.write_text(doc, encoding="utf-8", newline="\n")
    return path


def web_pages():
    tag, note = "작은 가게 소개 페이지", "최종 비용과 일정은 착수 전 서면으로 합의합니다"

    qs = ["메뉴판 사진만 올려 두셨나요?", "운영 시간 문의가 자주 오나요?", "지도·SNS 링크가 여기저기 흩어져 있나요?"]
    q = "".join(f'<div class=box style="padding:16px 20px;margin-top:12px;font-size:19px;font-weight:700">Q. {e(x)}</div>' for x in qs)
    yield page("web-02", tag, "이런 가게에 맞아요", "인스타그램·지도로 안내하는 카페·식당·공방",
               f'<div style="margin-top:18px">{q}</div><p style="margin-top:16px;font-size:16px;color:#685e51">'
               "하나라도 해당되면, 링크 하나로 정리한 페이지가 도움이 될 수 있어요.</p>", note)

    items = [("소개 페이지 1개", "모바일 대응 + HTML 소스 제공"), ("대표 메뉴 최대 6개", "이름·설명·가격"),
             ("지도·SNS·연락처 링크", "고객이 제공한 공개 정보"), ("수정 1회", "문구·사진·색상"),
             ("3영업일 제안", "자료 수령·범위 합의 후")]
    li = "".join(f'<div class=box style="padding:12px 16px;display:flex;gap:12px;align-items:center">'
                 f'<b style="color:#363e2f;font-size:20px">✓</b><div><b style="font-size:17px">{e(a)}</b>'
                 f'<div style="font-size:13px;color:#685e51">{e(b)}</div></div></div>' for a, b in items)
    yield page("web-03", tag, "받으시는 것", "기본 50,000원 기준",
               f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:20px">{li}</div>', note)

    steps = ["자료 전달", "범위·비용 확정", "제작", "검토·수정", "납품"]
    st = ""
    for i, s in enumerate(steps, 1):
        st += (f'<div style="flex:1;text-align:center"><div style="width:52px;height:52px;margin:auto;border-radius:50%;'
               f'background:#363e2f;color:#f7f1e7;font-size:22px;font-weight:800;line-height:52px">{i}</div>'
               f'<div style="margin-top:10px;font-size:15px;font-weight:700">{e(s)}</div></div>')
        if i < len(steps):
            st += '<div style="font-size:24px;color:#9a8f80;margin-top:10px">›</div>'
    yield page("web-04", tag, "진행 순서", "결과물·일정·비용·검수 조건을 착수 전에 먼저 합의해요",
               f'<div style="display:flex;align-items:flex-start;margin-top:40px">{st}</div>'
               '<div class=box style="margin-top:36px;padding:14px 18px;font-size:14px;color:#685e51;line-height:1.7">'
               "<b style=\"color:#362f26\">준비해 주실 것</b> · 가게명, 소개 문구, 메뉴·가격, 운영 시간, 지도 링크, 사용 권리가 있는 사진</div>", note)

    pk = [("기본", "페이지 1개 · 메뉴 6개 · 수정 1회", "50,000원"), ("확장", "메뉴 12개 · 사진 갤러리 · 수정 2회", "80,000원")]
    rows = "".join(f'<tr><td style="padding:14px;font-weight:800">{a}</td><td style="padding:14px">{e(b)}</td>'
                   f'<td class=num style="padding:14px;font-weight:800">{c}</td></tr>' for a, b, c in pk)
    yield page("web-05", tag, "가격과 제외 범위", "필요한 만큼만 고르세요",
               f'<table class=box style="margin-top:18px;font-size:16px">{rows}</table>'
               '<div style="margin-top:16px;background:#e9e6de;border-radius:14px;padding:14px 18px;font-size:14px;color:#685e51;line-height:1.7">'
               '<b style="color:#362f26">포함하지 않아요</b><br>주문·예약·결제 기능, 로그인·관리자 화면, 로고 제작, 유료 도메인·호스팅 비용</div>', note)


def excel_pages():
    with open(ROOT / "samples" / "excel" / "before.csv", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    cleaned, issues = clean(rows)
    by_menu = summarize(cleaned)
    total = sum(a for _, a in by_menu.values())
    tag, note = "엑셀 정리 · 자동화", "가상 카페 매출 데이터로 만든 예시입니다"

    cards = [(f"{len(rows)}행 → {len(cleaned)}행", "중복·수량 누락 제외"), (f"{len(issues)}건", "확인이 필요한 항목"),
             (f"{total:,}원", "메뉴별 매출 합계")]
    c = "".join(f'<div class=box style="flex:1;padding:16px 18px"><div style="font-size:22px;font-weight:800;color:#363e2f;white-space:nowrap">{a}</div>'
                f'<div style="font-size:13px;color:#685e51;margin-top:4px">{b}</div></div>' for a, b in cards)
    m = "".join(f'<tr><td style="padding:8px 14px">{e(k)}</td><td class=num style="padding:8px 14px">{q}개</td>'
                f'<td class=num style="padding:8px 14px">{a:,}원</td></tr>' for k, (q, a) in by_menu.items())
    yield page("excel-02", tag, "일주일 매출 기록 정리 예시", "날짜·메뉴·금액이 제각각이던 기록을 요약표까지",
               f'<div style="display:flex;gap:10px;margin-top:20px">{c}</div>'
               f'<table class=box style="margin-top:14px;font-size:15px">{m}</table>', note)

    ex = [("날짜", "2026.10.1 · 10/1 · 10월 2일", "2026-10-01"), ("메뉴", "아아 · americano · 아이스 아메리카노", "아메리카노"),
          ("금액", "4,000원 · ₩4000 · 4000", "4,000"), ("결제", "카드결제 · CARD · card", "카드"), ("중복", "같은 줄 두 번 입력", "1줄만 남김")]
    t = "".join(f'<tr><td style="padding:10px 14px;font-weight:800;color:#6c6848">{a}</td>'
                f'<td style="padding:10px 12px;color:#8a5a48">{e(b)}</td><td style="padding:10px 4px;color:#9a8f80">→</td>'
                f'<td style="padding:10px 14px;font-weight:700">{e(c)}</td></tr>' for a, b, c in ex)
    yield page("excel-03", tag, "이렇게 정리해요", "형식을 하나로 맞춰 바로 합계·필터를 쓸 수 있게",
               f'<table class=box style="margin-top:20px;font-size:15px">{t}</table>', note)

    it = "".join(f'<tr><td class=num style="padding:8px 12px">{n}행</td><td style="padding:8px 12px;font-weight:700">{e(k)}</td>'
                 f'<td style="padding:8px 12px;color:#685e51">{e(v)}</td></tr>' for n, k, v in issues)
    yield page("excel-04", tag, "임의로 고치지 않아요", "바꾸거나 뺀 내용은 '확인 필요' 시트에 따로 남겨요",
               f'<table class=box style="margin-top:18px;font-size:13.5px">{it}</table>', note)

    term = ('<div style="background:#2b2620;color:#e9e6de;border-radius:12px;padding:16px 18px;margin-top:18px;'
            'font-family:Consolas,monospace;font-size:14px;line-height:1.7">'
            f"&gt; python clean_sales.py 11월_1주.csv 정리.xlsx<br>원본 {len(rows)}행 → 정리 {len(cleaned)}행, 확인 필요 {len(issues)}건</div>")
    pk = [("정리", "파일 1개 · 약 1,000행 이하", "20,000원"), ("정리+요약", "파일 3개 합치기 · 요약표 1개", "40,000원"),
          ("자동화", "반복 작업 1개 · 사용 안내", "60,000원부터")]
    p = "".join(f'<tr><td style="padding:9px 14px;font-weight:800">{a}</td><td style="padding:9px 12px;font-size:14px">{b}</td>'
                f'<td class=num style="padding:9px 14px;font-weight:800">{c}</td></tr>' for a, b, c in pk)
    yield page("excel-05", tag, "다음 주 기록도 한 번에", "같은 정리를 스크립트로 반복해요",
               f'{term}<table class=box style="margin-top:14px;font-size:15px">{p}</table>', note)


def shoot(path):
    png = path.with_suffix(".png")
    subprocess.run([EDGE, "--headless", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
                    "--window-size=652,488", f"--screenshot={png}", path.as_uri()], check=True, capture_output=True)
    return png


def stack(pngs, dst):
    ims = [Image.open(p).convert("RGB").resize((652, 488), Image.LANCZOS) for p in pngs]
    out = Image.new("RGB", (652, 488 * len(ims)), "#f7f1e7")
    for i, im in enumerate(ims):
        out.paste(im, (0, 488 * i))
    out.save(dst)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    for kind, pages in (("web", web_pages), ("excel", excel_pages)):
        pngs = [shoot(p) for p in pages()]
        stack([OUT / f"{kind}-main.png", *pngs], OUT / f"{kind}-detail.png")
        print(kind, [p.name for p in pngs])
