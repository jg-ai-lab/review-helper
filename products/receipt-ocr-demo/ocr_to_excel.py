"""거래명세서·영수증 사진을 PC 안에서 OCR로 읽어 엑셀 한 장으로 모으고, 정답이 있으면 채점한다.

사용법 (.venv-ocr 환경):
  python ocr_to_excel.py photos_synth            사진 폴더를 읽어 results/photos_synth_변환결과.xlsx 저장
  python ocr_to_excel.py photos_synth --reuse    OCR은 건너뛰고 저장해 둔 인식 결과로 다시 정리·채점
  python ocr_to_excel.py photos_synth --raw      보정(수량 채우기·단가표 품목 이름 고치기) 없이 채점
  python ocr_to_excel.py docs --fast             가벼운 글자 찾기 모델 사용(CPU에서 빠름)

인터넷으로 사진을 보내지 않습니다. 처음 한 번만 OCR 모델을 내려받습니다.
결과 엑셀 시트: 문서(문서별 날짜·거래처·합계), 품목(줄별), 확인 필요(사람이 볼 칸과 이유).
docs/정답.json이 있으면 정확도 시트와 results/<폴더>_정확도.md도 만듭니다.
"""
import difflib
import json
import math
import re
import statistics
import sys
import time
import unicodedata
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

HERE = Path(__file__).parent
RESULTS = HERE / "results"
IMAGE_TYPES = (".jpg", ".jpeg", ".png")
LOW_SCORE = 0.85  # 이보다 자신 없는 글자는 확인 필요로 표시


# ---------- OCR ----------

def run_ocr(paths, fast):
    from paddleocr import PaddleOCR
    opts = dict(lang="korean", use_doc_orientation_classify=False, use_doc_unwarping=False,
                use_textline_orientation=False, enable_mkldnn=False)
    if fast:  # 모델 이름을 하나라도 정하면 lang이 무시되므로 한국어 인식 모델도 함께 정한다
        opts.update(text_detection_model_name="PP-OCRv5_mobile_det",
                    text_recognition_model_name="korean_PP-OCRv5_mobile_rec")
    ocr = PaddleOCR(**opts)
    raw = {}
    for p in paths:
        t = time.time()
        r = ocr.predict(str(p))[0]
        raw[p.name] = [{"text": tx, "score": float(sc), "poly": [[float(x), float(y)] for x, y in poly]}
                       for tx, sc, poly in zip(r["rec_texts"], r["rec_scores"], r["rec_polys"])]
        print(f"  {p.name}: 글자 {len(raw[p.name])}줄, {time.time() - t:.1f}초", flush=True)
    return raw


# ---------- 줄 맞추기 ----------

def tokens_of(lines):
    """OCR 조각을 기울기를 바로잡은 좌표의 토큰으로 바꾼다."""
    angles = []
    for ln in lines:
        (x0, y0), (x1, y1) = ln["poly"][0], ln["poly"][1]
        w = math.hypot(x1 - x0, y1 - y0)
        h = math.hypot(ln["poly"][3][0] - x0, ln["poly"][3][1] - y0)
        if w > 2 * h:
            angles.append(math.atan2(y1 - y0, x1 - x0))
    a = -statistics.median(angles) if angles else 0.0
    toks = []
    for ln in lines:
        xs = [x * math.cos(a) - y * math.sin(a) for x, y in ln["poly"]]
        ys = [x * math.sin(a) + y * math.cos(a) for x, y in ln["poly"]]
        toks.append({"text": ln["text"].strip(), "score": ln["score"], "x0": min(xs), "x1": max(xs),
                     "cx": sum(xs) / 4, "cy": sum(ys) / 4, "h": max(ys) - min(ys)})
    return [t for t in toks if t["text"]]


