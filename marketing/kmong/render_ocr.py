"""서비스 E(거래명세서·영수증 사진 → 엑셀) 크몽 이미지를 만듭니다.

사용법(저장소 루트): python marketing/kmong/render_ocr.py
먼저 products/receipt-ocr-demo에서 make_docs.py 2 → make_photos.py 2 → ocr_to_excel.py photos_synth2 --fast를 실행해 둡니다.
결과: marketing/kmong/ocr-main.png, ocr-0{2..5}.png (1304×976), ocr-main-652.png, ocr-detail.png
화면 속 표·숫자는 세트2(처음 보는 가상 문서 20장) 합성 사진의 실제 변환·채점 결과를 그대로 씁니다.
"""
import pathlib
import re
import sys

from openpyxl import load_workbook
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DEMO = ROOT / "products" / "receipt-ocr-demo"
RESULT = DEMO / "results" / "photos_synth2_fast_변환결과.xlsx"
REPORT = DEMO / "results" / "photos_synth2_fast_정확도.md"
PHOTO = DEMO / "photos_synth2" / "E07.jpg"
sys.path.insert(0, str(HERE))
from render_details import CSS, e, shoot, stack  # noqa: E402

TAG = "사진 → 엑셀, PC 안에서만"
NOTE = "화면 속 거래처·금액은 가상입니다 · 최종 범위·비용·일정은 착수 전 합의합니다"
EXTRA = """.off{display:inline-flex;gap:6px;align-items:center;font-size:13px;font-weight:700;color:#5b6b4a;background:#e7eedf;border-radius:99px;padding:4px 12px}
.xl{width:100%;border-collapse:collapse;font-size:12.5px;background:#fff;border:1px solid #c9d3c0}
.xl th{background:#5b6b4a;color:#fff;font-weight:700;padding:5px 7px;text-align:left}.xl td{border-top:1px solid #e3e8dc;padding:5px 7px}
.xl tr.y td{background:#fff2b3}.big{font-size:40px;font-weight:800;letter-spacing:-1px;color:#5b6b4a}"""


def page(name, title, sub, body):
    doc = (f'<!doctype html><html lang="ko"><meta charset="utf-8"><title>{e(title)}</title>'
           f"<style>{CSS}{EXTRA}</style><span class=tag>{e(TAG)}</span><h1>{e(title)}</h1>"
           f"<p class=sub>{e(sub)}</p>{body}<div class=note>{e(NOTE)}</div></html>")
    path = HERE / f"{name}.html"
    path.write_text(doc, encoding="utf-8", newline="\n")
    return path


def won(n):
    return f"{n:,}" if isinstance(n, int) else ""


