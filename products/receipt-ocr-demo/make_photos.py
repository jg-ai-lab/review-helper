"""docs/의 가상 문서 그림을 휴대폰 사진처럼 바꾼 합성 사진 20장을 만든다.

사용법: python make_photos.py [시험세트번호]   (OCR용 가상환경 .venv-ocr 또는 numpy·opencv가 있는 환경)
photos_synth/E01.jpg~E20.jpg를 만듭니다. 실제 촬영 사진이 아니라 합성이라는 점을 홍보물에 밝힙니다.
README의 촬영 조건 표와 같은 순서로 조건을 섞습니다.
"""
import random
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).parent
SET = next((int(a) for a in sys.argv[1:] if a.isdigit()), 0)  # 시험 세트 번호: 2를 주면 docs2/·다른 SEED로 새 세트
SRC = HERE / f"docs{SET or ''}"
OUT = HERE / f"photos_synth{SET or ''}"
SEED = 20261101 + SET
W, H = 1536, 2048  # 3:4 세로 사진

CONDITIONS = {  # 문서 번호 → 조건 (README 촬영 표와 같음)
    **{i: "정면" for i in range(1, 6)}, **{i: "기울기" for i in range(6, 11)},
    **{i: "그림자" for i in range(11, 15)}, **{i: "구김" for i in range(15, 19)},
    **{i: "멀리서" for i in range(19, 21)},
}


def imread(path):
    return cv2.imdecode(np.fromfile(str(path), np.uint8), cv2.IMREAD_COLOR)


def desk(rng, clutter):
    base = np.array([rng.randint(70, 110), rng.randint(100, 140), rng.randint(140, 190)], np.float32)  # BGR 나무색
    img = np.ones((H, W, 3), np.float32) * base
    grain = cv2.GaussianBlur(np.random.default_rng(rng.randint(0, 9999)).normal(0, 18, (H, W)).astype(np.float32), (0, 0), sigmaX=40, sigmaY=3)
    img += grain[..., None]
    if clutter:  # 키보드·컵 같은 물건
        x = rng.randint(0, W // 3)
        cv2.rectangle(img, (x, H - 420), (x + 900, H - 120), (40, 40, 45), -1)
        for k in range(12):
            for r in range(3):
                cv2.rectangle(img, (x + 20 + k * 72, H - 400 + r * 90), (x + 80 + k * 72, H - 330 + r * 90), (70, 70, 75), -1)
        cv2.circle(img, (W - 230, 260), 150, (230, 235, 240), -1)
        cv2.circle(img, (W - 230, 260), 110, (60, 90, 120), -1)
    return img


def crumple(rng, doc):
    h, w = doc.shape[:2]
    g = np.random.default_rng(rng.randint(0, 9999))
    dx = cv2.GaussianBlur(g.normal(0, 1, (h, w)).astype(np.float32), (0, 0), 45) * 300
    dy = cv2.GaussianBlur(g.normal(0, 1, (h, w)).astype(np.float32), (0, 0), 45) * 300
    xs, ys = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    out = cv2.remap(doc, xs + dx, ys + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
    shade = 1 + cv2.GaussianBlur(dx - dy, (0, 0), 25) / 250  # 구김 명암
    fold = h * rng.uniform(0.35, 0.65)  # 접힌 선
    shade *= 1 - 0.18 * np.exp(-((ys - fold) / 6) ** 2)
    return np.clip(out * shade[..., None], 0, 255)


def shadow(rng, img):
    mask = np.zeros((H, W), np.float32)
    x0 = rng.randint(W // 3, W // 2)
    pts = np.array([[x0, 0], [W, 0], [W, H], [x0 + rng.randint(-300, 300), H]], np.int32)
    cv2.fillPoly(mask, [pts], 1.0)
    mask = cv2.GaussianBlur(mask, (0, 0), 60)
    light = cv2.GaussianBlur(np.random.default_rng(1).normal(0, 1, (H, W)).astype(np.float32), (0, 0), 300)
    tint = np.array([0.9, 0.97, 1.0], np.float32)  # 형광등·실내등 색
    return img * (1 - 0.5 * mask[..., None]) * (1 + 0.1 * light[..., None]) * tint


def photo(rng, doc, cond):
    if cond == "구김":
        doc = crumple(rng, doc)
    doc = doc.astype(np.float32)
    h, w = doc.shape[:2]
    scale = (0.52 if cond == "멀리서" else rng.uniform(0.82, 0.9)) * min(W / w, H / h)
    dw, dh = w * scale, h * scale
    cx, cy = W / 2 + rng.uniform(-30, 30), H / 2 + rng.uniform(-30, 30)
    if cond == "멀리서":
        cx, cy = W * 0.45, H * 0.42
    angle = np.deg2rad({"정면": rng.uniform(-2, 2), "기울기": rng.uniform(-9, 9)}.get(cond, rng.uniform(-4, 4)))
    jitter = {"정면": 0.01, "기울기": 0.08}.get(cond, 0.03)
    corners = []
    for sx, sy in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
        x, y = sx * dw / 2, sy * dh / 2
        if cond == "기울기" and sy == -1:  # 위쪽이 멀어 보이는 원근
            x *= 1 - rng.uniform(0.06, 0.14)
        x += rng.uniform(-jitter, jitter) * dw
        y += rng.uniform(-jitter, jitter) * dh
        corners.append([cx + x * np.cos(angle) - y * np.sin(angle), cy + x * np.sin(angle) + y * np.cos(angle)])
    M = cv2.getPerspectiveTransform(np.float32([[0, 0], [w, 0], [w, h], [0, h]]), np.float32(corners))
    paper = cv2.warpPerspective(doc, M, (W, H), flags=cv2.INTER_AREA)
    mask = cv2.warpPerspective(np.ones((h, w), np.float32), M, (W, H))[..., None]
    img = desk(rng, cond == "멀리서") * (1 - mask) + paper * mask
    if cond == "그림자":
        img = shadow(rng, img)
    else:
        img *= 1 + 0.08 * np.linspace(-1, 1, W, dtype=np.float32)[None, :, None] * rng.choice([-1, 1])  # 조명 기울기
    img = img * rng.uniform(0.85, 1.0) + rng.uniform(-10, 10)
    img = cv2.GaussianBlur(img, (0, 0), rng.uniform(0.6, 1.3))
    img += np.random.default_rng(rng.randint(0, 9999)).normal(0, 4, img.shape)
    return np.clip(img, 0, 255).astype(np.uint8)


def main():
    rng = random.Random(SEED)
    OUT.mkdir(exist_ok=True)
    for n, cond in CONDITIONS.items():
        doc = imread(SRC / f"E{n:02d}.png")
        img = photo(rng, doc, cond)
        ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, rng.randint(72, 88)])
        buf.tofile(str(OUT / f"E{n:02d}.jpg"))
        print(f"E{n:02d} {cond}")


if __name__ == "__main__":
    main()
