# LangGraph Supervisor 패턴 비교 분석

## 목적
현재 thetable 프로젝트의 supervisor 구현 방식과 공식 `langgraph-supervisor` 패키지를 비교하고, 최적의 접근 방식을 근거와 함께 추천

## 핵심 요구사항
1. **하위 에이전트를 도구(tool)처럼 호출** - Backend 에이전트가 하위 전문가를 호출
2. **팀 단위 조직 구성** - 개발 1팀, 개발 2팀 같은 구조
3. **동적 확장** - YAML 설정으로 무제한 계층 깊이 지원

---

## 1. 현재 구현 분석

### 아키텍처 구조
```
supervisor_node → [pm_agent | tech_lead_agent] → supervisor_node
       ↓
 conditional_edges (route_from_supervisor)
       ↓
phase_transition → (closing) → END
```

### 핵심 컴포넌트

| 컴포넌트 | 파일 | 역할 |
|---------|------|------|
| `SupervisorAgent` | `agents/supervisor.py` | LLM 기반 다음 발언자 결정 |
| `supervisor_node` | `graph/nodes.py` | 그래프 노드, 컨텍스트 수집 및 라우팅 |
| `create_agent_node` | `graph/nodes.py` | 에이전트 노드 팩토리 함수 |
| `PhaseController` | `graph/phase_controller.py` | Phase 상태 머신 전환 |
| `MeetingState` | `graph/state.py` | TypedDict 기반 상태 관리 |

### 현재 구현의 특징

**장점:**
1. Phase 기반 회의 흐름에 특화된 커스텀 상태
2. 글로벌 캐싱으로 에이전트/프로필 재사용 (성능 최적화)
3. `phase_triggers`로 에이전트별 맞춤 작업 지원
4. 회의 시스템에 맞는 도메인 특화 설계

**단점:**
1. 수동 JSON 파싱 (LLM 출력 → dict)
2. 글로벌 캐시가 스레드 안전하지 않음
3. `add_conditional_edges` 기반 라우팅은 정적임
4. 에러 핸들링 및 재시도 로직 부족
5. 계층적 확장이 어려움 (하위 에이전트 호출 패턴 미지원)

---

## 2. LangGraph Supervisor 패턴

### 채택한 방식: `langgraph-supervisor` 패키지

```python
from langgraph_supervisor import create_supervisor
from langgraph.prebuilt import create_react_agent

pm_agent = create_react_agent(
    model=model,
    tools=[report_status],
    name="PM"
)

workflow = create_supervisor(
    agents=[pm_agent, tech_lead_agent],
    model=model,
    prompt="You are the meeting host..."
)
```

**핵심 기능:**
- `create_react_agent`로 도구 기반 에이전트 생성
- 자동 핸드오프 도구 생성 (transfer_to_backend, transfer_to_frontend 등)
- 메시지 히스토리 자동 관리
- 계층적(Hierarchical) 슈퍼바이저 지원
- 팀을 서브그래프로 컴파일하여 상위 supervisor에 에이전트처럼 등록

---

## 3. 구현 비교

| 기준 | 현재 구현 | langgraph-supervisor |
|------|----------|---------------------|
| **코드 복잡도** | 중간 | 낮음 |
| **Phase 관리** | 커스텀 (유연) | Host 프롬프트로 통합 |
| **라우팅 방식** | conditional_edges | 자동 핸드오프 |
| **상태 관리** | 커스텀 TypedDict | MessagesState 상속 |
| **에이전트 정의** | BaseAgent 클래스 | create_react_agent |
| **도구 통합** | 수동 | 자동 (ReAct 패턴) |
| **계층적 확장** | 어려움 | 매우 쉬움 (재귀적 빌드) |
| **타입 안전성** | 낮음 | 중간 |
| **학습 곡선** | 중간 | 낮음 |
| **확장성** | 좋음 | 매우 좋음 |

---

## 4. 최종 추천: langgraph-supervisor 채택

### 이유

#### 1. 동적 계층 확장 지원 (★★★)
```python
# 팀을 서브그래프로 컴파일
dev_team_1 = create_supervisor(agents=[...]).compile(name="dev_team_1")

# 상위 supervisor에 팀 등록
host = create_supervisor(
    agents=[dev_team_1, dev_team_2, pm_agent],
    model=model
)
```

YAML에서 재귀적 구조 정의 → 코드에서 동적 빌드 가능

#### 2. 핸드오프 도구 자동 생성 (★★★)
```python
# langgraph-supervisor가 자동 생성:
# transfer_to_backend, transfer_to_frontend 등
# 하위 에이전트를 "도구처럼 호출"하는 패턴 기본 지원
```

#### 3. 팀 단위 조직 구성 (★★★)
```yaml
# agent_profiles.yaml
- name: TechLead
  agents:
    - name: Backend
    - name: Frontend
    - name: DevOps
```

계층 구조를 YAML에서 정의하면 자동으로 팀 빌드

#### 4. Phase 시스템 통합 방안 (★★)
- Phase 관리는 Host 프롬프트에서 처리
- PhaseController 불필요 (단순화)
- Host가 `[PHASE: next_phase]` 형식으로 전환 지시

---

## 5. 구현 세부사항

