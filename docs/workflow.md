# LangGraph 워크플로우

## MeetingState 필드

### 안건 관리
- `agendas: List[dict]` - 회의 안건 목록 (Agenda 모델의 dict 변환)
- `current_agenda_idx: int` - 현재 진행 중인 안건 인덱스

### 발언자 큐
- `pending_speakers: List[str]` - 다음 발언자 대기 큐 (예: `["PM", "TechLead"]`)

### 발언 추적
- `speaker_counts: Dict[str, int]` - 각 참여자의 발언 횟수 카운트

### 무한루프 방지
- `consecutive_host_delegations: int` - 연속 Host 위임 횟수 (3회 이상 시 강제 종료)
- `turn_count: int` - 전체 턴 수
- `max_turns: int` - 최대 턴 제한 (기본값 1000)

### 회의 제어
- `meeting_ended: bool` - 회의 종료 플래그
- `summary: str` - 대화 요약 (토큰 관리용)

### 메타데이터
- `start_time: float` - 회의 시작 시간 (Unix timestamp)
- `messages: List[BaseMessage]` - LangGraph MessagesState 상속

---

## 워크플로우 사이클

```mermaid
graph TB
    START([회의 시작]) --> refill[refill_speakers]
    refill --> router{condition_router}

    router -->|pending_speakers 비어있음| refill
    router -->|meeting_ended=true| END([회의 종료])
    router -->|turn_count >= max_turns| END
    router -->|pending_speakers[0]| agent[Agent Node]

    agent --> summarize[summarize]
    summarize --> process[process_response]
    process --> router

    style refill fill:#e1f5ff
    style router fill:#fff3cd
    style agent fill:#d4edda
    style summarize fill:#f8d7da
    style process fill:#d1ecf1
```

### 노드 실행 순서

1. **refill_speakers** → pending_speakers 비어있으면 채우기
2. **condition_router** → 다음 노드 결정 (순수 상태 기반, LLM 미사용)
3. **Agent Node** → LLM 기반 발언 생성 (tool-calling 지원)
4. **summarize** → 메시지 개수 초과 시 요약
5. **process_response** → 멘션 추출, 안건 완료, 종료 감지
6. **condition_router** → (사이클 반복)

---

## 노드 상세

### refill_speakers 노드

**역할**: pending_speakers 비어있을 때 채우기

**입력**:
- `agendas[current_agenda_idx].required_speakers` - 필수 발언자 목록
- `speaker_counts` - 이미 발언한 참여자 추적

**로직**:
1. 안건의 `required_speakers` 중 아직 발언하지 않은 참여자 찾기
2. `valid_speakers`로 필터링 (비활성 에이전트 제외)
3. 남은 참여자가 있으면 최대 2명씩 `pending_speakers`에 추가
4. 모두 발언했으면 Host에게 위임
5. Host 연속 위임 3회 이상 시 강제 종료

**출력**:
- `pending_speakers` - 업데이트된 발언자 큐
- `consecutive_host_delegations` - Host 위임 횟수

**무한루프 방지**:
- Host 연속 위임 3회 시 `consecutive_host_delegations=0` 리셋 후 강제 진행

**파일**: `thetable/graph/nodes/refill.py`

---

### condition_router 함수

**역할**: 순수 상태 기반 라우팅 (LLM 미사용)

**우선순위**:
1. `meeting_ended=true` → END
2. `turn_count >= max_turns` → END
3. `pending_speakers` 비어있음 → `refill_speakers`
4. `pending_speakers[0]` → 해당 에이전트 노드
5. fallback → END

**특징**:
- LLM 호출 없이 상태만으로 분기 결정
- 성능 최적화 (라우팅마다 LLM 호출 불필요)

**파일**: `thetable/graph/nodes/router.py`

---

### Agent 노드

**역할**: BaseAgent 래핑, LLM 기반 발언 생성

**입력**:
- `messages` - 대화 기록
- `summary` - 요약문 (토큰 절약)
- `agendas[current_agenda_idx]` - 현재 안건 컨텍스트

**로직**:
1. 시스템 프롬프트 구성 (역할, 책임, 전문성, MCP 도구 목록)
2. 안건 컨텍스트 추가 (제목, 설명, 필수 발언자)
3. 대화 요약 포함 (최근 메시지 토큰 절약)
4. `BaseAgent.invoke_with_tools()` 호출
5. Tool-calling 루프 실행 (최대 50회)
6. 최종 AIMessage 반환