def rows_of(toks):
    if not toks:
        return []
    mh = statistics.median(t["h"] for t in toks)
    rows = []
    for t in sorted(toks, key=lambda t: t["cy"]):
        if rows and abs(t["cy"] - statistics.mean(r["cy"] for r in rows[-1])) < 0.55 * mh:
            rows[-1].append(t)
        else:
            rows.append([t])
    return [sorted(r, key=lambda t: t["cx"]) for r in rows]


def num(text):
    d = re.sub(r"[^\d]", "", text)
    return int(d) if d else None


def is_num(text):
    return bool(re.fullmatch(r"[\d,.\s원]+", text)) and any(c.isdigit() for c in text)


def clean(name):
    """품목 이름 끝에 붙은 '-', '.' 같은 군더더기를 뗀다."""
    return re.sub(r"[^\w)]+$", "", name).strip() if name else name


def row_text(row):
    return " ".join(t["text"] for t in row)


def find_row(rows, *words, start=0):
    for i in range(start, len(rows)):
        s = row_text(rows[i]).replace(" ", "")
        if all(w in s for w in words):
            return i
    return None


def last_num(row):
    nums = [t for t in row if is_num(t["text"])]
    return (num(nums[-1]["text"]), nums[-1]["score"]) if nums else (None, 0)


def value_after(toks, key, pattern=None):
    """'상호: 값' 처럼 키 뒤의 값을 찾는다. 같은 조각에 없으면 바로 오른쪽 조각을 본다. 가장 왼쪽(공급자) 것을 쓴다."""
    for t in sorted((t for t in toks if key in t["text"].replace(" ", "")), key=lambda t: t["cx"]):
        v = re.sub(rf"^.*?{key}\s*[:;：]?\s*", "", t["text"].replace(" ", "") if pattern else t["text"]).strip()
        if not v:
            right = [u for u in toks if u["x0"] > t["x1"] - 5 and abs(u["cy"] - t["cy"]) < t["h"] * 0.6]
            if right:
                u = min(right, key=lambda u: u["x0"])
                v, t = u["text"].strip(), u
        if pattern:
            m = re.search(pattern, v)
            v = m.group(0) if m else v
        if v:
            return v, t["score"]
    return None, 0


# ---------- 문서 읽기 ----------

def parse(name, lines):
    toks = tokens_of(lines)
    rows = rows_of(toks)
    alltext = " ".join(t["text"] for t in toks)
    d = {"파일": name, "문서번호": None, "종류": None, "날짜": None, "거래처": None, "사업자번호": None,
         "품목": [], "공급가액": None, "세액": None, "합계": None, "확인": []}
    m = re.search(r"E\s?(\d{2})\b", alltext)
    d["문서번호"] = f"E{m.group(1)}" if m else None
    flat = alltext.replace(" ", "")
    if "명세서" in flat or "공급받는자" in flat:
        d["종류"] = "거래명세서"
        parse_statement(d, toks, rows)
    elif "상품명" in flat or "과세" in flat:
        d["종류"] = "영수증"
        parse_receipt(d, toks, rows)
    check(d)
    return d


