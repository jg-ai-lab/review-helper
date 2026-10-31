"""확인 질문 7개로 데모 답변을 점검합니다. 사용법: python check.py"""
import json
import sys
import time

from app import INDEX, answer

CASES = [
    ("배우자 출산 휴가는 며칠이에요?", ["10일"], "04_경조사.md"),
    ("서울 출장 숙박비 한도는?", ["10만"], "05_출장비.md"),
    ("비밀번호를 몇 번 틀리면 잠겨요?", ["5번"], "09_비밀번호.md"),
    ("교육비 지원받고 6개월 만에 퇴사하면?", ["50%"], "12_교육비지원.md"),
    ("회의실은 한 번에 몇 시간까지 예약돼요?", ["2시간"], "16_회의실.md"),
    ("구입 8개월 된 제품 고장 A/S는 무료인가요?", ["무상"], "20_AS접수.md"),
    ("회사 주차 지원금은 얼마예요?", ["찾지 못했"], None),
]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    items = json.loads(INDEX.read_text(encoding="utf-8"))
    passed = 0
    for q, keys, doc in CASES:
        t = time.time()
        r = answer(q, items)
        docs = [s["doc"] for s in r["sources"]]
        ok_text = all(k in r["answer"] for k in keys)
        ok_doc = doc in docs if doc else True
        passed += ok_text and ok_doc
        print(f"{'통과' if ok_text and ok_doc else '실패'} {time.time() - t:4.1f}초 | {q}\n   → {r['answer']}\n   근거: {docs}")
    print(f"\n{passed}/{len(CASES)} 통과")


if __name__ == "__main__":
    main()
