"""Open Images V7에서 캔·병 사진을 골라 내려받고 출처 목록(ATTRIBUTION.md)을 만든다.

사용법: python fetch_openimages.py
- 검증·시험 세트(validation, test) 중 '캔(Tin can)'·'병(Bottle)' 상자가 2~20개인 사진만 고릅니다.
- 라이선스가 CC BY 2.0으로 표시된 사진만 씁니다. 상업 홍보에 쓰려면 출처(작성자·원본 주소·라이선스)를 밝혀야 합니다.
- 사람·얼굴 상자가 있는 사진, 묶음 상자(IsGroupOf)·그림 속 물건(IsDepiction)이 있는 사진은 뺍니다.
  Open Images 라벨이 모든 사람을 표시하지는 않으므로 데모 이미지로 쓰기 전에 눈으로 다시 확인합니다.
- 사진은 openimages/images/, 상자 정보는 openimages/labels.json에 저장합니다(사진은 git에 올리지 않음).
"""
import csv
import json
import sys
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "openimages"
CACHE = OUT / "meta"
BASE = "https://storage.googleapis.com/openimages"
META = {s: (f"{BASE}/v5/{s}-annotations-bbox.csv", f"{BASE}/2018_04/{s}/{s}-images-with-rotation.csv")
        for s in ("validation", "test")}
CLASSES = {"/m/02jnhm": "캔", "/m/04dr76w": "병"}
PEOPLE = {"/m/01g317", "/m/0dzct", "/m/04yx4", "/m/03bt1vf", "/m/01bl7v", "/m/05r655", "/m/04hgtk", "/m/0k65p",
          "/m/035r7c", "/m/0283dt1", "/m/014sv8", "/m/039xj_", "/m/03q69", "/m/0k0pj", "/m/015h_t", "/m/031n1",
          "/m/0dzf4", "/m/02p0tk3"}  # 사람·얼굴·손 등 신체 부위
LICENSE = "https://creativecommons.org/licenses/by/2.0/"


def fetch(url, path):
    if not path.exists():
        print(f"  내려받는 중: {url}", flush=True)
        urllib.request.urlretrieve(url, path)
    return path


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    (OUT / "images").mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(exist_ok=True)
    picked = []
    for subset, (box_url, img_url) in META.items():
        boxes, bad = defaultdict(list), set()
        with open(fetch(box_url, CACHE / f"{subset}-boxes.csv"), encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["LabelName"] in PEOPLE:
                    bad.add(r["ImageID"])
                elif r["LabelName"] in CLASSES:
                    boxes[r["ImageID"]].append(r)
                    if r["IsGroupOf"] == "1" or r["IsDepiction"] == "1":
                        bad.add(r["ImageID"])
        with open(fetch(img_url, CACHE / f"{subset}-images.csv"), encoding="utf-8") as f:
            for m in csv.DictReader(f):
                bs = boxes.get(m["ImageID"])
                if bs and m["ImageID"] not in bad and m["License"] == LICENSE and 2 <= len(bs) <= 20:
                    picked.append({"id": m["ImageID"], "subset": subset, "title": m["Title"], "author": m["Author"],
                                   "author_url": m["AuthorProfileURL"], "source": m["OriginalLandingURL"],
                                   "license": m["License"], "rotation": m["Rotation"],
                                   "boxes": [{"label": CLASSES[b["LabelName"]], "xmin": float(b["XMin"]),
                                              "xmax": float(b["XMax"]), "ymin": float(b["YMin"]),
                                              "ymax": float(b["YMax"])} for b in bs]})
    picked.sort(key=lambda p: p["id"])
    print(f"고른 사진 {len(picked)}장, 상자 {Counter(b['label'] for p in picked for b in p['boxes'])}")
    for i, p in enumerate(picked, 1):
        dest = OUT / "images" / f"{p['id']}.jpg"
        if not dest.exists():
            urllib.request.urlretrieve(f"https://open-images-dataset.s3.amazonaws.com/{p['subset']}/{p['id']}.jpg", dest)
        if i % 25 == 0:
            print(f"  {i}/{len(picked)}장", flush=True)
    (OUT / "labels.json").write_text(json.dumps(picked, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = ["# 사진 출처 (Open Images V7)", "",
             "서비스 C 데모에 쓴 사진입니다. 모두 [CC BY 2.0](https://creativecommons.org/licenses/by/2.0/)으로 표시된 사진이며,",
             "상자 라벨은 Google의 Open Images([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/))입니다.",
             "Open Images는 사진마다 라이선스를 보증하지 않으므로, 홍보 이미지에 쓰는 사진은 원본 주소에서 라이선스를 다시 확인합니다.",
             "사진을 자르거나 탐지 상자를 그려 넣은 것은 변경에 해당합니다.", "",
             "| 사진 ID | 제목 | 작성자 | 원본 |", "| --- | --- | --- | --- |"]
    for p in picked:
        title = (p["title"] or "(제목 없음)").replace("|", "/")
        author = (p["author"] or "(이름 없음)").replace("|", "/")
        lines.append(f"| {p['id']} | {title} | [{author}]({p['author_url']}) | [Flickr]({p['source']}) |")
    (HERE / "ATTRIBUTION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"→ {OUT / 'images'} , {HERE / 'ATTRIBUTION.md'}")


if __name__ == "__main__":
    main()