def pages():
    wb = load_workbook(RESULT, read_only=True)
    items = [r for r in wb["품목"].iter_rows(min_row=2, values_only=True) if r[0] == "E07"]
    doc = next(r for r in wb["문서"].iter_rows(min_row=2, values_only=True) if r[1] == "E07")
    checks = [r for r in wb["확인 필요"].iter_rows(min_row=2, values_only=True)]
    report = REPORT.read_text(encoding="utf-8")
    cells = re.search(r"칸 (\d+)개 중 (\d+)개 맞음 \(\*\*([\d.]+)%", report).groups()
    perfect = re.search(r"모든 칸이 맞은 문서: (\d+)/(\d+)장", report).groups()
    sec = re.search(r"장당 (\d+)초", report).group(1)

    rows = "".join(f"<tr><td>{e(r[2])}</td><td>{e(r[3] or '')}</td><td class=num>{r[4]}</td><td class=num>{won(r[6])}</td></tr>"
                   for r in items)
    table = (f'<table class=xl><tr><th>품목<th>규격<th class=num>수량<th class=num>금액</tr>{rows}'
             f'<tr><td colspan=3><b>합계 (공급가액+세액)</b></td><td class=num><b>{won(doc[9])}</b></td></tr></table>'
             f'<p style="font-size:11.5px;color:#685e51;margin-top:6px">{e(doc[3])} · {e(doc[4])} · 실제 변환 결과</p>')
    yield page("ocr-main", "사진 찍어 보내면 엑셀로", "거래명세서·영수증을 읽어 날짜·거래처·품목·금액을 한 장에 모아요",
               '<div style="margin-top:10px"><span class=off>● 사진을 인터넷으로 보내지 않아요</span></div>'
               '<div style="display:grid;grid-template-columns:150px 30px 1fr;gap:8px;align-items:center;margin-top:12px">'
               f'<img src="{PHOTO.as_uri()}" style="width:150px;height:200px;object-fit:cover;border-radius:10px;border:1px solid #d6ccbd">'
               f'<div style="font-size:28px;color:#5b6b4a;text-align:center">→</div><div>{table}</div></div>')

    qs = ["종이 거래명세서를 매달 엑셀에 손으로 옮기나요?", "영수증이 쌓여 월말 정리에 하루가 걸리나요?",
          "거래처 자료라 외부 사이트에 올리기 꺼려지나요?"]
    box = "".join(f'<div class=box style="padding:15px 20px;margin-top:11px;font-size:18px;font-weight:700">Q. {e(x)}</div>' for x in qs)
    yield page("ocr-02", "이런 곳에 맞아요", "카페·식당·작은 가게·사무실처럼 종이 문서가 계속 쌓이는 곳",
               f'<div style="margin-top:14px">{box}</div>')

    pick = [c for c in checks if "단가표" in c[3] or "금액÷단가" in c[3]][:2] + [c for c in checks if "읽지 못함" in c[3]][:1]
    rows = "".join(f'<tr class=y><td>{e(c[1])}</td><td>{e(c[2])}</td><td>{e(c[3])}</td></tr>' for c in pick)
    yield page("ocr-03", "자신 없는 칸은 노랗게 표시해요", "틀린 채로 넘기지 않게, 사람이 볼 칸만 따로 모아 드려요",
               f'<table class=xl style="margin-top:14px"><tr><th>문서<th>칸<th>이유</tr>{rows}</table>'
               '<div class=box style="margin-top:12px;padding:12px 16px;font-size:13.5px;line-height:1.7">'
               '· 수량×단가=금액, 품목 합=문서 합계가 맞는지 계산으로 대조<br>'
               '· 단가표를 주시면 비슷하게 읽힌 품목 이름을 고치고, 고친 칸도 표시<br>'
               '· 노란 칸만 원본과 비교하면 끝나요</div>')

    yield page("ocr-04", "시험 결과를 숫자로 보여 드려요", "처음 보는 가상 문서 20장을 휴대폰 사진처럼 만들어 시험했어요",
               '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:16px;text-align:center;font-size:12px">'
               f'<div class=box style="padding:16px 8px"><div class=big>{cells[2]}%</div><div style="font-size:13px">칸 {cells[0]}개 중 {cells[1]}개 정답</div></div>'
               f'<div class=box style="padding:16px 8px"><div class=big>{perfect[0]}/{perfect[1]}</div><div style="font-size:13px">모든 칸이 맞은 문서</div></div>'
               f'<div class=box style="padding:16px 8px"><div class=big>{sec}초</div><div style="font-size:13px">장당 처리 (CPU만)</div></div></div>'
               '<p style="margin-top:12px;font-size:13px;color:#685e51;line-height:1.6">틀린 1장은 멀리서 찍은 작은 영수증이었고, 문서 전체가 \'확인 필요\'로 표시됐어요.<br>'
               '합성 사진 시험이라 실제 사진은 다를 수 있어요. 주문 전 샘플 5~10장으로 먼저 확인해 드려요.</p>')

    pk = [("변환 대행", "인쇄 문서 사진·PDF 50장 이하 → 엑셀", "30,000원"),
          ("설치형 변환 프로그램", "양식 1종 자동 변환 · PC 1대 · 안내서", "150,000원"),
          ("여러 양식", "양식 3종 이하 + 월별 합계 시트", "250,000원")]
    rows = "".join(f'<tr><td style="padding:13px;font-weight:800">{e(a)}</td><td style="padding:13px;font-size:14px">{e(b)}</td>'
                   f'<td class=num style="padding:13px;font-weight:800">{c}</td></tr>' for a, b, c in pk)
    yield page("ocr-05", "패키지", "착수 전에 샘플 사진으로 읽을 수 있는지 먼저 알려 드려요",
               f'<table class=box style="margin-top:16px;font-size:16px">{rows}</table>'
               '<div style="margin-top:14px;background:#e9e6de;border-radius:14px;padding:12px 18px;font-size:13px;color:#685e51;line-height:1.7">'
               '<b style="color:#362f26">포함하지 않아요</b> · 손글씨 문서, 100% 정확도 보장, 회계·세무 판단, 홈택스·ERP 연동, 신분증 등 민감 문서</div>')


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    pngs = [shoot(p) for p in pages()]
    Image.open(pngs[0]).resize((652, 488), Image.LANCZOS).save(HERE / "ocr-main-652.png")
    stack(pngs, HERE / "ocr-detail.png")
    print([p.name for p in pngs])