def parse_statement(d, toks, rows):
    for t in toks:
        m = re.search(r"(20\d\d)\D{1,3}(\d{1,2})\D{1,3}(\d{1,2})", t["text"])
        if m and "일자" in t["text"].replace(" ", ""):
            d["날짜"] = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    d["거래처"], s1 = value_after(toks, "상호")
    # 등록번호는 공급자·공급받는자 두 개가 있으므로 가장 왼쪽(공급자) 번호를 쓴다
    biz = sorted((t for t in toks if re.search(r"\d{3}-?\d{2}-?\d{5}", t["text"])), key=lambda t: t["cx"])
    d["사업자번호"] = re.search(r"\d{3}-?\d{2}-?\d{5}", biz[0]["text"]).group(0) if biz else None
    s2 = biz[0]["score"] if biz else 0
    if min(s1, s2) < LOW_SCORE:
        d["확인"].append(("거래처·등록번호", "글자 인식 자신 없음"))
    head = find_row(rows, "품목", "단가")
    end = find_row(rows, "합계", start=(head or 0) + 1)
    if head is None:
        d["확인"].append(("품목 표", "표 머리글(품목·단가)을 찾지 못함"))
    else:
        cols = {}
        for key in ("품목", "규격", "수량", "단가", "공급가액", "세액"):
            hit = [t for t in rows[head] if key in t["text"].replace(" ", "")]
            if key == "세액":
                hit = [t for t in hit if "공급" not in t["text"]]
            if hit:
                cols[key] = hit[0]["cx"]
        for row in rows[head + 1:end]:
            if not row:
                continue
            if len(row) == 6:  # 칸이 다 있으면 순서대로
                vals = dict(zip(["품목", "규격", "수량", "단가", "공급가액", "세액"], row))
            else:
                vals = {}
                for t in row:
                    key = min(cols, key=lambda k: abs(cols[k] - t["cx"]))
                    vals[key] = t if key not in vals else {**vals[key], "text": vals[key]["text"] + t["text"],
                                                           "score": min(vals[key]["score"], t["score"])}
            if not any(k in vals for k in ("품목", "공급가액")):
                continue
            item = {"품목": clean(vals.get("품목", {}).get("text")), "규격": vals.get("규격", {}).get("text"),
                    "수량": num(vals["수량"]["text"]) if "수량" in vals else None,
                    "단가": num(vals["단가"]["text"]) if "단가" in vals else None,
                    "금액": num(vals["공급가액"]["text"]) if "공급가액" in vals else None,
                    "세액": num(vals["세액"]["text"]) if "세액" in vals else None,
                    # 숫자는 수량×단가·합계 대조로 확인하므로, 인식 점수는 글자 칸(품목·규격)만 본다
                    "점수": min([vals[k]["score"] for k in ("품목", "규격") if k in vals] or [1.0])}
            d["품목"].append(item)
    for words, key in [(("공급가액", "합계"), "공급가액"), (("세액", "합계"), "세액"), (("합계", "금액"), "합계")]:
        i = find_row(rows, *words, start=end or 0)
        if i is not None:
            d[key], sc = last_num(rows[i])
            if sc < LOW_SCORE:
                d["확인"].append((key, "글자 인식 자신 없음"))


def parse_receipt(d, toks, rows):
    m = re.search(r"(20\d\d)[-.](\d{1,2})[-.](\d{1,2})", " ".join(t["text"] for t in toks))
    if m:
        d["날짜"] = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    biz = next((t for t in toks if "사업자" in t["text"].replace(" ", "")), None)
    m = re.search(r"\d{3}-?\d{2}-?\d{5}", " ".join(t["text"] for t in toks))
    d["사업자번호"] = m.group(0) if m else None
    if biz:
        above = [t for t in toks if t["cy"] < biz["cy"] - biz["h"] * 0.5 and not re.fullmatch(r"E\s?\d{2}", t["text"])]
        if above:
            name = max(above, key=lambda t: t["h"])
            d["거래처"] = name["text"]
            if name["score"] < LOW_SCORE:
                d["확인"].append(("거래처", "글자 인식 자신 없음"))
    head = find_row(rows, "상품명")
    end = find_row(rows, "과세", start=(head or 0) + 1)
    if head is None:
        d["확인"].append(("품목 표", "머리글(상품명)을 찾지 못함"))
    else:
        for row in rows[head + 1:end]:
            first = row[0]["text"]
            if len(row) == 1 and re.match(r"^[^\d가-힣]?\s*[\d,.]+$", first) and d["품목"]:
                d["품목"][-1]["단가"] = num(first)
                continue
            words = [t for t in row if not is_num(t["text"])]
            nums = [t for t in row if is_num(t["text"])]
            if not words:
                continue
            item = {"품목": clean("".join(t["text"] for t in words)), "규격": None,
                    "수량": num(nums[0]["text"]) if len(nums) >= 2 else None,
                    "단가": None, "금액": num(nums[-1]["text"]) if nums else None, "세액": None,
                    "점수": min(t["score"] for t in words)}
            d["품목"].append(item)
    for word, key in [("과세", "공급가액"), ("부가세", "세액")]:
        i = find_row(rows, word, start=end or 0)
        if i is not None:
            d[key], _ = last_num(rows[i])
    i = next((i for i in range(end or 0, len(rows))
              if re.search(r"합\s*계", row_text(rows[i])) and "과세" not in row_text(rows[i])), None)
    if i is not None:
        d["합계"], sc = last_num(rows[i])
        if sc < LOW_SCORE:
            d["확인"].append(("합계", "글자 인식 자신 없음"))