**Tool-calling 루프** (`BaseAgent.invoke_with_tools()`):
```python
while iteration < 50:
    response = await llm.bind_tools(mcp_tools).ainvoke(messages)

    if not response.tool_calls:
        return response  # 최종 응답

    # 도구 실행
    for tool_call in response.tool_calls:
        result = await tool_fn.ainvoke(tool_call["args"])
        messages.append(ToolMessage(content=result, tool_call_id=...))
```

**출력**:
- AIMessage (name, content 포함)

**파일**:
- `thetable/graph/nodes/agent.py` (AgentNode)
- `thetable/agents/base_agent.py` (BaseAgent)

---

### summarize 노드

**역할**: 대화 요약 (토큰 관리)

**임계값**:
- `max_messages_before_summary=5` (기본값)
- 메시지 개수 초과 시 자동 요약

**로직**:
1. 메시지 개수 체크 (`len(messages) > threshold`)
2. Task LLM으로 대화 요약 생성 (최대 3000 토큰)
3. 최근 3개 메시지 유지
4. `summary` 필드 업데이트

**출력**:
- `summary` - 업데이트된 요약문
- `messages` - 최근 3개만 유지 (현재 구현에서는 유지, 향후 개선 필요)

**파일**: `thetable/graph/nodes/summarize.py`

---

### process_response 노드

**역할**: 멘션 추출, 안건 완료 감지, 종료 감지, 동적 안건 업데이트

**입력**:
- `messages[-1]` - 마지막 발언
- `agendas` - 안건 리스트
- `speaker_counts` - 발언 횟수

**로직**:

#### 1. 발언자 제거 및 카운트
- 현재 발언자를 `pending_speakers`에서 제거
- `speaker_counts[speaker_name]` 증가

#### 2. 멘션 추출 (LLM 기반)
```python
prompt = """다음 발언에서 언급된 참여자를 추출하세요.
발언: "{content}"
선택 가능한 참여자: {valid_speakers}
언급된 참여자 이름만 쉼표로 구분하여 출력 (없으면 "없음"):"""
```
- Task LLM으로 멘션 추출
- 추출된 참여자를 `pending_speakers`에 추가 (중복 제외)

#### 3. 안건 완료 감지 (Host 발언만)
**키워드 기반**:
```python
completion_keywords = [
    "다음 안건", "다음으로", "넘어가", "마무리",
    "정리하면", "결론", "이 안건은 여기까지"
]
```
- 키워드 감지 시 현재 안건 `status="completed"`, `end_time` 설정
- `current_agenda_idx` 증가
- 다음 안건 `status="in_progress"`, `start_time` 설정
- `pending_speakers` 초기화

#### 4. 회의 종료 감지 (Host 발언만)
**1단계: 키워드 감지** (안건 상태 무관)
```python
end_keywords = [
    "회의를 마치겠습니다", "회의를 종료",
    "이상으로 마치겠습니다", "오늘 회의는 여기까지"
]
```
**2단계: LLM 분석** (키워드 미감지 + 안건 80% 이상 완료)
```python
prompt = """다음 Host의 발언이 회의를 종료하려는 의도인지 판단하세요.
발언: "{content}"
회의 종료 의도가 명확하면 "예", 아니면 "아니오"로만 답하세요:"""
```
- 안건 완료율 ≥ 80% 시에만 LLM 호출 (토큰 절약)
- `meeting_ended=true` 설정

#### 5. 안건 동적 업데이트 (매 발언마다)
- 최근 10개 메시지 분석 (`extract_agenda_updates()`)
- Task LLM으로 안건 추가/수정/삭제 판단
- 기존 안건 메타데이터 보존 (`status`, `start_time`, `end_time`)
- 타임스탬프 자동 설정 (`_ensure_agenda_timestamps()`)

**출력**:
- `pending_speakers` - 업데이트된 큐
- `speaker_counts` - 업데이트된 카운트
- `current_agenda_idx` - 다음 안건 인덱스
- `agendas` - 업데이트된 안건 리스트
- `consecutive_host_delegations` - 0으로 리셋
- `turn_count` - 증가
- `meeting_ended` - 종료 플래그

