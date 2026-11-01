"""Open Images 캔·병 사진으로 물건 찾기(객체 탐지) 모델을 학습하고 시험 사진으로 성능을 잰다. (서비스 C 데모)

사용법 (.venv-vision 환경, NVIDIA 그래픽카드):
  python train_detector.py            학습 → 시험 → results/정확도.md, openimages/model.pt, openimages/preds/*.jpg
  python train_detector.py --eval     저장한 모델로 시험만 다시

모델: torchvision Faster R-CNN ResNet50-FPN v2 (코드 BSD-3, COCO로 미리 학습된 가중치에서 시작).
사진을 8:2로 나눠 학습에 쓰지 않은 시험 사진으로만 성능을 잽니다. 회전 정보가 있는 사진 4장은 뺍니다.
비교용으로 COCO 원래 모델('bottle' 클래스만 있고 캔은 없음)의 병 성능도 함께 잽니다.
"""
import json
import random
import sys
import time
from pathlib import Path

import torch
import torchvision
from PIL import Image, ImageDraw, ImageFont
from torchvision.models.detection import FasterRCNN_ResNet50_FPN_V2_Weights, fasterrcnn_resnet50_fpn_v2
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.ops import box_iou
from torchvision.transforms.functional import hflip, to_tensor

HERE = Path(__file__).parent
DATA = HERE / "openimages"
RESULTS = HERE / "results"
CLASSES = ["배경", "캔", "병"]
COCO_BOTTLE = 44  # COCO 클래스 번호 'bottle'
SEED = 20261101
EPOCHS = 24
SIZE = 800  # 사진 긴 변. 크면 그래픽카드 메모리가 넘쳐 매우 느려지고 PC 메모리까지 부족해짐
BATCH = 2
SCORE = 0.5  # 이 점수 이상인 상자만 '찾았다'로 셈
IOU = 0.5


def load():
    items = [p for p in json.loads((DATA / "labels.json").read_text(encoding="utf-8")) if p["rotation"] in ("", "0.0")]
    random.Random(SEED).shuffle(items)
    cut = int(len(items) * 0.8)
    return items[:cut], items[cut:]


def small(p):
    """긴 변 SIZE로 줄인 사진을 한 번만 만들어 두고 쓴다."""
    path = DATA / f"images_{SIZE}" / f"{p['id']}.jpg"
    if not path.exists():
        path.parent.mkdir(exist_ok=True)
        img = Image.open(DATA / "images" / f"{p['id']}.jpg").convert("RGB")
        img.thumbnail((SIZE, SIZE), Image.LANCZOS)
        img.save(path, quality=92)
    return Image.open(path).convert("RGB")


def sample(p, train):
    img = small(p)
    w, h = img.size
    boxes = torch.tensor([[b["xmin"] * w, b["ymin"] * h, b["xmax"] * w, b["ymax"] * h] for b in p["boxes"]])
    labels = torch.tensor([CLASSES.index(b["label"]) for b in p["boxes"]])
    x = to_tensor(img)
    if train and random.random() < 0.5:
        x = hflip(x)
        boxes = torch.stack([w - boxes[:, 2], boxes[:, 1], w - boxes[:, 0], boxes[:, 3]], 1)
    return img, x, {"boxes": boxes, "labels": labels}


def build(pretrained_only=False):
    model = fasterrcnn_resnet50_fpn_v2(weights=FasterRCNN_ResNet50_FPN_V2_Weights.COCO_V1, min_size=SIZE, max_size=SIZE)
    if not pretrained_only:
        model.roi_heads.box_predictor = FastRCNNPredictor(model.roi_heads.box_predictor.cls_score.in_features, len(CLASSES))
    return model


