"""서비스 D(로컬 LLM 사내 문서 Q&A) 크몽 이미지를 만듭니다.

사용법(저장소 루트, Ollama 실행 중): python marketing/kmong/render_llm.py
결과: marketing/kmong/llm-main.png, llm-0{2..5}.png (1304×976), llm-main-652.png, llm-detail.png
화면 속 답변은 products/local-llm-demo의 실제 답변을 그대로 씁니다.
"""
import json
import pathlib
import sys

from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DEMO = ROOT / "products" / "local-llm-demo"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(DEMO))
from render_details import CSS, e, shoot, stack  # noqa: E402
from app import INDEX, answer  # noqa: E402

TAG = "인터넷 없이 쓰는 사내 AI 비서"
NOTE = "화면 속 회사·문서는 가상입니다 · 최종 범위·비용·일정은 착수 전 합의합니다"
EXTRA = """.chat{background:#fffaf2;border:1px solid #d6ccbd;border-radius:14px;padding:14px 18px}
.q{font-weight:700;font-size:15px}.a{font-size:15px;line-height:1.55;margin-top:6px}
.src{margin-top:8px;font-size:12px;color:#685e51}.src b{background:#e9e6de;border-radius:6px;padding:2px 7px;font-weight:600;margin-right:4px}
.off{display:inline-flex;gap:6px;align-items:center;font-size:13px;font-weight:700;color:#5b6b4a;background:#e7eedf;border-radius:99px;padding:4px 12px}"""


def page(name, title, sub, body):
    doc = (f'<!doctype html><html lang="ko"><meta charset="utf-8"><title>{e(title)}</title>'
           f"<style>{CSS}{EXTRA}</style><span class=tag>{e(TAG)}</span><h1>{e(title)}</h1>"
           f"<p class=sub>{e(sub)}</p>{body}<div class=note>{e(NOTE)}</div></html>")
    path = HERE / f"{name}.html"
    path.write_text(doc, encoding="utf-8", newline="\n")
    return path


def chat(q, r, n_src=2):
    srcs = "".join(f"<b>{e(s['title'])}</b>" for s in r["sources"][:n_src])
    src = f"<div class=src>근거 문서 {srcs}</div>" if srcs else ""
    return f'<div class=chat><div class=q>Q. {e(q)}</div><div class=a>{e(r["answer"])}</div>{src}</div>'


def pages(items):
    q1, q2 = "서울 출장 숙박비 한도는?", "회사 주차 지원금은 얼마예요?"
    r1, r2 = answer(q1, items), answer(q2, items)
    yield page("llm-main", "자료가 밖으로 안 나가는 AI 비서", "PC 한 대에 설치해 사내 문서를 찾아 답해요",
               '<div style="margin-top:16px"><span class=off>● 인터넷 연결 없이 실행</span></div>'
               f'<div style="margin-top:12px">{chat(q1, r1)}</div>')

    qs = ["고객 정보 때문에 ChatGPT를 못 쓰고 있나요?", "직원들이 규정·매뉴얼을 매번 물어보나요?",
          "문서는 많은데 찾는 데 시간이 오래 걸리나요?"]
    box = "".join(f'<div class=box style="padding:15px 20px;margin-top:11px;font-size:18px;font-weight:700">Q. {e(x)}</div>' for x in qs)
    yield page("llm-02", "이런 곳에 맞아요", "제조·병원 행정·세무 사무소·학원처럼 내부 자료가 중요한 작은 회사",
               f'<div style="margin-top:14px">{box}</div>')

    yield page("llm-03", "모르면 모른다고 답해요", "근거 문서가 있을 때만 답하고, 없으면 담당 부서를 안내해요",
               f'<div style="display:grid;gap:10px;margin-top:14px">{chat(q1, r1, 1)}{chat(q2, r2)}</div>'
               '<p style="margin-top:10px;font-size:13px;color:#685e51">실제 데모 답변 그대로 · 모든 답에 근거 문서를 펼쳐 볼 수 있어요</p>')

    pk = [("설치형 AI 채팅", "PC 1대 설치 · 채팅 화면 · 사용 안내", "150,000원"),
          ("사내 문서 Q&A", "+ 문서 200개 이하 검색 답변 · 근거 표시", "350,000원"),
          ("맞춤 업무 도구", "+ 반복 업무 기능 1개 · 결과 엑셀 저장", "650,000원~")]
    rows = "".join(f'<tr><td style="padding:13px;font-weight:800">{e(a)}</td><td style="padding:13px;font-size:14px">{e(b)}</td>'
                   f'<td class=num style="padding:13px;font-weight:800">{c}</td></tr>' for a, b, c in pk)
    yield page("llm-04", "패키지", "착수 전에 PC 사양을 보고 가능한 모델·속도를 먼저 알려 드려요",
               f'<table class=box style="margin-top:16px;font-size:16px">{rows}</table>'
               '<div style="margin-top:14px;background:#e9e6de;border-radius:14px;padding:12px 18px;font-size:13px;color:#685e51;line-height:1.7">'
               '<b style="color:#362f26">포함하지 않아요</b> · 답변 정확도 보장, 서버 구축·상시 유지보수, 모델 학습(파인튜닝), 외부 시스템 연동</div>')

    checks = json.loads((HERE / "llm-checks.json").read_text(encoding="utf-8"))
    rows = "".join(f'<tr><td style="padding:7px 12px">{e(c["q"])}</td><td style="padding:7px 12px">{e(c["expect"])}</td>'
                   f'<td style="padding:7px 12px;font-weight:800;color:#5b6b4a">{"통과" if c["ok"] else "실패"}</td></tr>'
                   for c in checks)
    yield page("llm-05", "확인표까지 드려요", "고객 문서로 만든 질문으로 답이 맞는지 점검한 결과를 함께 납품해요",
               f'<table class=box style="margin-top:14px;font-size:13px">{rows}</table>'
               '<p style="margin-top:8px;font-size:12px;color:#685e51">데모 점검 예시 (RTX 4070 Ti, 답변당 약 2~3초)</p>')


def run_checks(items):
    from check import CASES
    out = []
    for q, keys, doc in CASES:
        r = answer(q, items)
        ok = all(k in r["answer"] for k in keys) and (doc in [s["doc"] for s in r["sources"]] if doc else True)
        out.append({"q": q, "expect": keys[0].replace("찾지 못했", "문서에 없음 → 모른다고 답함"), "ok": ok})
    (HERE / "llm-checks.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    items = json.loads(INDEX.read_text(encoding="utf-8"))
    checks = run_checks(items)
    print(f"점검 {sum(c['ok'] for c in checks)}/{len(checks)}")
    pngs = [shoot(p) for p in pages(items)]
    Image.open(pngs[0]).resize((652, 488), Image.LANCZOS).save(HERE / "llm-main-652.png")
    stack(pngs, HERE / "llm-detail.png")
    print([p.name for p in pngs])