**파일**: `thetable/graph/nodes/process.py`

---

## 노드 플러그인 시스템

### BaseNode ABC

**추상 클래스**: 모든 노드는 `BaseNode`를 상속받아 `execute()` 메서드 구현

```python
from thetable.graph.nodes.base import BaseNode, NodeType

class CustomNode(BaseNode):
    node_type = NodeType.UTILITY  # AGENT, UTILITY, HUMAN, ROUTING
    requires_llm = True  # LLM 필요 여부
    requires_tools = False  # MCP 도구 필요 여부

    async def execute(self, state: MeetingState) -> Dict[str, Any]:
        # 상태 처리 로직
        return {"field": "value"}
```

**훅 메서드**:
- `on_enter(state)` - 노드 진입 전 실행 (전처리)
- `on_exit(state, result)` - 노드 종료 후 실행 (후처리)

**LangGraph 호환**:
- `__call__(state)` - LangGraph가 호출하는 메서드 (자동 구현)

**파일**: `thetable/graph/nodes/base.py`

---

### NodeRegistry 및 @register_node 데코레이터

**레지스트리 패턴**: 노드를 플러그인 방식으로 등록 및 관리

```python
from thetable.graph.nodes.registry import register_node

@register_node("custom_node", category="custom")
class CustomNode(BaseNode):
    async def execute(self, state: MeetingState) -> Dict[str, Any]:
        return {}
```

**장점**:
- 새 노드 추가 시 워크플로우 수정 불필요
- `NodeRegistry.create("custom_node", ...)` 동적 생성
- 카테고리별 노드 조회 가능
- 플러그인 자동 발견 (`discover_plugins()`)

**노드 생성**:
```python
node = NodeRegistry.create(
    "agent",
    profile=profile,
    model=main_llm,
    all_agent_names=list(profiles.keys()),
    mcp_tools=mcp_tools
)
workflow.add_node("host", node)
```

**파일**: `thetable/graph/nodes/registry.py`

---

## 안건 관리 시스템

### 정적 안건 (YAML)

**파일**: `config/agendas.yaml`

```yaml
- title: 프로젝트 현황 공유
  description: 현재 진행 상황 및 이슈 사항 공유
  status: pending
  required_speakers:
    - PM
    - TechLead
```

**로드**: `load_agendas()` 함수로 초기 안건 로드

---

### 동적 안건 (LLM 기반)

**목적**: 회의 중 새로운 안건 발견 및 기존 안건 수정

**실행 시점**: 매 발언마다 (`ProcessResponseNode.execute()`)

**로직**:
1. 최근 10개 메시지를 `extract_agenda_updates()`에 전달
2. Task LLM으로 안건 분석 (Structured Output 사용)
3. 새 안건 추가, 기존 안건 수정, 상태 변경
4. 기존 메타데이터 보존 (`status`, `start_time`, `end_time`)
5. 타임스탬프 자동 설정

**프롬프트 규칙**:
- 구체적인 논의 주제만 안건으로 등록
- 기존 안건은 절대 삭제하지 않음 (업데이트만 가능)
- 제목은 한국어로 30자 이내
- 담당자(`owner`)는 명시적으로 언급된 경우만 설정
- 결정사항(`decision`)은 명확한 결론이 나왔을 때만 기록

**상태 종류**:
- `pending` - 아직 논의 안 됨
- `in_progress` - 현재 논의 중
- `completed` - 완료
- `deferred` - 보류/연기

**파일**: `thetable/graph/agenda_manager.py`

---

## 참고 파일

- `thetable/graph/workflow.py` - 워크플로우 생성 (`create_meeting_workflow()`)
- `thetable/graph/state.py` - MeetingState, Agenda 정의
- `thetable/graph/nodes/base.py` - BaseNode 추상 클래스
- `thetable/graph/nodes/registry.py` - NodeRegistry, @register_node
- `thetable/graph/nodes/agent.py` - AgentNode 구현
- `thetable/graph/nodes/refill.py` - RefillSpeakersNode 구현
- `thetable/graph/nodes/router.py` - condition_router 함수
- `thetable/graph/nodes/process.py` - ProcessResponseNode 구현
- `thetable/graph/nodes/summarize.py` - SummarizationNode 구현
- `thetable/graph/agenda_manager.py` - extract_agenda_updates 함수
