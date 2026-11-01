# 비전 AI 데모 · 매대 상품 개수 세기

서비스 C(`MARKETPLACE.md`) 홍보용 데모입니다. 직접 찍은 사진만 씁니다.

## 사진 넣는 곳

`photos/` 폴더에 휴대폰 사진(jpg)을 그대로 넣습니다. 사진 원본은 용량 때문에 git에 올리지 않습니다.

## 촬영 가이드

- 대상: 음료 캔·과자 등 3~4종 (상표가 크게 보여도 되지만 데모 이미지에 쓸 때는 제품 홍보처럼 보이지 않게 함)
- 150~200장, 한 장에 2~10개 정도
- 바꿀 것: 각도(정면·위·비스듬히), 조명(낮·밤·형광등), 개수, 배치(겹침 조금 포함), 배경(선반·책상)
- 사람 얼굴·개인 물건(편지, 화면 속 개인정보)이 찍히지 않게

## 촬영 배분 (예: 4종 × 약 45장 = 180장)

| 장수 | 조건 |
| --- | --- |
| 40 | 선반 정면, 밝은 곳, 2~5개 |
| 40 | 위에서·비스듬히, 4~8개 |
| 40 | 저녁 실내 조명, 그림자 있음 |
| 30 | 일부 겹치거나 가려짐, 6~10개 |
| 30 | 다른 배경(책상·바닥), 섞어서 놓기 |

- 한 번에 몰아 찍기보다 위치·개수를 바꿀 때마다 2~3장씩 찍습니다. 거의 같은 사진이 많으면 성능이 실제보다 좋게 나옵니다.
- 사진은 USB·케이블로 원본을 옮깁니다(카톡은 화질 저하).
- 상품 종류 이름을 정해 알려 주세요(예: 콜라캔, 사이다캔, 감자칩, 초코과자). 자동 라벨링 문구로 씁니다.

## Open Images로 학습·시험 (2026-11-01)

```powershell
.venv\Scripts\python.exe products\vision-demo\fetch_openimages.py        # 캔·병 사진 213장 + ATTRIBUTION.md
.venv\Scripts\python.exe -m venv .venv-vision
.venv-vision\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
.venv-vision\Scripts\python.exe products\vision-demo\train_detector.py   # 학습 → results\정확도.md, openimages\preds\
```

- 학습 전에 `ollama stop qwen3:8b`로 그래픽 메모리를 비웁니다. 사진 긴 변 800px·2장 묶음·반정밀도로 그래픽 메모리 약 1.7GB, 24회 4.5분(RTX 4070 Ti).
- 결과는 [`results/정확도.md`](results/정확도.md). Open Images 라벨이 모든 물건을 표시하지 않아 정밀도는 실제보다 낮게 나옵니다.
- 홍보 이미지: `marketing/kmong/render_vision.py` (사진마다 작성자·CC BY 2.0 표기)

## 납품용 프로그램 `물건세기.exe` (2026-11-01)

```powershell
.venv-vision\Scripts\python.exe -m pip install onnx onnxruntime
.venv-vision\Scripts\python.exe products\vision-demo\export_onnx.py       # openimages\model.pt → package\model.onnx (165MB)
.venv\Scripts\python.exe -m pip install onnxruntime numpy
powershell -ExecutionPolicy Bypass -File products\vision-demo\package\build.ps1   # dist\물건세기\ + 물건세기.zip (193MB)
```

- 고객은 `사진넣기\`에 사진을 넣고 exe를 더블클릭 → `결과\날짜_시간\개수.xlsx`와 상자를 그린 사진. 인터넷·그래픽카드 없이 CPU로 장당 약 1초.
- torch 대신 ONNX(onnxruntime)로 바꿔 exe 40MB + 모델 165MB. 변환 전후 시험 사진 5장의 상자가 같음(차이 0px).
- 점수 0.3~0.5 상자는 회색 '?'로 표시하고 엑셀 '확인 필요' 칸에 수를 적음. 휴대폰 사진 회전(EXIF)을 바로잡고, 열 수 없는 파일은 건너뛰고 표에 남김.
- 종류가 달라도 거의 같은 자리(IoU 0.6 초과)의 상자는 하나만 남김(병 하나를 캔·병으로 두 번 세는 문제). 시험 사진 42장 비교: 캔 개수 정확 2/8→3/8·±1 이내 5/8→6/8, 병 정확 16/34→15/34·±1 이내 27/34→26/34. 사진 수가 적어 차이는 크지 않음.
- 고객 상품으로 다시 학습하면 `train_detector.py`의 `CLASSES`와 `package\config.json`의 `이름`을 함께 바꾼 뒤 위 순서로 다시 만듭니다.
- `model.onnx`, `dist\`는 용량 때문에 git에 올리지 않습니다.