def fix(d, catalog):
    """사람이 확인할 수 있게 표시를 남기고 흔한 OCR 실수를 고친다."""
    for i, it in enumerate(d["품목"], 1):
        # 한 글자 숫자(수량 1 등)는 놓치기 쉽다: 금액÷단가가 나누어떨어지면 채운다
        if it["수량"] is None and it["단가"] and it["금액"] and it["금액"] % it["단가"] == 0:
            it["수량"] = it["금액"] // it["단가"]
            d["확인"].append((f"{i}번째 줄", f"수량을 읽지 못해 금액÷단가로 채움({it['수량']})"))
        # 영문 o와 숫자 0, 띄어쓰기 등: 단가표 품목 이름 중 아주 비슷한 것으로 고친다
        if catalog and it["품목"]:
            # 자모 단위로 비교해야 '흘'↔'홀'처럼 모음 하나 틀린 것을 비슷하다고 본다
            key = unicodedata.normalize("NFD", norm(it["품목"]))
            keys = {unicodedata.normalize("NFD", norm(c)): c for c in catalog}
            if key not in keys:
                hit = difflib.get_close_matches(key, list(keys), n=1, cutoff=0.8)
                if hit:
                    d["확인"].append((f"{i}번째 줄", f"품목 이름을 단가표로 고침: {it['품목']} → {keys[hit[0]]}"))
                    it["품목"] = keys[hit[0]]
                else:
                    d["확인"].append((f"{i}번째 줄", f"단가표에 없는 품목: {it['품목']}"))


def check(d):
    for key in ("문서번호", "종류", "날짜", "거래처", "합계"):
        if not d[key]:
            d["확인"].append((key, "읽지 못함"))
    for i, it in enumerate(d["품목"], 1):
        if it["수량"] and it["단가"] and it["금액"] and it["수량"] * it["단가"] != it["금액"]:
            d["확인"].append((f"{i}번째 줄", f"수량×단가({it['수량'] * it['단가']:,})와 금액({it['금액']:,})이 다름"))
        if it["점수"] < LOW_SCORE:
            d["확인"].append((f"{i}번째 줄", "글자 인식 자신 없음"))
        if any(it[k] is None for k in ("품목", "수량", "금액")):
            d["확인"].append((f"{i}번째 줄", "빈 칸이 있음"))
    amounts = [it["금액"] or 0 for it in d["품목"]]
    if d["종류"] == "거래명세서" and d["공급가액"] is not None and sum(amounts) != d["공급가액"]:
        d["확인"].append(("공급가액", f"품목 금액 합({sum(amounts):,})과 문서 합계({d['공급가액']:,})가 다름"))
    if d["종류"] == "영수증" and d["합계"] is not None and sum(amounts) != d["합계"]:
        d["확인"].append(("합계", f"품목 금액 합({sum(amounts):,})과 영수증 합계({d['합계']:,})가 다름"))
    if None not in (d["공급가액"], d["세액"], d["합계"]) and d["공급가액"] + d["세액"] != d["합계"]:
        d["확인"].append(("합계", "공급가액+세액과 합계가 다름"))


# ---------- 채점 ----------

