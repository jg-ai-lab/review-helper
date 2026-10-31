# 샘플 공개 배포

GitHub Pages 배포 워크플로는 `main`에 푸시할 때 실행됩니다.
저장소 Settings → Pages → Build and deployment → Source를 GitHub Actions로 설정해야 합니다.
비공개 저장소는 요금제에 따라 Pages를 사용할 수 없을 수 있습니다. 저장소 공개 여부를 임의로 변경하지 않습니다.

배포 성공 후 기본 주소가 사용된다면:

- 앱: https://jg-ai-lab.github.io/review-helper/
- 가게 샘플: https://jg-ai-lab.github.io/review-helper/samples/cafe.html
- 의뢰서: https://jg-ai-lab.github.io/review-helper/samples/request.html

위 주소는 예상 주소이며, Actions 배포 성공과 HTTP 응답 확인 전에는 공개 완료로 간주하지 않습니다. 커스텀 도메인이 설정돼 있으면 실제 주소가 달라집니다.

## 현재 확인 상태

GitHub API와 공개 사이트 확인 요청이 환경 프록시에서 거부되어 배포 성공 여부를 확인하지 못했습니다. 환경 설정에 저장된 `api.github.com`, `jg-ai-lab.github.io` 도메인 추가 초안을 검토·저장하고 환경에 적용해야 합니다. 초안 저장만으로 현재 네트워크 정책이 바뀌지는 않습니다.

적용 후에는 GitHub API로 Pages 설정을 조회하고, 필요하면 `build_type: workflow`로 활성화한 다음 배포 실행 결과를 확인합니다. API 인증·권한 오류가 별도로 발생하면 그 결과에 따라 진단합니다. 현재 프록시 거부만으로 GitHub 권한이 없다고 단정하지 않습니다.

직접 설정할 경우 [Pages 설정](https://github.com/jg-ai-lab/review-helper/settings/pages)에서 Source를 GitHub Actions로 선택하고 [배포 실행 목록](https://github.com/jg-ai-lab/review-helper/actions/workflows/pages.yml)에서 실행합니다. 성공한 실행이 표시된 뒤 실제 공개 URL로 접속해야 완료입니다.

`public` 폴더에 명시적으로 복사한 HTML만 배포합니다. 고객 자료나 의뢰서 파일을 저장소에 커밋하지 마세요.

의뢰서는 파일 다운로드 방식이며 자동 전송·접수·결제는 제공하지 않습니다. 고객에게 공유하기 전에 실제 회신 채널을 합의하세요.
