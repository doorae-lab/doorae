---
name: pr
description: 현재 브랜치의 변경사항을 commit, push하고 PR을 생성합니다.
---

# PR Workflow

1. `uv run pytest`로 테스트 실행 — 실패 시 중단
2. 변경된 파일을 `git add`로 스테이징
3. conventional commit 메시지로 커밋
4. 현재 브랜치를 origin에 push
5. `gh pr create`로 PR 생성
   - body에 관련 이슈가 있으면 각각 별도 줄에 `Closes #N` 포함
6. PR URL 출력

NEVER merge directly to main.
