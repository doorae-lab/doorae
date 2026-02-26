# 일일 스탠드업 가이드

## 목적
- 팀원 간 진행 상황 공유
- 장애 요인 조기 발견
- 협업 효율성 향상

## 진행 방식
- **시간**: 매일 오전 10시
- **장소**: GitHub Discussions "일일 스탠드업" 카테고리
- **형식**: 각 담당자 3분 내외 발언

## 발언 내용
1. **어제 한 일**: 전날 완료한 작업
2. **오늘 할 일**: 당일 계획 작업  
3. **장애 요인**: 진행 중인 문제 또는 도움 필요 사항

## 참여자
- PM (project_manager)
- TechLead
- 개발자 A
- 개발자 B
- Host

## 현재 진행 중인 마일스톤
1. **데이터 백업 완료 (D+2)** - #175
2. **핵심 안정성 개선 (D+5)** - #176
3. **기능 개선 완료 (D+10)** - #177
4. **통합 테스트 시작 (D+15)** - #178

## 브랜치 현황
- `feat/backup-script` - 개발자 B (우선 개발)
- `feat/157-1-memorysaver-implementation` - TechLead
- `feat/157-2-threadid-session-management` - TechLead
- `feat/157-3-checkpointer-testing` - TechLead
- `feat/156-1-exception-handling` - 개발자 A
- `feat/156-2-agent-skip-mechanism` - 개발자 A
- `feat/156-3-timeout-implementation` - 개발자 A
- `fix/166-missing-tool-message` - 개발자 B

## 개발 순서
1. 데이터 백업 스크립트 (개발자 B)
2. #157-1 MemorySaver 구현 (TechLead) + #156-1 예외 처리 (개발자 A) 병렬
3. 나머지 서브 태스크 순차적 진행