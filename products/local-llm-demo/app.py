"""인터넷 없이 돌아가는 사내 규정 Q&A (서비스 D).

이 PC의 Ollama(127.0.0.1:11434)만 호출합니다. PDF를 읽을 때만 pypdf가 필요합니다.

사용법:
  python app.py                색인이 없거나 문서가 바뀌었으면 색인 후 채팅 화면 열기 (exe 더블클릭과 같음)
  python app.py index          docs/ 문서(.md .txt .pdf)를 잘라 임베딩하고 index.json 저장
  python app.py ask "질문"      터미널에서 한 번 질문
  python app.py serve          채팅 화면만 열기

채팅 화면의 [문서 관리]에서 문서를 올리거나 빼면 바뀐 부분만 바로 다시 색인합니다.
뺀 문서는 지우지 않고 '뺀 문서' 폴더로 옮깁니다.

설정은 실행 파일 옆 config.json으로 바꿉니다 (company, contact, docs, port, chat_model, think).
"""
import json
import math
import re
import shutil
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
CONFIG = {"company": "샘플테크(가상 회사)", "contact": "인사팀", "docs": "docs", "port": 8765,
          "chat_model": "qwen3:8b", "think": True}
if (HERE / "config.json").exists():
    CONFIG.update(json.loads((HERE / "config.json").read_text(encoding="utf-8-sig")))
DOCS = HERE / CONFIG["docs"]
INDEX = HERE / "index.json"
REMOVED = HERE / "뺀 문서"
DOC_TYPES = (".md", ".txt", ".pdf")
MAX_UPLOAD_MB = 50
OLLAMA = "http://127.0.0.1:11434"
EMBED_MODEL = "bge-m3"
CHAT_MODEL = CONFIG["chat_model"]
TOP_K = 4
MIN_SCORE = 0.45
THINK = CONFIG["think"]  # 추론 모드: 예외 조건을 더 잘 읽지만 그래픽카드가 없으면 매우 느림

NOT_FOUND = f"규정 문서에서 찾지 못했습니다. {CONFIG['contact']}에 확인해 주세요."
SYSTEM = f"""너는 '{CONFIG['company']}'의 사내 규정 안내 도우미다.
아래 [자료]에 있는 내용만 근거로 한국어로 짧고 정확하게 답한다.
- 답의 근거가 된 문서 이름을 문장 끝에 [문서명] 형식으로 붙인다.
- 자료에 없는 내용은 추측하지 말고 "{NOT_FOUND}"라고 답한다.
- 숫자(일수·금액·기한)는 자료에 적힌 그대로 쓴다.
- 괄호 안이나 '단', '~는 제외' 같은 예외 조건(지역·대상·기간별로 다른 값)을 먼저 확인하고, 질문 조건에 맞는 값을 답한다."""