### 변경 대상 파일

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `pyproject.toml` | ✅ 수정 | langgraph-supervisor 의존성 추가 |
| `config/agent_profiles.yaml` | ✅ 수정 | agents 필드 추가 (계층 구조) |
| `thetable/core/profile.py` | ✅ 수정 | 재귀적 프로필 로딩 |
| `thetable/graph/state.py` | ✅ 수정 | MessagesState 상속 |
| `thetable/graph/agent_factory.py` | ✅ 신규 | 계층적 에이전트 빌더 |
| `thetable/graph/workflow.py` | ✅ 신규 | langgraph-supervisor 기반 워크플로우 |
| `thetable/graph/phase_controller.py` | ⏳ 정리 예정 | Host 프롬프트로 대체 |

### 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────┐
│         langgraph-supervisor with MeetingState              │
│                                                             │
│  MeetingState(MessagesState):  ◀── MessagesState 상속      │
│  ├── messages                                               │
│  ├── current_phase          ◀── Host가 직접 관리           │
│  ├── phase_history                                          │
│  └── speaker_counts                                         │
│                                                             │
│              Host (Supervisor)                              │
│              • Phase 규칙을 프롬프트로 이해                  │
│              • 필수 발언자 체크                              │
│              • Phase 전환 시점 직접 결정                    │
│                     │                                       │
│         ┌──────────┼──────────┐                            │
│         ▼          ▼          ▼                            │
│       PM      TechLead    Designer                          │
│                   │                                         │
│          ┌────────┼────────┐                               │
│          ▼        ▼        ▼                               │
│      Backend  Frontend  DevOps                              │
└─────────────────────────────────────────────────────────────┘

✅ PhaseController 불필요 - Host가 프롬프트로 판단
✅ Phase 래퍼 불필요 - 단일 그래프로 처리
✅ 계층적 확장 - YAML에서 무제한 depth 지원
```

---

## 6. 마이그레이션 전략

### Phase 1: 기반 구축 (완료 ✅)
1. ✅ `langgraph-supervisor` 의존성 추가
2. ✅ `MeetingState`를 `MessagesState` 상속으로 변경
3. ✅ `AgentProfile` 스키마 확장 (`agents` 필드)
4. ✅ `agent_profiles.yaml`에 계층 구조 추가
5. ✅ `build_agent_graph` 팩토리 구현
6. ✅ Host 프롬프트에 Phase 규칙 통합

### Phase 2: 점진적 전환 (다음 단계)
1. ⏳ 기존 워크플로우와 새 워크플로우 병행 운영
2. ⏳ 단일 팀 (예: TechLead 팀)부터 계층화 적용
3. ⏳ 테스트 케이스 업데이트

### Phase 3: 정리 (최종)
1. ⏳ `PhaseController` 삭제
2. ⏳ 기존 `SupervisorAgent` → `create_supervisor` 전환 완료
3. ⏳ 레거시 코드 정리

---

## 7. 검증 계획

### 기능 검증
- [ ] MessagesState 상속 상태가 langgraph-supervisor와 호환되는지
- [ ] Host가 Phase 전환을 올바르게 판단하는지
- [ ] 계층적 에이전트 (TechLead → Backend/Frontend) 핸드오프 동작
- [ ] speaker_counts가 올바르게 추적되는지

### 성능 검증
- [ ] 기존 대비 응답 시간 비교
- [ ] 메모리 사용량 측정
- [ ] 계층 깊이에 따른 성능 영향

### 품질 검증
```bash
# 의존성 설치
uv add langgraph-supervisor

# 테스트 실행
uv run pytest -v

# 회의 실행 (E2E)
uv run python -m thetable.main
```

---

## 8. 장단점 요약

### langgraph-supervisor 장점
✅ 동적 계층 확장 (무제한 depth)
✅ 하위 에이전트를 도구처럼 호출 (핸드오프)
✅ 팀 단위 조직 구성 (서브그래프)
✅ 자동 메시지 관리
✅ 코드 복잡도 감소
✅ 유지보수성 향상

### langgraph-supervisor 단점 (및 해결책)
⚠️ Phase 관리가 프롬프트 의존적
   → 해결: 명확한 Phase 규칙을 프롬프트에 명시
   
⚠️ 커스텀 동작 추가가 제한적
   → 해결: 후처리 핸들러로 보완
   
⚠️ 새로운 패키지 학습 필요
   → 해결: 공식 문서와 예제 코드 참고

---

## 9. 결론

**최종 추천: langgraph-supervisor 채택**

핵심 요구사항 (계층적 확장, 도구 기반 호출, 팀 구성)을 모두 만족하며, 코드 복잡도를 크게 줄일 수 있습니다.

현재 구현의 장점 (Phase 관리, 도메인 특화)은 Host 프롬프트와 MeetingState 상속으로 유지하면서, langgraph-supervisor의 강력한 계층적 구조를 활용할 수 있습니다.

---

## 부록: 참고 자료

- [LangGraph Supervisor Documentation](https://github.com/langchain-ai/langgraph-supervisor)
- [LangGraph Hierarchical Agent Teams](https://langchain-ai.github.io/langgraph/tutorials/multi_agent/hierarchical_agent_teams/)
- [LangGraph Messages State](https://langchain-ai.github.io/langgraph/concepts/low_level/#messagesstate)
