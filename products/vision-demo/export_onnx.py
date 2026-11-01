"""학습한 캔·병 모델(openimages/model.pt)을 납품용 ONNX 파일로 바꾼다. (서비스 C)

사용법 (.venv-vision 환경): python export_onnx.py  → package/model.onnx
ONNX로 바꾸면 고객 PC에 torch(수 GB) 없이 onnxruntime(수십 MB)만으로 그래픽카드 없이도 돌아갑니다.
바꾼 뒤 시험 사진 몇 장을 torch와 onnxruntime으로 각각 돌려 결과가 같은지 확인합니다.
"""
import json
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch

from train_detector import DATA, SCORE, build, load, small
from torchvision.transforms.functional import to_tensor

HERE = Path(__file__).parent
OUT = HERE / "package" / "model.onnx"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    model = build()
    model.load_state_dict(torch.load(DATA / "model.pt", map_location="cpu"))
    model.eval()
    _, te = load()
    x = to_tensor(small(te[0]))
    torch.onnx.export(model, ([x],), OUT, opset_version=17, dynamo=False,
                      input_names=["image"], output_names=["boxes", "labels", "scores"],
                      dynamic_axes={"image": {1: "h", 2: "w"}, "boxes": {0: "n"}, "labels": {0: "n"}, "scores": {0: "n"}})
    print(f"저장: {OUT} ({OUT.stat().st_size / 2**20:.0f}MB)")

    sess = ort.InferenceSession(str(OUT), providers=["CPUExecutionProvider"])
    worst = 0.0
    for p in te[:5]:
        x = to_tensor(small(p))
        with torch.no_grad():
            ref = model([x])[0]
        boxes, labels, scores = sess.run(None, {"image": x.numpy()})
        a, b = ref["scores"].numpy() >= SCORE, scores >= SCORE
        same = a.sum() == b.sum() and (ref["labels"].numpy()[a] == labels[b]).all()
        diff = float(np.abs(ref["boxes"].numpy()[a] - boxes[b]).max()) if same and a.any() else 0.0
        worst = max(worst, diff)
        print(f"  {p['id']}: torch {int(a.sum())}개 / onnx {int(b.sum())}개, 같음={bool(same)}, 상자 차이 최대 {diff:.2f}px")
    print(json.dumps({"상자 차이 최대(px)": round(worst, 2)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