def post(path, payload):
    req = urllib.request.Request(OLLAMA + path, json.dumps(payload).encode(),
                                 {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.load(r)
    except urllib.error.URLError as e:
        raise SystemExit("Ollama에 연결할 수 없습니다. 작업 표시줄에서 Ollama가 켜져 있는지 확인하고 "
                         f"'설치.bat'을 다시 실행해 주세요. ({e.reason})")


def post_stream(path, payload):
    req = urllib.request.Request(OLLAMA + path, json.dumps(payload).encode(),
                                 {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            for line in r:
                if line.strip():
                    yield json.loads(line)
    except urllib.error.URLError as e:
        raise SystemExit("Ollama에 연결할 수 없습니다. 작업 표시줄에서 Ollama가 켜져 있는지 확인하고 "
                         f"'설치.bat'을 다시 실행해 주세요. ({e.reason})")


def embed(texts):
    return post("/api/embed", {"model": EMBED_MODEL, "input": texts})["embeddings"]


def read_text(path):
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    for enc in ("utf-8-sig", "cp949"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"{path.name}: 글자 인코딩을 읽을 수 없습니다")


def chunks(path):
    """마크다운은 제목 아래 줄을 3개씩, 그 밖의 문서는 약 400자씩 묶어 조각으로 나눈다."""
    lines = [l.strip() for l in read_text(path).splitlines()
             if l.strip() and not re.match(r"^\|\s*-", l.strip())]
    if not lines:
        return
    if lines[0].startswith("#"):
        title, lines = lines[0].lstrip("# ").strip(), lines[1:]
    else:
        title = path.stem
    buf = []
    for line in lines:
        buf.append(line)
        full = len(buf) >= 3 if path.suffix.lower() == ".md" else sum(map(len, buf)) >= 400
        if full:
            yield title, "\n".join(buf)
            buf = []
    if buf:
        yield title, "\n".join(buf)


def doc_files():
    return sorted(p for p in DOCS.rglob("*") if p.suffix.lower() in DOC_TYPES)


def build_index(old=()):
    """docs 폴더를 다시 색인한다. 이전 색인(old)에 같은 조각이 있으면 임베딩을 다시 하지 않는다."""
    cache = {(it["title"], it["text"]): it["vec"] for it in old}
    items = [{"doc": p.name, "title": t, "text": c} for p in doc_files() for t, c in chunks(p)]
    todo = [it for it in items if (it["title"], it["text"]) not in cache]
    for i in range(0, len(todo), 32):
        batch = todo[i:i + 32]
        for it, v in zip(batch, embed([f"{it['title']}\n{it['text']}" for it in batch])):
            cache[(it["title"], it["text"])] = v
    for it in items:
        it["vec"] = cache[(it["title"], it["text"])]
    INDEX.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    return items


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


def search(question, items):
    q = embed([question])[0]
    scored = sorted(((cosine(q, it["vec"]), it) for it in items), key=lambda s: -s[0])
    return [(s, it) for s, it in scored[:TOP_K] if s >= MIN_SCORE]


def chat_request(question, hits, stream):
    context = "\n\n".join(f"[{it['doc']} · {it['title']}]\n{it['text']}" for _, it in hits)
    return {
        "model": CHAT_MODEL, "stream": stream, "think": THINK,
        "options": {"temperature": 0.1},
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": f"[자료]\n{context}\n\n[질문]\n{question}"}],
    }


def answer(question, items):
    hits = search(question, items)
    if not hits:
        return {"answer": NOT_FOUND, "sources": []}
    res = post("/api/chat", chat_request(question, hits, False))
    text = re.sub(r"<think>.*?</think>", "", res["message"]["content"], flags=re.S).strip()
    return {"answer": text, "sources": pick_sources(text, hits)}


def answer_stream(question, items):
    """답을 만들어지는 대로 조각({"t": 글자})으로 내보내고, 끝에 {"sources": [...]}를 낸다."""
    hits = search(question, items)
    if not hits:
        yield {"t": NOT_FOUND}
        yield {"sources": []}
        return
    yield {"status": "답을 쓰는 중…" if not THINK else "규정을 읽고 생각하는 중…"}
    text = ""
    for part in post_stream("/api/chat", chat_request(question, hits, True)):
        t = part.get("message", {}).get("content", "")
        if t:
            text += t
            yield {"t": t}
    yield {"sources": pick_sources(text, hits)}


def pick_sources(text, hits):
    if "찾지 못했" in text:
        return []
    sources = []
    for s, it in hits:
        if it["doc"] not in [x["doc"] for x in sources]:
            sources.append({"doc": it["doc"], "title": it["title"], "score": round(s, 2), "text": it["text"]})
    cited = [x for x in sources if Path(x["doc"]).stem in text or x["title"] in text]
    return cited or sources


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
.warn{font-size:12px;color:#9a8f80;margin-top:18px}
#mg{margin:0 0 16px;background:#fffaf2;border:1px solid #d6ccbd;border-radius:14px;padding:4px 18px}#mg>summary{padding:10px 0;font-weight:700}
.drop{display:block;border:2px dashed #c9bda9;border-radius:10px;padding:16px;text-align:center;color:#685e51;font-size:14px;margin:6px 0 10px;cursor:pointer}
.drop.on{background:#efe6d6}#st{font-size:13px;min-height:18px;margin-bottom:8px;white-space:pre-wrap}
ul{list-style:none;padding:0;margin:0 0 12px;max-height:260px;overflow:auto}li{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:6px 0;border-top:1px solid #ece4d6;font-size:14px}
li span{overflow-wrap:anywhere}li small{color:#9a8f80}li button{padding:4px 10px;font-size:13px;background:#a0624f;flex:none}</style>
<main><span class=badge>인터넷 연결 없이 이 PC에서만 실행</span><h1>사내 규정 도우미</h1>
<p class=sub>__COMPANY__ 규정 문서 <b id=cnt>__COUNT__</b>개에서 찾아 답하고, 근거 문서를 함께 보여 줍니다.</p>
<details id=mg><summary>문서 관리 (올리기·빼기)</summary>
<label class=drop id=drop>여기로 파일을 끌어 놓거나 눌러서 고르세요<br><small>PDF·TXT·MD, 여러 개 가능. 한글·워드·엑셀은 PDF로 저장해서 올려 주세요.</small>
<input type=file id=file multiple accept=".pdf,.txt,.md" hidden></label>
<div id=st></div><ul id=docs></ul></details>
<form id=f><input id=q placeholder="궁금한 규정을 물어보세요" autocomplete=off><button>질문</button></form>
<div id=log></div><p class=warn>AI가 틀릴 수 있습니다. 중요한 내용은 근거 문서를 확인하세요.</p></main>
<script>
const f=document.getElementById('f'),q=document.getElementById('q'),log=document.getElementById('log');
const esc=s=>s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const H={'X-Local-App':'1'},st=document.getElementById('st'),ul=document.getElementById('docs'),drop=document.getElementById('drop'),file=document.getElementById('file');
const kb=n=>n<1048576?Math.ceil(n/1024)+'KB':(n/1048576).toFixed(1)+'MB';
async function loadDocs(){const r=await fetch('/docs').then(r=>r.json());document.getElementById('cnt').textContent=r.docs.length;
ul.innerHTML=r.docs.map(d=>'<li><span>'+esc(d.name)+' <small>'+kb(d.size)+(d.chunks?'':' · 글자를 읽지 못함')+'</small></span><button data-n="'+esc(d.name).replace(/"/g,'&quot;')+'">빼기</button></li>').join('')}
ul.onclick=async e=>{const n=e.target.dataset.n;if(!n||!confirm(n+" 문서를 뺄까요?\\n(파일은 '뺀 문서' 폴더로 옮겨 둡니다)"))return;
st.textContent='문서를 빼고 다시 읽는 중…';const r=await fetch('/delete',{method:'POST',headers:H,body:JSON.stringify({name:n})}).then(r=>r.json());st.textContent=r.message;loadDocs()};
async function upload(files){for(const f of files){st.textContent=f.name+' 올리고 읽는 중… (큰 PDF는 몇 분 걸릴 수 있어요)';
const r=await fetch('/upload',{method:'POST',headers:{...H,'X-Filename':encodeURIComponent(f.name)},body:f}).then(r=>r.json()).catch(()=>({message:f.name+': 올리지 못했습니다'}));
st.textContent=r.message;await loadDocs()}}
file.onchange=()=>{upload([...file.files]);file.value=''};
drop.ondragover=e=>{e.preventDefault();drop.classList.add('on')};drop.ondragleave=()=>drop.classList.remove('on');
drop.ondrop=e=>{e.preventDefault();drop.classList.remove('on');upload([...e.dataTransfer.files])};loadDocs();
f.onsubmit=async e=>{e.preventDefault();const text=q.value.trim();if(!text)return;q.value='';
const box=document.createElement('div');box.className='qa';box.innerHTML='<div class=q>Q. '+esc(text)+'</div><div class=a>규정을 찾는 중…</div>';
log.prepend(box);const a=box.querySelector('.a'),t0=Date.now(),tick=setInterval(()=>{if(!started)a.dataset.s=Math.round((Date.now()-t0)/1000)},1000);
let started=false,r={sources:[]},buf='';
try{const res=await fetch('/ask',{method:'POST',headers:H,body:JSON.stringify({q:text})}),rd=res.body.getReader(),dec=new TextDecoder();
for(;;){const {done,value}=await rd.read();if(done)break;buf+=dec.decode(value,{stream:true});let i;
while((i=buf.indexOf('\\n'))>=0){const m=JSON.parse(buf.slice(0,i));buf=buf.slice(i+1);
if(m.status&&!started)a.textContent=m.status;if(m.t){if(!started){started=true;a.textContent=''}a.textContent+=m.t}
if(m.sources)r=m;if(m.message){started=true;a.textContent=m.message}}}}
catch(err){a.textContent='답을 받지 못했습니다. 검은 창이 켜져 있는지 확인해 주세요.'}clearInterval(tick);
if(r.sources.length){box.insertAdjacentHTML('beforeend','<div class=src>근거 문서'+r.sources.map(s=>
'<details><summary>'+esc(s.title)+' ('+esc(s.doc)+')</summary><pre>'+esc(s.text)+'</pre></details>').join('')+'</div>')}};
</script></html>"""


def serve(items, port=CONFIG["port"]):
    page = (PAGE.replace("__COMPANY__", CONFIG["company"])
            .replace("__COUNT__", str(len({it["doc"] for it in items}))))
    state = {"items": items}
    lock = threading.Lock()

    def reindex():
        state["items"] = build_index(state["items"])

    def doc_list():
        counts = {}
        for it in state["items"]:
            counts[it["doc"]] = counts.get(it["doc"], 0) + 1
        return [{"name": p.name, "size": p.stat().st_size, "chunks": counts.get(p.name, 0)} for p in doc_files()]

    def upload(name, data):
        name = Path(name).name.strip()
        if Path(name).suffix.lower() not in DOC_TYPES:
            return f"{name}: PDF·TXT·MD 파일만 올릴 수 있습니다. 한글·워드·엑셀은 PDF로 저장해서 올려 주세요."
        DOCS.mkdir(exist_ok=True)
        path = DOCS / name
        backup = path.read_bytes() if path.exists() else None
        path.write_bytes(data)
        try:
            reindex()
        except Exception as e:  # 읽을 수 없는 파일은 되돌린다
            if backup is None:
                path.unlink()
            else:
                path.write_bytes(backup)
            reindex()
            return f"{name}: 문서를 읽지 못해 올리지 않았습니다. ({e})"
        n = sum(it["doc"] == name for it in state["items"])
        if n == 0:
            return f"{name}: 올렸지만 글자를 찾지 못했습니다. 스캔한 그림 PDF는 읽을 수 없습니다."
        return f"{name}: {'바꿔 ' if backup is not None else ''}올렸습니다. 이제 질문할 수 있어요."

    def remove(name):
        path = DOCS / Path(name).name
        if not path.is_file() or path.suffix.lower() not in DOC_TYPES:
            return f"{name}: 문서를 찾지 못했습니다."
        REMOVED.mkdir(exist_ok=True)
        dest = REMOVED / path.name
        if dest.exists():
            dest = REMOVED / f"{path.stem}_{time.strftime('%Y%m%d%H%M%S')}{path.suffix}"
        shutil.move(str(path), str(dest))
        reindex()
        return f"{name}: 뺐습니다. 파일은 '{REMOVED.name}' 폴더에 있습니다."

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _local(self):
            # 다른 웹사이트가 이 PC의 문서를 바꾸거나 묻지 못하게 주소와 헤더를 확인한다
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
            return host in ("127.0.0.1", "localhost") and self.headers.get("X-Local-App") == "1"

        def _send(self, body, ctype, code=200):
            data = body.encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _json(self, obj, code=200):
            self._send(json.dumps(obj, ensure_ascii=False), "application/json; charset=utf-8", code)

        def _stream(self, parts):
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
            self.end_headers()
            try:
                for part in parts:
                    self.wfile.write((json.dumps(part, ensure_ascii=False) + "\n").encode())
                    self.wfile.flush()
            except SystemExit as e:  # Ollama 연결 실패
                self.wfile.write((json.dumps({"message": str(e)}, ensure_ascii=False) + "\n").encode())
            except (BrokenPipeError, ConnectionResetError):
                pass  # 사용자가 창을 닫음

        def do_GET(self):
            if self.path == "/docs":
                self._json({"docs": doc_list()})
            else:
                self._send(page, "text/html; charset=utf-8")

        def do_POST(self):
            if not self._local():
                return self._json({"message": "허용되지 않은 요청입니다."}, 403)
            size = int(self.headers.get("Content-Length") or 0)
            if size > MAX_UPLOAD_MB * 1024 * 1024:
                self.close_connection = True
                return self._json({"message": f"{MAX_UPLOAD_MB}MB보다 큰 파일은 올릴 수 없습니다."}, 413)
            body = self.rfile.read(size)
            if self.path == "/ask":
                return self._stream(answer_stream(json.loads(body)["q"], state["items"]))
            try:
                with lock:
                    if self.path == "/upload":
                        msg = upload(urllib.parse.unquote(self.headers.get("X-Filename", "")), body)
                    else:
                        msg = remove(json.loads(body)["name"])
            except SystemExit as e:  # Ollama 연결 실패
                msg = str(e)
            self._json({"message": msg})

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"http://127.0.0.1:{port} 에서 실행 중입니다. 이 창을 닫으면 종료됩니다.")
    webbrowser.open(f"http://127.0.0.1:{port}")
    server.serve_forever()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "start"
    stale = not INDEX.exists() or any(p.stat().st_mtime > INDEX.stat().st_mtime for p in doc_files()) \
        or {p.name for p in doc_files()} != {it["doc"] for it in json.loads(INDEX.read_text(encoding="utf-8"))}
    if cmd == "index" or (cmd == "start" and stale):
        print("문서를 읽는 중입니다. 문서 수에 따라 몇 분 걸릴 수 있어요...")
        items = build_index(json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else [])
        if not items:
            raise SystemExit(f"'{DOCS.name}' 폴더에 읽을 문서(.md .txt .pdf)가 없습니다.")
        print(f"조각 {len(items)}개 색인 완료 → {INDEX.name}")
        if cmd == "index":
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
