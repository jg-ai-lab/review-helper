# 샘플 공개 배포

GitHub Pages 배포 워크플로는 `main`에 푸시할 때 실행됩니다.
저장소 Settings → Pages → Build and deployment → Source를 GitHub Actions로 설정해야 합니다.
비공개 저장소는 요금제에 따라 Pages를 사용할 수 없을 수 있습니다. 저장소 공개 여부를 임의로 변경하지 않습니다.

배포 성공 후 기본 주소가 사용된다면:

- 앱: https://jg-ai-lab.github.io/review-helper/
- 가게 샘플: https://jg-ai-lab.github.io/review-helper/samples/cafe.html
- 의뢰서: https://jg-ai-lab.github.io/review-helper/samples/request.html
- 엑셀 샘플: https://jg-ai-lab.github.io/review-helper/samples/excel.html

위 주소는 예상 주소이며, Actions 배포 성공과 HTTP 응답 확인 전에는 공개 완료로 간주하지 않습니다. 커스텀 도메인이 설정돼 있으면 실제 주소가 달라집니다.

## 현재 확인 상태 · 2026년 11월 1일

Pages를 GitHub Actions 방식으로 활성화한 뒤 커밋 `50dbf81` 배포가 성공했습니다. 위 주소 3개와 엑셀 샘플(`samples/excel.html`, `samples/excel/after.xlsx`)이 모두 HTTP 200으로 응답합니다. 그 전 10월 31일 실행 2건은 Pages가 꺼져 있어 `configure-pages` 단계에서 실패했습니다.

직접 설정할 경우 [Pages 설정](https://github.com/jg-ai-lab/review-helper/settings/pages)에서 Source를 GitHub Actions로 선택하고 [배포 실행 목록](https://github.com/jg-ai-lab/review-helper/actions/workflows/pages.yml)에서 실행합니다. 성공한 실행이 표시된 뒤 실제 공개 URL로 접속해야 완료입니다.

`public` 폴더에 명시적으로 복사한 HTML만 배포합니다. 고객 자료나 의뢰서 파일을 저장소에 커밋하지 마세요.

의뢰서는 파일 다운로드 방식이며 자동 전송·접수·결제는 제공하지 않습니다. 고객에게 공유하기 전에 실제 회신 채널을 합의하세요.
