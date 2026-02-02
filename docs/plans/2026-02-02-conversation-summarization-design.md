# 대화 요약 기능 구현 계획

**날짜:** 2026-02-02
**브랜치:** feat/47
**이슈:** #47

## 목표

회의가 길어질수록 토큰 사용량이 급증하는 문제를 해결하기 위해, 오래된 대화를 요약으로 압축하고 최근 메시지만 유지하는 시스템 구현.

## 아키텍처 개요

### 핵심 컴포넌트

1. **State 확장**: `MeetingState`에 `summary` 필드 추가
2. **요약 노드**: 조건부로 대화 요약 생성 및 메시지 정리
3. **Workflow 통합**: 매 턴마다 요약 노드 실행
4. **Agent 수정**: 요약을 시스템 프롬프트에 포함

### 데이터 흐름

```
Agent 발언 → Summarize Node (조건 체크)
                    ↓
            메시지 10개 초과?
                    ↓
                   Yes → 요약 생성 + 메시지 삭제 (최근 5개만 유지)
                   No  → 아무것도 안 함
                    ↓
            Coordinator (다음 발언자 선택)
```

## 구현 태스크

### Phase 1: 기반 작업

**Task 1.1: State에 summary 필드 추가**
- 파일: `thetable/graph/state.py`
- 변경: `MeetingState` 클래스에 `summary: str = ""` 추가
- 검증: 기존 테스트 통과 확인

**Task 1.2: Settings에 요약 파라미터 추가**
- 파일: `thetable/config/settings.py`
- 추가 파라미터:
  - `max_messages_before_summary: int = 10`
  - `keep_recent_messages: int = 5`
  - `summary_max_tokens: int = 200`
- 검증: Settings 로드 확인

### Phase 2: 요약 노드 구현

**Task 2.1: summarization.py 생성**
- 파일: `thetable/graph/summarization.py` (신규)
- 구현: `summarize_conversation_node` 함수
- 기능:
  1. 메시지 개수 확인 (임계값: 10개)
  2. 요약 생성 (기존 요약 있으면 확장)
  3. 오래된 메시지 삭제 (최근 5개만 유지)
  4. 에러 처리 (요약 실패 시 기존 요약 유지)
- 검증: 단위 테스트 작성 및 실행

**Task 2.2: 단위 테스트 작성**
- 파일: `tests/test_summarization.py` (신규)
- 테스트 케이스:
  1. 메시지 적을 때 요약 안 함
  2. 메시지 많을 때 요약 생성
  3. 기존 요약 확장
- 검증: `pytest tests/test_summarization.py -v`

### Phase 3: Agent 통합

**Task 3.1: Agent에서 요약 활용**
- 파일: `thetable/graph/agent_factory.py`
- 변경:
  1. `state.get("summary", "")` 가져오기
  2. 요약이 있으면 시스템 프롬프트에 포함
  3. 모든 메시지 포맷팅 (이미 요약 노드가 정리함)
- 검증: Agent 응답에 요약 컨텍스트 반영 확인

### Phase 4: Workflow 통합

**Task 4.1: Workflow에 요약 노드 추가**
- 파일: `thetable/graph/workflow.py`
- 변경:
  1. `summarize_conversation_node` import
  2. `workflow.add_node("summarize", summarize_conversation_node)` 추가
  3. 각 에이전트 → 요약 노드 → coordinator edge 추가
- 검증: Workflow 그래프 정상 생성 확인

**Task 4.2: 라우팅 로직 추가**
- 파일: `thetable/graph/workflow.py`
- 변경:
  1. `route_after_agent` 함수: 에이전트 → summarize
  2. `route_after_summarize` 함수: summarize → coordinator
  3. Conditional edges 연결
- 검증: 전체 워크플로우 실행 테스트

### Phase 5: 통합 테스트 및 검증

**Task 5.1: 통합 테스트 작성**
- 파일: `tests/test_workflow_with_summary.py` (신규)
- 테스트:
  1. 전체 워크플로우에서 요약 동작 확인
  2. 10개 메시지 후 요약 생성 검증
  3. 메시지 정리 확인 (5개만 남음)
- 검증: `pytest tests/test_workflow_with_summary.py -v`

**Task 5.2: 실제 회의 시뮬레이션**
- 실행: CLI로 실제 회의 진행 (15턴 이상)
- 확인:
  1. 10턴 이후 요약 생성 여부
  2. 메시지 개수 유지 (5개)
  3. Agent 응답 품질 유지
  4. 토큰 사용량 비교
- 검증: 로그 및 상태 확인

**Task 5.3: 기존 테스트 확인**
- 실행: `pytest tests/ -v`
- 목표: 모든 기존 테스트 통과
- 검증: CI/CD 통과 확인

## 성공 기준

### 기능 검증
- ✅ 메시지 10개 이하: 요약 미생성
- ✅ 메시지 10개 초과: 요약 생성 및 메시지 정리
- ✅ 기존 요약 있을 때: 확장 요약
- ✅ Agent가 요약을 프롬프트에서 활용
- ✅ 회의 전체 흐름 정상 동작

### 성능 검증
- ✅ 토큰 사용량 50% 이상 감소 (20턴 이상 회의 기준)
- ✅ 응답 시간 변화 최소 (요약 생성 오버헤드)

### 품질 검증
- ✅ 요약이 핵심 내용 포함
- ✅ Agent 응답 품질 유지
- ✅ 회의 맥락 유지

## 예상 토큰 절감

### Before (요약 없음)
- 20턴 회의: ~50,000 토큰 (전체 히스토리)
- 50턴 회의: ~125,000 토큰

### After (요약 적용)
- 20턴 회의: ~2,500 토큰/호출 (요약 200 + 메시지 5개)
- 50턴 회의: ~2,500 토큰/호출 (일정하게 유지)

**절감률: ~95%**

## 위험 요소 및 대응

### 위험 1: 요약 품질 저하
- **완화**: 요약 프롬프트에 구체적 지침 포함
- **대응**: 실제 테스트 후 프롬프트 개선

### 위험 2: 중요 정보 손실
- **완화**: 최근 5개 메시지는 항상 유지
- **대응**: `keep_recent_messages` 파라미터 조정 가능

### 위험 3: 요약 생성 실패
- **완화**: try-except로 에러 처리
- **대응**: 실패 시 기존 요약 유지 (시스템 안정성)

## 참고 자료

- [LangGraph Memory Management](https://langchain-ai.github.io/langgraph/how-tos/memory/)
- [LangChain SummarizationNode](https://docs.langchain.com/oss/python/langgraph/add-memory)
- GitHub Issue: #47