def train(model, items, dev):
    model.to(dev).train()
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.SGD(params, lr=0.01, momentum=0.9, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.MultiStepLR(opt, [16, 21], 0.1)
    scaler = torch.amp.GradScaler(dev.type, enabled=dev.type == "cuda")
    for ep in range(EPOCHS):
        random.shuffle(items)
        t, total = time.time(), 0.0
        for i in range(0, len(items), BATCH):
            batch = [sample(p, True) for p in items[i:i + BATCH]]
            xs = [b[1].to(dev) for b in batch]
            ys = [{k: v.to(dev) for k, v in b[2].items()} for b in batch]
            with torch.autocast(dev.type, enabled=dev.type == "cuda"):  # 반정밀도로 메모리 절약
                loss = sum(model(xs, ys).values())
            opt.zero_grad()
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            total += loss.item()
        sched.step()
        mem = torch.cuda.max_memory_allocated() / 2**30 if dev.type == "cuda" else 0
        print(f"  {ep + 1}/{EPOCHS}회 손실 {total / (len(items) / BATCH):.3f} ({time.time() - t:.0f}초, 그래픽 메모리 최대 {mem:.1f}GB)", flush=True)


@torch.no_grad()
def evaluate(model, items, dev, coco=False):
    """클래스별 찾은 비율(재현율)·맞힌 비율(정밀도), 사진별 개수 정답률을 잰다."""
    model.to(dev).eval()
    stat = {c: {"tp": 0, "fp": 0, "fn": 0} for c in CLASSES[1:]}
    per_image, secs = [], 0.0
    for p in items:
        img, x, tgt = sample(p, False)
        t = time.time()
        out = model([x.to(dev)])[0]
        secs += time.time() - t
        keep = out["scores"] >= SCORE
        boxes, labels, scores = out["boxes"][keep].cpu(), out["labels"][keep].cpu(), out["scores"][keep].cpu()
        if coco:  # COCO 모델은 병(44)만 보고 '병'으로 바꿔 셈
            m = labels == COCO_BOTTLE
            boxes, labels, scores = boxes[m], torch.full((int(m.sum()),), 2), scores[m]
        counts = {}
        for ci, c in enumerate(CLASSES[1:], 1):
            if coco and c == "캔":
                continue
            pb, gb = boxes[labels == ci], tgt["boxes"][tgt["labels"] == ci]
            matched = set()
            if len(pb) and len(gb):
                ious = box_iou(pb, gb)
                for j in scores[labels == ci].argsort(descending=True).tolist():
                    k = int(ious[j].argmax())
                    if ious[j, k] >= IOU and k not in matched:
                        matched.add(k)
            stat[c]["tp"] += len(matched)
            stat[c]["fp"] += len(pb) - len(matched)
            stat[c]["fn"] += len(gb) - len(matched)
            counts[c] = (len(pb), len(gb))
        per_image.append({"id": p["id"], "counts": counts, "boxes": boxes.tolist(), "labels": labels.tolist(),
                          "scores": scores.tolist()})
    return stat, per_image, secs / len(items)


def draw(per_image, out_dir):
    out_dir.mkdir(exist_ok=True)
    font = ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf", 22)
    colors = {1: (230, 120, 40), 2: (40, 140, 220)}
    for r in per_image:
        img = small({"id": r["id"]})
        g = ImageDraw.Draw(img)
        for b, l, s in zip(r["boxes"], r["labels"], r["scores"]):
            g.rectangle(b, outline=colors[l], width=4)
            g.text((b[0] + 4, b[1] + 2), f"{CLASSES[l]} {s:.2f}", font=font, fill=colors[l], stroke_width=3, stroke_fill="white")
        label = "  ".join(f"{c} {n}개" for c, (n, _) in r["counts"].items() if n)
        g.text((14, 12), label or "찾지 못함", font=font, fill="black", stroke_width=4, stroke_fill="white")
        img.save(out_dir / f"{r['id']}.jpg", quality=90)


def report(name, stat, per_image, sec, n_train, n_test, train_min, coco_stat):
    lines = [f"# 캔·병 찾기 모델 시험 결과 ({name})", "",
             f"- 사진: Open Images V7 (CC BY 2.0 표시, 출처 `ATTRIBUTION.md`) 학습 {n_train}장 / **처음 보는 시험 사진 {n_test}장**",
             f"- 모델: torchvision Faster R-CNN ResNet50-FPN v2, COCO 가중치에서 {EPOCHS}회 학습(사진 긴 변 {SIZE}px)"
             + (f" ({train_min:.1f}분, RTX 4070 Ti)" if train_min else ""),
             f"- 기준: 점수 {SCORE} 이상 상자, 정답 상자와 겹침(IoU) {IOU} 이상이면 맞음. 사진 한 장 처리 {sec * 1000:.0f}ms(그래픽카드)", "",
             "| 대상 | 정답 상자 | 찾은 비율(재현율) | 맞힌 비율(정밀도) |", "| --- | --- | --- | --- |"]
    for c, s in stat.items():
        n = s["tp"] + s["fn"]
        rec = s["tp"] / n if n else 0
        prec = s["tp"] / (s["tp"] + s["fp"]) if s["tp"] + s["fp"] else 0
        lines.append(f"| {c} | {n} | {rec:.0%} | {prec:.0%} |")
    for c in CLASSES[1:]:
        imgs = [r for r in per_image if c in r["counts"] and r["counts"][c][1] > 0]
        exact = sum(r["counts"][c][0] == r["counts"][c][1] for r in imgs)
        within1 = sum(abs(r["counts"][c][0] - r["counts"][c][1]) <= 1 for r in imgs)
        if imgs:
            lines.append(f"\n- {c} 개수: {c}이 있는 시험 사진 {len(imgs)}장 중 정확히 맞힘 {exact}장, ±1개 이내 {within1}장")
    if coco_stat:
        s = coco_stat["병"]
        n = s["tp"] + s["fn"]
        lines += ["", f"**비교 · 학습 전 COCO 모델:** 병 찾은 비율 {s['tp'] / n:.0%}, 맞힌 비율 "
                  f"{s['tp'] / max(s['tp'] + s['fp'], 1):.0%}. COCO에는 '캔' 분류가 없어 캔은 찾지 못합니다."]
    lines += ["", "공개 사진은 술병·화장품병·소스병 등 종류가 섞여 있고, 사진당 물건 수가 적습니다(대부분 2~3개). "
              "실제 고객 사진(같은 매대·같은 상품 반복)에서는 다시 재야 합니다."]
    (RESULTS / "정확도.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    torch.manual_seed(SEED)
    random.seed(SEED)
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tr, te = load()
    RESULTS.mkdir(exist_ok=True)
    print(f"학습 {len(tr)}장, 시험 {len(te)}장, 장치 {dev}")
    model = build()
    train_min = 0
    if "--eval" in sys.argv:
        model.load_state_dict(torch.load(DATA / "model.pt", map_location="cpu"))
    else:
        t = time.time()
        train(model, list(tr), dev)
        train_min = (time.time() - t) / 60
        torch.save(model.state_dict(), DATA / "model.pt")
    stat, per_image, sec = evaluate(model, te, dev)
    coco_stat, _, _ = evaluate(build(pretrained_only=True), te, dev, coco=True)
    (RESULTS / "시험사진_결과.json").write_text(json.dumps(per_image, ensure_ascii=False), encoding="utf-8")
    draw(per_image, DATA / "preds")
    report("시험 사진", stat, per_image, sec, len(tr), len(te), train_min, coco_stat)


if __name__ == "__main__":
    main()
