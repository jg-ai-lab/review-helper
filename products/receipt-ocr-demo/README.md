# OCR 데모 · 거래명세서·영수증 사진을 엑셀로 (서비스 E)

서비스 E(`MARKETPLACE.md`) 홍보용 데모입니다. 문서는 모두 `make_docs.py`로 만든 가상 문서이고, 사진은 직접 찍습니다.

## 문서 만들기

```powershell
.venv\Scripts\python.exe products\receipt-ocr-demo\make_docs.py
```

`docs\`에 아래 파일이 생깁니다(용량 때문에 git에는 올리지 않음, 위 명령으로 다시 만듦).

| 파일 | 내용 |
| --- | --- |
| `인쇄용_20장.pdf` | 인쇄할 문서. E01~E12 거래명세서, E13~E20 영수증 |
| `E01.png`~`E20.png` | 같은 문서의 원본 그림 (사진 대신 넣어 보는 '쉬운 시험'용) |
| `정답.xlsx` | 문서 시트(날짜·거래처·사업자번호·공급가액·세액·합계)와 품목 시트(품목·규격·수량·단가·금액) |
| `정답.json` | 같은 정답, 자동 채점용 |

현재 값(`SEED = 20261101`): 문서 20장, 품목 줄 61개, 합계 1,982,530원.

## 인쇄와 촬영

1. `인쇄용_20장.pdf`를 A4 흑백, **실제 크기(100%)**로 인쇄합니다. 영수증 페이지는 회색 테두리를 따라 잘라도 되고 그대로 둬도 됩니다.
2. 휴대폰으로 한 장에 문서 하나씩 찍습니다. 오른쪽 위 문서번호(E01 등)가 사진에 들어가게 합니다.
3. 실제 고객 사진처럼 일부러 조건을 섞습니다.

| 문서 | 찍는 방법 |
| --- | --- |
| E01~E05 | 책상 위, 정면, 밝은 곳 (쉬움) |
| E06~E10 | 비스듬히(15~30도 기울게) |
| E11~E14 | 그림자 지게, 형광등 아래 |
| E15~E18 | 종이를 한 번 접었다 펴거나 구겨서 |
| E19~E20 | 조금 멀리서, 배경(키보드·컵 등)이 같이 나오게 |

4. 사진은 `photos\`에 넣습니다. 파일 이름은 그대로 둬도 됩니다(문서번호는 사진에서 읽음). 카톡으로 옮기면 화질이 떨어지니 USB·케이블이나 원본 전송을 씁니다.
5. 사진에 다른 사람 얼굴·개인 서류가 나오지 않게 합니다.

## 합성 사진 (2026-11-01, 실제 촬영 전 대신 씀)

```powershell
.venv-ocr\Scripts\python.exe products\receipt-ocr-demo\make_photos.py
```

`photos_synth\E01.jpg~E20.jpg`를 만듭니다. 문서 그림을 책상 위에 놓고 위 표와 같은 조건(정면·기울기·그림자·구김·멀리서)으로 찍은 것처럼 바꾼 합성 사진입니다. 홍보물에는 "합성 사진으로 시험"이라고 밝히고, 실제 촬영 사진 결과가 생기면 그것으로 바꿉니다.

## 사진 → 엑셀 변환과 채점

OCR은 PaddleOCR(Apache-2.0)을 이 PC에서 돌리며 사진을 인터넷으로 보내지 않습니다. D 납품 환경과 섞이지 않게 별도 가상환경을 씁니다.

```powershell
.venv\Scripts\python.exe -m venv .venv-ocr
.venv-ocr\Scripts\python.exe -m pip install paddlepaddle paddleocr openpyxl
.venv-ocr\Scripts\python.exe products\receipt-ocr-demo\ocr_to_excel.py photos_synth
```

- 결과: `results\photos_synth_변환결과.xlsx`(문서·품목·확인 필요·정확도 시트), `results\photos_synth_정확도.md`
- `--reuse`: OCR을 다시 돌리지 않고 저장해 둔 인식 결과(`results\*_ocr.json`)로 정리·채점만 다시 함
- `--fast`: 가벼운 모델(CPU에서 장당 6~10초, 표준 모델은 54초인데 더 정확하지도 않아 기본으로 권장)
- `--raw`: 보정 없이 채점. 기본 보정은 ① 수량을 못 읽으면 금액÷단가로 채움 ② `docs\품목목록.txt`(고객 단가표 역할)로 품목 이름을 자모 단위로 아주 비슷한 것으로 고침. 고친 칸은 모두 '확인 필요'에 남김
- **처음 보는 문서로 다시 재기:** 읽기 규칙을 고친 뒤에는 `make_docs.py 2` → `make_photos.py 2` → `ocr_to_excel.py photos_synth2 --fast`처럼 새 세트(다른 SEED)로 잽니다. 세트1은 규칙을 맞춘 문서라 점수가 부풀려집니다.
- 결과 요약(2026-11-01): 세트2 합성 사진 칸 95.9%, 20장 중 19장 모든 칸 정답, 장당 8초. 표는 `MARKETPLACE.md` 서비스 E
- Windows CPU에서 paddlepaddle 3.3은 oneDNN 오류가 나서 `enable_mkldnn=False`로 끕니다.
- '확인 필요' 기준: 수량×단가 ≠ 금액, 품목 금액 합 ≠ 문서 합계, 공급가액+세액 ≠ 합계, 인식 점수 0.85 미만, 빈 칸