def norm(v):
    return re.sub(r"\s", "", str(v)) if v is not None else None


def score(docs, answer):
    truth = {a["문서번호"]: a for a in answer}
    doc_fields = ["종류", "날짜", "거래처", "사업자번호", "공급가액", "세액", "합계"]
    stats = {f: [0, 0] for f in doc_fields + ["품목", "규격", "수량", "단가", "금액"]}
    rows = []
    for d in docs:
        a = truth.get(d["문서번호"]) or truth.get(Path(d["파일"]).stem)
        if not a:
            continue
        errs = []
        for f in doc_fields:
            ok = norm(d[f]) == norm(a[f])
            stats[f][0] += ok
            stats[f][1] += 1
            if not ok:
                errs.append(f"{f}: {d[f]} (정답 {a[f]})")
        for i, al in enumerate(a["품목"]):
            got = d["품목"][i] if i < len(d["품목"]) else {}
            for f in ("품목", "규격", "수량", "단가", "금액"):
                if f == "규격" and a["종류"] == "영수증":
                    continue
                ok = norm(got.get(f)) == norm(al[f])
                stats[f][0] += ok
                stats[f][1] += 1
                if not ok:
                    errs.append(f"{i + 1}번째 줄 {f}: {got.get(f)} (정답 {al[f]})")
        if len(d["품목"]) != len(a["품목"]):
            errs.append(f"품목 줄 수 {len(d['품목'])} (정답 {len(a['품목'])})")
        rows.append({"문서": a["문서번호"], "틀린 칸": len(errs), "확인 필요 표시": bool(d["확인"]), "내용": errs})
    return stats, rows


# ---------- 저장 ----------

