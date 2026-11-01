"""사진 속 캔·병 개수 세기 (서비스 C 납품용 프로그램).

exe 옆 '사진넣기' 폴더의 사진을 모두 읽어 물건마다 상자를 그리고 개수를 셉니다.
결과는 '결과\\YYYYMMDD_HHMM\\' 에 개수.xlsx 와 상자를 그린 사진으로 저장합니다.
인터넷 연결과 그래픽카드 없이 동작합니다(model.onnx, onnxruntime CPU).

개발 중 실행: .venv\\Scripts\\python.exe products\\vision-demo\\count_app.py [사진 폴더]
"""
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import onnxruntime as ort
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from PIL import Image, ImageDraw, ImageFont, ImageOps

BASE = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent / "package"
DEFAULT = {"이름": {"1": "캔", "2": "병"}, "점수기준": 0.5, "확인기준": 0.3, "겹침기준": 0.6, "사진긴변": 800}
EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
COLORS = [(230, 120, 40), (40, 140, 220), (60, 170, 90), (190, 70, 160)]


def config():
    path = BASE / "config.json"
    cfg = dict(DEFAULT)
    if path.exists():
        cfg.update(json.loads(path.read_text(encoding="utf-8-sig")))
    return cfg


def font(size):
    for name in ("malgunbd.ttf", "malgun.ttf"):
        try:
            return ImageFont.truetype(f"C:/Windows/Fonts/{name}", size)
        except OSError:
            pass
    return ImageFont.load_default()


def detect(sess, img, cfg):
    """사진 한 장 → [(이름, 점수, 상자)], 점수 '확인기준' 이상만."""
    x = np.asarray(img, dtype=np.float32).transpose(2, 0, 1) / 255.0
    boxes, labels, scores = sess.run(None, {"image": x})
    names = cfg["이름"]
    found = []
    for i in np.argsort(-scores):  # 점수 높은 순. 종류가 달라도 거의 같은 자리면 한 물건으로 본다
        if scores[i] < cfg["확인기준"] or any(iou(boxes[i], b) > cfg["겹침기준"] for _, _, b in found):
            continue
        found.append((names.get(str(int(labels[i])), str(int(labels[i]))), float(scores[i]), boxes[i].tolist()))
    return found


def iou(a, b):
    w = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    h = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = w * h
    return inter / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter + 1e-9)


def draw(img, found, cfg, names):
    g = ImageDraw.Draw(img)
    f, small = font(max(16, img.width // 40)), font(max(14, img.width // 55))
    for name, s, b in found:
        sure = s >= cfg["점수기준"]
        color = COLORS[names.index(name) % len(COLORS)] if sure else (150, 150, 150)
        g.rectangle(b, outline=color, width=4 if sure else 2)
        g.text((b[0] + 4, b[1] + 2), f"{name} {s:.2f}" + ("" if sure else " ?"), font=small, fill=color,
               stroke_width=3, stroke_fill="white")
    counts = [f"{n} {sum(1 for x in found if x[0] == n and x[1] >= cfg['점수기준'])}개" for n in names]
    g.text((12, 10), "  ".join(counts), font=f, fill="black", stroke_width=4, stroke_fill="white")
    return img


def save_excel(rows, names, path):
    wb = Workbook()
    ws = wb.active
    ws.title = "사진별 개수"
    ws.append(["사진"] + names + ["합계", "확인 필요(애매한 상자)"])
    for r in rows:
        ws.append([r["파일"]] + [r[n] for n in names] + [sum(r[n] for n in names), r["애매"] or None])
    n = ws.max_row
    ws.append(["합계"] + [f"=SUM({c.column_letter}2:{c.column_letter}{n})" for c in ws[1][1:]])
    bold, head = Font(bold=True), PatternFill("solid", fgColor="E7EEDF")
    for c in ws[1]:
        c.font, c.fill = bold, head
    for c in ws[ws.max_row]:
        c.font = bold
    ws.column_dimensions["A"].width = 32
    ws.column_dimensions[ws.cell(1, ws.max_column).column_letter].width = 24
    ws.freeze_panes = "A2"
    note = wb.create_sheet("안내")
    for line in ["점수가 '점수기준' 이상인 상자만 개수에 넣었습니다.",
                 "'확인 필요'는 점수가 낮아 개수에서 뺀 상자 수입니다. 표시된 사진에서 회색 상자(?)를 확인해 주세요.",
                 "기준은 exe 옆 config.json에서 바꿀 수 있습니다."]:
        note.append([line])
    note.column_dimensions["A"].width = 100
    wb.save(path)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = config()
    names = list(dict.fromkeys(cfg["이름"].values()))
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE / "사진넣기"
    src.mkdir(exist_ok=True)
    photos = sorted(p for p in src.iterdir() if p.suffix.lower() in EXT)
    if not photos:
        print(f"'{src}' 폴더에 사진이 없습니다. 사진(jpg·png)을 넣고 다시 실행해 주세요.")
        return
    model = BASE / "model.onnx"
    if not model.exists():
        print(f"모델 파일이 없습니다: {model}")
        return
    out = BASE / "결과" / datetime.now().strftime("%Y%m%d_%H%M")
    (out / "표시된 사진").mkdir(parents=True, exist_ok=True)
    print(f"사진 {len(photos)}장을 셉니다. 처음 한 장은 준비 때문에 조금 더 걸립니다.\n")
    sess = ort.InferenceSession(str(model), providers=["CPUExecutionProvider"])
    rows, t0 = [], time.time()
    for i, p in enumerate(photos, 1):
        try:
            img = ImageOps.exif_transpose(Image.open(p)).convert("RGB")
        except Exception as e:  # 깨진 파일은 건너뛰고 표에 남긴다
            print(f"  [{i}/{len(photos)}] {p.name}: 열 수 없음({e.__class__.__name__})")
            rows.append({"파일": f"{p.name} (열 수 없음)", **{n: 0 for n in names}, "애매": 0})
            continue
        img.thumbnail((cfg["사진긴변"], cfg["사진긴변"]), Image.LANCZOS)
        found = detect(sess, img, cfg)
        row = {"파일": p.name, "애매": sum(1 for x in found if x[1] < cfg["점수기준"])}
        row.update({n: sum(1 for x in found if x[0] == n and x[1] >= cfg["점수기준"]) for n in names})
        rows.append(row)
        draw(img, found, cfg, names).save(out / "표시된 사진" / f"{p.stem}.jpg", quality=90)
        extra = f", 확인 필요 {row['애매']}" if row["애매"] else ""
        print(f"  [{i}/{len(photos)}] {p.name}: " + ", ".join(f"{n} {row[n]}" for n in names) + extra)
    save_excel(rows, names, out / "개수.xlsx")
    total = ", ".join(f"{n} {sum(r[n] for r in rows)}개" for n in names)
    print(f"\n완료: {total} ({(time.time() - t0) / len(photos):.1f}초/장)\n결과: {out}")
    if getattr(sys, "frozen", False):
        os.startfile(out)


if __name__ == "__main__":
    try:
        main()
    finally:
        if getattr(sys, "frozen", False):
            input("\n엔터를 누르면 창이 닫힙니다.")
