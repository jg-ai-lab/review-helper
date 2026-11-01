"""서비스 C(사진 속 물건 찾아 세기) 크몽 이미지 3장을 만듭니다.

사용법(저장소 루트): python marketing/kmong/render_vision.py
먼저 products/vision-demo에서 fetch_openimages.py → train_detector.py를 실행해 둡니다.
결과: marketing/kmong/vision-main.png, vision-02.png, vision-03.png (1304×976), vision-main-652.png, vision-detail.png
사진은 Open Images(CC BY 2.0)이고 탐지 상자를 그려 넣었으므로(변경) 이미지마다 작성자·라이선스를 적습니다.
숫자는 products/vision-demo/results/정확도.md(학습에 쓰지 않은 시험 사진 결과)에서 읽습니다.
"""
import json
import pathlib
import re
import sys

from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DEMO = ROOT / "products" / "vision-demo"
PREDS = DEMO / "openimages" / "preds"
sys.path.insert(0, str(HERE))
from render_details import CSS, e, shoot, stack  # noqa: E402

GOOD = ["caa44bce1d51cee3", "b426e52fccedea01", "600d910af3cbb842"]  # 개수를 정확히 맞힌 시험 사진(상표가 크게 안 보이는 것)
BAD = "92c6701835d2a3ee"  # 놓친 사례: 선반 위 유리병
TAG = "사진 속 물건 찾아 세기"
NOTE = "사진: Open Images(Flickr, CC BY 2.0), 탐지 상자를 그려 넣음 · 최종 범위·비용·일정은 착수 전 합의합니다"
EXTRA = """.ph{border-radius:10px;border:1px solid #d6ccbd;object-fit:cover;width:100%}
.cap{font-size:10.5px;color:#9a8f80;margin-top:3px;line-height:1.3}.big{font-size:34px;font-weight:800;letter-spacing:-1px;color:#5b6b4a}"""


def page(name, title, sub, body):
    doc = (f'<!doctype html><html lang="ko"><meta charset="utf-8"><title>{e(title)}</title>'
           f"<style>{CSS}{EXTRA}</style><span class=tag>{e(TAG)}</span><h1>{e(title)}</h1>"
           f"<p class=sub>{e(sub)}</p>{body}<div class=note>{e(NOTE)}</div></html>")
    path = HERE / f"{name}.html"
    path.write_text(doc, encoding="utf-8", newline="\n")
    return path


def pages():
    labels = {p["id"]: p for p in json.loads((DEMO / "openimages" / "labels.json").read_text(encoding="utf-8"))}
    md = (DEMO / "results" / "정확도.md").read_text(encoding="utf-8")
    rows = dict(re.findall(r"^\| (캔|병) \| \d+ \| (\d+)% \|", md, re.M))
    n_test = re.search(r"처음 보는 시험 사진 (\d+)장", md).group(1)
    ms = re.search(r"사진 한 장 처리 (\d+)ms", md).group(1)
    near = re.search(r"병 개수: .*?(\d+)장 중 정확히 맞힘 (\d+)장, ±1개 이내 (\d+)장", md).groups()

    def credit(i):
        return f"{e(labels[i]['author'] or '작성자 미상')} · CC BY 2.0"

    res = {r["id"]: r for r in json.loads((DEMO / "results" / "시험사진_결과.json").read_text(encoding="utf-8"))}

    def count(i):
        return " · ".join(f"{c} {a}개(정답 {b})" for c, (a, b) in res[i]["counts"].items() if b)

    cells = "".join(f'<div><img class=ph src="{(PREDS / f"{i}.jpg").as_uri()}" style="height:190px">'
                    f'<div style="font-size:13px;font-weight:700;margin-top:4px">{count(i)}</div>'
                    f'<div class=cap>{credit(i)}</div></div>' for i in GOOD)
    yield page("vision-main", "사진 속 물건을 찾아 개수를 세요", "가진 사진으로 우리 물건 전용 AI 모델을 만들어 드려요",
               f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:16px">{cells}</div>'
               '<p style="margin-top:8px;font-size:13px;color:#685e51">학습에 쓰지 않은 시험 사진의 실제 결과 · 상자마다 종류와 확신 점수 표시</p>')

    yield page("vision-02", "틀린 것까지 숫자로 보여 드려요", f"학습에 쓰지 않은 시험 사진 {n_test}장으로 잰 결과예요",
               '<div style="display:grid;grid-template-columns:1fr 1fr 160px;gap:10px;margin-top:14px;align-items:start">'
               f'<div class=box style="padding:14px;text-align:center"><div class=big>{rows["병"]}%</div><div style="font-size:12.5px">병을 찾은 비율</div>'
               f'<div style="font-size:12px;color:#685e51;margin-top:6px">개수 ±1 이내 {near[2]}/{near[0]}장</div></div>'
               f'<div class=box style="padding:14px;text-align:center"><div class=big>{rows["캔"]}%</div><div style="font-size:12.5px">캔을 찾은 비율</div>'
               '<div style="font-size:12px;color:#685e51;margin-top:6px">학습 전 모델은 0%(캔 분류 없음)</div></div>'
               f'<div><img class=ph src="{(PREDS / f"{BAD}.jpg").as_uri()}" style="height:150px"><div class=cap>놓친 사례: 선반 위 유리병<br>{credit(BAD)}</div></div></div>'
               f'<div class=box style="margin-top:10px;padding:11px 16px;font-size:13px;line-height:1.65">'
               f'· 사진 한 장 {int(ms) / 1000:.2f}초(그래픽카드) · 술병·화장품병이 섞인 공개 사진이라 어려운 시험이에요<br>'
               '· 고객 사진(같은 상품 반복)으로 다시 재고, 틀린 사진도 함께 납품해요</div>')

    pk = [("모델 학습", "라벨 있는 사진 1,000장 이하 · 성능 리포트 · 폴더 일괄 검사 프로그램", "150,000원"),
          ("자동 라벨링+학습", "라벨 없는 사진 500장 이하, 대상 3종 이하 · 위 내용 포함", "250,000원")]
    rows_html = "".join(f'<tr><td style="padding:13px;font-weight:800">{e(a)}</td><td style="padding:13px;font-size:13.5px">{e(b)}</td>'
                        f'<td class=num style="padding:13px;font-weight:800;white-space:nowrap">{c}</td></tr>' for a, b, c in pk)
    yield page("vision-03", "패키지와 진행 방법", "착수 전에 사진 20~30장으로 가능한지 먼저 알려 드려요",
               f'<table class=box style="margin-top:12px;font-size:15px">{rows_html}</table>'
               '<div class=box style="margin-top:10px;padding:11px 16px;font-size:13px;line-height:1.65">'
               '· 학습은 작업 PC 그래픽카드에서 해요. 사진을 클라우드에 올리지 않아요<br>'
               '· 납품: 더블클릭 실행 프로그램 + 안내서 + 성능 리포트(틀린 사례 사진 포함)</div>'
               '<div style="margin-top:8px;background:#e9e6de;border-radius:14px;padding:8px 16px;font-size:12px;color:#685e51;line-height:1.6">'
               '<b style="color:#362f26">하지 않아요</b> · 사람이 한 장씩 하는 라벨링, 정확도 보장, 서버·앱 운영, 사진 수집, 얼굴 인식·감시 목적 작업</div>')


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    pngs = [shoot(p) for p in pages()]
    Image.open(pngs[0]).resize((652, 488), Image.LANCZOS).save(HERE / "vision-main-652.png")
    stack(pngs, HERE / "vision-detail.png")
    print([p.name for p in pngs])
