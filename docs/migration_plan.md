# langgraph-supervisor 마이그레이션 계획

## 완료 현황

### Phase 1: 기반 구축 ✅ (완료)

| 작업 | 상태 | 파일 |
|------|------|------|
| langgraph-supervisor 의존성 추가 | ✅ | pyproject.toml |
| AgentProfile 스키마 확장 | ✅ | thetable/core/profile.py |
| agent_profiles.yaml 계층 구조 추가 | ✅ | config/agent_profiles.yaml |
| MeetingState MessagesState 상속 | ✅ | thetable/graph/state.py |
| 계층적 에이전트 팩토리 구현 | ✅ | thetable/graph/agent_factory.py |
| 워크플로우 구성 | ✅ | thetable/graph/workflow.py |
| 비교 분석 문서 작성 | ✅ | docs/langgraph_supervisor_analysis.md |
| 테스트 업데이트 | ✅ | tests/ |

---

## Phase 2: 점진적 전환 (다음 단계)

### 2.1 통합 테스트 작성
```bash
# 새 워크플로우 통합 테스트
tests/integration/test_langgraph_supervisor_workflow.py
```

**테스트 항목:**
- [ ] 계층적 에이전트 빌드 (TechLead → Backend/Frontend/DevOps)
- [ ] Phase 전환 (opening → status_check → issue_resolution → closing)
- [ ] 핸드오프 도구 자동 생성 확인
- [ ] speaker_counts 추적
- [ ] MessagesState 호환성

### 2.2 Main 엔트리포인트 생성
```python
# thetable/main.py
from thetable.graph.workflow import create_meeting_workflow

def main():
    workflow = create_meeting_workflow()
    
    # 초기 상태
    initial_state = {
        "messages": [],
        "current_phase": "opening",
        "agents": [
            {"name": "PM", "role": "project_manager", "profile_key": "PM"},
            {"name": "TechLead", "role": "tech_lead", "profile_key": "TechLead"},
        ]
    }
    
    # 실행
    result = workflow.invoke(initial_state)
    
    for msg in result["messages"]:
        print(f"{msg.name}: {msg.content}")

if __name__ == "__main__":
    main()
```

### 2.3 기존 코드와 병행 운영
- 기존 워크플로우 유지 (호환성 보장)
- 새 워크플로우 별도 실행 (검증)
- 기능 비교 및 성능 측정

---

## Phase 3: 정리 (최종)

### 3.1 레거시 코드 정리

#### 삭제 대상
```bash
# PhaseController는 Host 프롬프트로 대체됨
thetable/graph/phase_controller.py
tests/graph/test_phase_controller.py
```

#### 리팩토링 대상
```bash
# SupervisorAgent → create_supervisor 전환
thetable/agents/supervisor.py
tests/agents/test_supervisor.py

# 기존 노드 팩토리 → langgraph-supervisor 통합
thetable/graph/nodes.py
tests/graph/test_nodes.py
```

### 3.2 문서 업데이트
- [ ] README.md 아키텍처 다이어그램 업데이트
- [ ] API 문서 (계층적 에이전트 구조)
- [ ] 사용 가이드 (YAML 설정 방법)

### 3.3 성능 최적화
- [ ] 에이전트 캐싱 전략 재평가
- [ ] 메모리 사용량 프로파일링
- [ ] 응답 시간 벤치마킹

---

## 검증 체크리스트

### 기능 검증
- [ ] ✅ AgentProfile이 계층 구조를 올바르게 로드하는가?
- [ ] ✅ MeetingState가 MessagesState를 상속하는가?
- [ ] ⏳ build_agent_graph가 재귀적으로 에이전트를 빌드하는가?
- [ ] ⏳ Host가 Phase 전환을 올바르게 판단하는가?
- [ ] ⏳ 핸드오프 도구가 자동 생성되는가?
- [ ] ⏳ TechLead → Backend/Frontend/DevOps 위임이 동작하는가?

### 품질 검증
```bash
# 단위 테스트
uv run pytest tests/ -v

# 타입 체크
uv run mypy thetable/

# 린트
uv run ruff check thetable/

# 커버리지
uv run pytest --cov=thetable tests/
```

### 성능 검증
- [ ] 기존 대비 응답 시간 비교
- [ ] 메모리 사용량 측정
- [ ] 계층 깊이별 성능 영향 분석

---

## 롤백 계획

### 문제 발생 시
1. 기존 구현으로 롤백 (git revert)
2. 새 구현 브랜치로 격리 (feature/langgraph-supervisor)
3. 문제 원인 분석 및 수정
4. 재시도

### 롤백 조건
- [ ] 테스트 실패율 >20%
- [ ] 응답 시간 >2배 증가
- [ ] 메모리 사용량 >50% 증가
- [ ] 치명적 버그 발견

---

## 타임라인 (예상)

| Phase | 기간 | 상태 |
|-------|------|------|
| Phase 1: 기반 구축 | 완료 | ✅ |
| Phase 2: 점진적 전환 | 1-2주 | ⏳ |
| Phase 3: 정리 | 1주 | ⏳ |

---

## 다음 단계

### 즉시 실행 가능
```bash
# 1. 의존성 설치
uv sync

# 2. 테스트 실행
uv run pytest tests/core/test_profile.py -v
uv run pytest tests/graph/test_state.py -v
uv run pytest tests/graph/test_agent_factory.py -v
uv run pytest tests/graph/test_workflow.py -v

# 3. 전체 테스트
uv run pytest -v
```

### 추가 작업 필요
1. **통합 테스트**: 실제 LLM과 함께 End-to-End 테스트
2. **Main 엔트리포인트**: 실행 가능한 회의 시스템 구현
3. **성능 벤치마킹**: 기존 vs 새 구현 비교

---

## 참고 사항

### langgraph-supervisor 제약사항
- 현재 버전 (v0.0.1)은 초기 릴리스
- 일부 기능 (후처리 핸들러)은 향후 버전에서 지원 예정
- Phase 전환은 Host 프롬프트로 처리 (현재 베스트 프랙티스)

### 알려진 이슈
- [ ] langgraph-supervisor가 실제로 PyPI에 게시되어 있는지 확인 필요
- [ ] 버전 호환성 (langgraph >=0.2.0과 호환되는지)

### 대안 (langgraph-supervisor 사용 불가 시)
- Command 기반 라우팅으로 대체
- 수동 핸드오프 도구 구현
- 계층 구조는 재귀적 StateGraph로 구현
