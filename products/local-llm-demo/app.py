"""인터넷 없이 돌아가는 사내 규정 Q&A 데모 (서비스 D).

이 PC의 Ollama(127.0.0.1:11434)만 호출합니다. 외부 패키지가 필요 없습니다.

사용법:
  python app.py index          docs/ 문서를 잘라 임베딩하고 index.json 저장
  python app.py ask "질문"      터미널에서 한 번 질문
  python app.py serve          http://127.0.0.1:8765 에서 채팅 화면 열기
"""
import json
import math
import re
import sys
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).parent
DOCS = HERE / "docs"
INDEX = HERE / "index.json"
OLLAMA = "http://127.0.0.1:11434"
EMBED_MODEL = "bge-m3"
CHAT_MODEL = "qwen3:8b"
TOP_K = 4
MIN_SCORE = 0.45
THINK = True  # 추론 모드: 느리지만 예외 조건을 더 잘 읽음

SYSTEM = """너는 '샘플테크(가상 회사)'의 사내 규정 안내 도우미다.
아래 [자료]에 있는 내용만 근거로 한국어로 짧고 정확하게 답한다.
- 답의 근거가 된 문서 이름을 문장 끝에 [문서명] 형식으로 붙인다.
- 자료에 없는 내용은 추측하지 말고 "규정 문서에서 찾지 못했습니다. 인사팀에 확인해 주세요."라고 답한다.
- 숫자(일수·금액·기한)는 자료에 적힌 그대로 쓴다.
- 괄호 안이나 '단', '~는 제외' 같은 예외 조건(지역·대상·기간별로 다른 값)을 먼저 확인하고, 질문 조건에 맞는 값을 답한다."""


def post(path, payload):
    req = urllib.request.Request(OLLAMA + path, json.dumps(payload).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


def embed(texts):
    return post("/api/embed", {"model": EMBED_MODEL, "input": texts})["embeddings"]


def chunks(path):
    """제목 아래 목록 항목·표 행을 2~3개씩 묶어 조각으로 나눈다."""
    text = path.read_text(encoding="utf-8")
    title = text.splitlines()[0].lstrip("# ").strip()
    lines = [l for l in text.splitlines()[1:] if l.strip() and not re.match(r"^\|\s*-", l)]
    size = 3
    for i in range(0, len(lines), size):
        yield title, "\n".join(lines[i:i + size])


def build_index():
    items = [{"doc": p.name, "title": t, "text": c}
             for p in sorted(DOCS.glob("*.md")) for t, c in chunks(p)]
    vecs = embed([f"{it['title']}\n{it['text']}" for it in items])
    for it, v in zip(items, vecs):
        it["vec"] = v
    INDEX.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    return len(items)


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


def search(question, items):
    q = embed([question])[0]
    scored = sorted(((cosine(q, it["vec"]), it) for it in items), key=lambda s: -s[0])
    return [(s, it) for s, it in scored[:TOP_K] if s >= MIN_SCORE]


def answer(question, items):
    hits = search(question, items)
    if not hits:
        return {"answer": "규정 문서에서 찾지 못했습니다. 인사팀에 확인해 주세요.", "sources": []}
    context = "\n\n".join(f"[{it['doc']} · {it['title']}]\n{it['text']}" for _, it in hits)
    res = post("/api/chat", {
        "model": CHAT_MODEL, "stream": False, "think": THINK,
        "options": {"temperature": 0.1},
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": f"[자료]\n{context}\n\n[질문]\n{question}"}],
    })
    text = re.sub(r"<think>.*?</think>", "", res["message"]["content"], flags=re.S).strip()
    sources = []
    for s, it in hits:
        if it["doc"] not in [x["doc"] for x in sources]:
            sources.append({"doc": it["doc"], "title": it["title"], "score": round(s, 2), "text": it["text"]})
    return {"answer": text, "sources": sources}


PAGE = """<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>사내 규정 도우미</title><style>
*{box-sizing:border-box}body{margin:0;background:#f7f1e7;color:#362f26;font-family:"Malgun Gothic",system-ui,sans-serif}
main{max-width:760px;margin:0 auto;padding:28px 16px}h1{font-size:24px;margin:0 0 4px}.sub{color:#685e51;margin:0 0 18px;font-size:14px}
.badge{display:inline-block;background:#363e2f;color:#f7f1e7;font-size:12px;padding:3px 10px;border-radius:99px;margin-bottom:10px}
form{display:flex;gap:8px}input{flex:1;padding:12px 14px;border:1px solid #d6ccbd;border-radius:10px;font-size:16px;background:#fffaf2}
button{padding:0 18px;border:0;border-radius:10px;background:#5b6b4a;color:#fff;font-size:15px;cursor:pointer}
.qa{background:#fffaf2;border:1px solid #d6ccbd;border-radius:14px;padding:16px 18px;margin-top:14px}
.q{font-weight:700;margin-bottom:8px}.a{white-space:pre-wrap;line-height:1.6}.src{margin-top:12px;font-size:13px;color:#685e51}
details{margin-top:6px}summary{cursor:pointer}pre{white-space:pre-wrap;background:#f3efe6;padding:8px;border-radius:8px;font-size:12px}
.warn{font-size:12px;color:#9a8f80;margin-top:18px}</style>
<main><span class=badge>인터넷 연결 없이 이 PC에서만 실행</span><h1>사내 규정 도우미</h1>
<p class=sub>샘플테크(가상 회사) 규정 문서 20개에서 찾아 답하고, 근거 문서를 함께 보여 줍니다.</p>
<form id=f><input id=q placeholder="예: 배우자 출산 휴가는 며칠이에요?" autocomplete=off><button>질문</button></form>
<div id=log></div><p class=warn>AI가 틀릴 수 있습니다. 중요한 내용은 근거 문서를 확인하세요.</p></main>
<script>
const f=document.getElementById('f'),q=document.getElementById('q'),log=document.getElementById('log');
const esc=s=>s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
f.onsubmit=async e=>{e.preventDefault();const text=q.value.trim();if(!text)return;q.value='';
const box=document.createElement('div');box.className='qa';box.innerHTML='<div class=q>Q. '+esc(text)+'</div><div class=a>찾는 중…</div>';
log.prepend(box);const r=await fetch('/ask',{method:'POST',body:JSON.stringify({q:text})}).then(r=>r.json());
box.querySelector('.a').textContent=r.answer;
if(r.sources.length){box.insertAdjacentHTML('beforeend','<div class=src>근거 문서'+r.sources.map(s=>
'<details><summary>'+esc(s.title)+' ('+esc(s.doc)+')</summary><pre>'+esc(s.text)+'</pre></details>').join('')+'</div>')}};
</script></html>"""


def serve(items, port=8765):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, body, ctype):
            data = body.encode()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            self._send(PAGE, "text/html; charset=utf-8")

        def do_POST(self):
            q = json.loads(self.rfile.read(int(self.headers["Content-Length"])))["q"]
            self._send(json.dumps(answer(q, items), ensure_ascii=False), "application/json; charset=utf-8")

    print(f"http://127.0.0.1:{port} 에서 실행 중 (Ctrl+C로 종료)")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "serve"
    if cmd == "index":
        print(f"조각 {build_index()}개 색인 완료 → {INDEX.name}")
        return
    items = json.loads(INDEX.read_text(encoding="utf-8"))
    if cmd == "ask":
        r = answer(" ".join(sys.argv[2:]), items)
        print(r["answer"])
        for s in r["sources"]:
            print(f"  - {s['doc']} ({s['score']})")
    else:
        serve(items)


if __name__ == "__main__":
    main()