def save(docs, stats, rows, out_xlsx, md_path, title, elapsed):
    wb = Workbook()
    bold = Font(bold=True)
    yellow = PatternFill("solid", fgColor="FFF2B3")
    ws = wb.active
    ws.title = "문서"
    ws.append(["파일", "문서번호", "종류", "날짜", "거래처", "사업자번호", "품목 수", "공급가액", "세액", "합계", "확인 필요"])
    for d in docs:
        ws.append([d["파일"], d["문서번호"], d["종류"], d["날짜"], d["거래처"], d["사업자번호"], len(d["품목"]),
                   d["공급가액"], d["세액"], d["합계"], len(d["확인"]) or ""])
        if d["확인"]:
            for c in ws[ws.max_row]:
                c.fill = yellow
    ws2 = wb.create_sheet("품목")
    ws2.append(["문서번호", "줄", "품목", "규격", "수량", "단가", "금액", "세액", "인식 점수"])
    for d in docs:
        for i, it in enumerate(d["품목"], 1):
            ws2.append([d["문서번호"], i, it["품목"], it["규격"], it["수량"], it["단가"], it["금액"], it["세액"],
                        round(it["점수"], 2)])
            if it["점수"] < LOW_SCORE:
                for c in ws2[ws2.max_row]:
                    c.fill = yellow
    ws3 = wb.create_sheet("확인 필요")
    ws3.append(["파일", "문서번호", "칸", "이유"])
    for d in docs:
        for where, why in d["확인"]:
            ws3.append([d["파일"], d["문서번호"], where, why])
    if stats:
        ws4 = wb.create_sheet("정확도")
        ws4.append(["항목", "맞음", "전체", "정확도"])
        for f, (ok, n) in stats.items():
            if n:
                ws4.append([f, ok, n, round(ok / n, 3)])
    for sheet in wb.worksheets:
        for c in sheet[1]:
            c.font = bold
        for col in sheet.columns:
            sheet.column_dimensions[col[0].column_letter].width = 14
        for row in sheet.iter_rows(min_row=2):
            for c in row:
                if isinstance(c.value, int) and c.value >= 1000:
                    c.number_format = "#,##0"
    wb.save(out_xlsx)

    if stats:
        cells_ok = sum(ok for ok, n in stats.values())
        cells = sum(n for ok, n in stats.values())
        perfect = sum(r["틀린 칸"] == 0 for r in rows)
        wrong_docs = [r for r in rows if r["틀린 칸"]]
        caught = sum(r["확인 필요 표시"] for r in wrong_docs)
        false_alarm = sum(r["확인 필요 표시"] for r in rows if not r["틀린 칸"])
        lines = [f"# OCR 정확도 · {title}", "",
                 f"- 문서 {len(rows)}장, 칸 {cells}개 중 {cells_ok}개 맞음 (**{cells_ok / cells:.1%}**)",
                 f"- 모든 칸이 맞은 문서: {perfect}/{len(rows)}장",
                 f"- 틀린 칸이 있는 문서 {len(wrong_docs)}장 중 '확인 필요'로 표시된 문서: {caught}장",
                 f"- 다 맞았는데 '확인 필요'로 표시된 문서: {false_alarm}장",
                 f"- OCR 시간: {elapsed}", "",
                 "| 항목 | 맞음/전체 | 정확도 |", "| --- | --- | --- |"]
        lines += [f"| {f} | {ok}/{n} | {ok / n:.1%} |" for f, (ok, n) in stats.items() if n]
        lines += ["", "## 틀린 칸", ""]
        for r in rows:
            for e in r["내용"]:
                lines.append(f"- {r['문서']} {e}{'' if r['확인 필요 표시'] else ' **(확인 필요 표시 없음)**'}")
        if not wrong_docs:
            lines.append("- 없음")
        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("\n".join(lines[:7]))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    folder = HERE / (args[0] if args else "photos_synth")
    RESULTS.mkdir(exist_ok=True)
    tag = folder.name + ("_fast" if "--fast" in sys.argv else "")
    cache = RESULTS / f"{tag}_ocr.json"
    elapsed = "저장된 인식 결과 사용"
    if "--reuse" in sys.argv and cache.exists():
        raw = json.loads(cache.read_text(encoding="utf-8"))
        old_md = RESULTS / f"{tag}_정확도.md"  # 이전에 잰 OCR 시간을 이어서 적는다
        if old_md.exists():
            m = re.search(r"^- OCR 시간: (.+)$", old_md.read_text(encoding="utf-8"), re.M)
            if m and "저장된" not in m.group(1):
                elapsed = m.group(1)
    else:
        paths = sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGE_TYPES)
        print(f"{folder.name}: 사진 {len(paths)}장 OCR 시작")
        t = time.time()
        raw = run_ocr(paths, "--fast" in sys.argv)
        secs = time.time() - t
        elapsed = f"{len(paths)}장 {secs / 60:.1f}분 (장당 {secs / max(len(paths), 1):.0f}초, CPU{', 가벼운 모델' if '--fast' in sys.argv else ''})"
        cache.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    # 정답·단가표는 같은 세트의 docs 폴더에서 읽는다 (photos_synth2 → docs2)
    n = re.search(r"\d+$", folder.name)
    answer = HERE / f"docs{n.group(0) if n else ''}" / "정답.json"
    catalog_file = answer.with_name("품목목록.txt")
    docs = [parse(name, lines) for name, lines in raw.items()]
    if "--raw" in sys.argv:  # 보정 없이 OCR 그대로 채점
        tag += "_보정없음"
    else:
        catalog = ([l.strip() for l in catalog_file.read_text(encoding="utf-8").splitlines() if l.strip()]
                   if catalog_file.exists() else [])
        for d in docs:
            fix(d, catalog)
    stats, rows = score(docs, json.loads(answer.read_text(encoding="utf-8"))) if answer.exists() else ({}, [])
    out = RESULTS / f"{tag}_변환결과.xlsx"
    save(docs, stats, rows, out, RESULTS / f"{tag}_정확도.md", tag, elapsed)
    print(f"→ {out}")


if __name__ == "__main__":
    main()
