# 동적 안건 관리 시스템 디자인

**날짜**: 2026-02-02
**목표**: 회의 흐름에 따라 AI가 자동으로 안건을 추가/수정/제거하는 시스템 구현

## 배경

현재 `thetable` 프로젝트는 정적인 안건 리스트만 지원합니다. 회의 중 새로운 이슈가 발생하거나 논의 방향이 바뀔 때 안건을 동적으로 관리할 필요가 있습니다.

POC 프로젝트(`thetable-poc`)에는 `AgendaManager` 클래스와 `extract_agenda_updates` 함수가 구현되어 있으나, 객체 지향 구조로 인해 LangGraph State 직렬화 문제가 있습니다.

## 설계 결정

### 1. 안건 관리 방식
- **선택**: AI가 자동으로 판단 (A)
- **이유**: 회의 흐름에 자연스럽게 적응, 자동화

### 2. 업데이트 타이밍
- **선택**: 매 발언 후마다 (A)
- **이유**: 실시간 반영, 놓치는 것 없음
- **트레이드오프**: LLM 호출 증가 (10턴: ~$0.01, 30턴: ~$0.03)

### 3. 구현 접근법
- **선택**: 현재 구조에 맞게 재설계 (B)
- **이유**:
  - LangGraph State 완벽 호환 (dict 기반)
  - 직렬화 문제 없음
  - YAGNI 준수
  - 성능 우수

## 아키텍처

### 전체 구조

```
에이전트 발언
  → process_response
  → extract_agenda_updates (LLM 호출)
  → Pydantic 모델 검증
  → dict 변환
  → State 업데이트
```

### 주요 컴포넌트

#### 1. Agenda 모델 확장 (`thetable/graph/state.py`)

```python
class Agenda(BaseModel):
    title: str
    description: str = ""
    status: str = "pending"  # "pending", "in_progress", "completed", "deferred"
    required_speakers: List[str] = []

    # 추가 필드
    owner: Optional[str] = None  # 안건 담당자
    decision: Optional[str] = None  # 결정 사항
    time_limit: int = 300  # 초 단위 (5분 기본)
    start_time: Optional[float] = None  # Unix timestamp
    end_time: Optional[float] = None
```

#### 2. 안건 추출 모듈 (`thetable/graph/agenda_manager.py`)

**새 파일 생성**, POC의 `extract_agenda_updates` 함수 이식:

```python
class AgendaExtractionResult(BaseModel):
    """안건 추출 결과"""
    items: List[dict] = Field(default_factory=list)
    changes_summary: Optional[str] = None

async def extract_agenda_updates(
    llm: BaseChatModel,
    messages: List[BaseMessage],
    current_items: List[dict],
) -> AgendaExtractionResult:
    """
    최근 대화를 분석하여 안건 추가/수정/제거

    Args:
        llm: LLM 모델
        messages: 최근 대화 메시지 (마지막 10개)
        current_items: 현재 안건 리스트 (dict)

    Returns:
        업데이트된 안건 리스트
    """
    # 1. 현재 안건 컨텍스트 생성
    # 2. 대화 컨텍스트 생성
    # 3. LLM에게 안건 업데이트 요청
    # 4. 구조화된 출력 파싱
    # 5. 실패 시 기존 안건 유지
```

#### 3. workflow.py 수정

`process_response` 함수에 안건 업데이트 로직 추가:

```python
async def process_response(state: MeetingState, model, valid_speakers: list[str]) -> dict:
    """에이전트 응답 처리 + 안건 업데이트"""
    messages = state.get("messages", [])
    # ... 기존 로직 (멘션 추출, pending 업데이트 등)

    # ===== 안건 업데이트 =====
    from thetable.graph.agenda_manager import extract_agenda_updates

    recent_messages = messages[-10:]  # 최근 10개만
    current_agendas = state.get("agendas", [])

    try:
        agenda_result = await extract_agenda_updates(
            llm=model,
            messages=recent_messages,
            current_items=current_agendas,
        )
        new_agendas = agenda_result.items
    except Exception as e:
        print(f"⚠️ 안건 업데이트 실패: {e}")
        new_agendas = current_agendas

    return {
        "pending_speakers": new_pending,
        "speaker_counts": new_counts,
        "agendas": new_agendas,  # 업데이트된 안건
        # ... 나머지 필드
    }
```

## 에러 핸들링

### 3단계 Fallback 전략

1. **1차 시도**: 구조화된 출력 (`with_structured_output`)
2. **2차 시도**: JSON 파싱 (POC 방식)
3. **최종 Fallback**: 기존 안건 유지

```python
try:
    structured_llm = llm.with_structured_output(AgendaExtractionResult)
    result = structured_llm.invoke([...])
except Exception:
    try:
        # JSON 파싱 시도
        ...
    except Exception:
        # 기존 안건 유지
        return AgendaExtractionResult(items=current_items)
```

### 안전성 보장

- LLM 실패 시에도 회의 계속 진행
- 기존 안건 절대 삭제되지 않음 (POC 규칙 유지)
- Pydantic 모델로 타입 검증

## 성능 최적화

### 토큰 절약
- 최근 10개 메시지만 분석 (~2K 토큰 절약)
- 불필요한 컨텍스트 제거

### 비용 추정
- **10턴 회의**: ~$0.01
- **30턴 회의**: ~$0.03

### 기타 최적화
- LLM 호출 타임아웃: 5초
- 캐싱 고려 (선택사항)

## 테스트 전략

### 단위 테스트 (`tests/graph/test_agenda_manager.py`)

```python
async def test_extract_agenda_updates():
    """안건 추출 기본 테스트"""
    messages = [
        HumanMessage(content="새로운 이슈가 발생했어요", name="PM"),
        HumanMessage(content="긴급 배포 건 논의가 필요합니다", name="DevOps"),
    ]

    result = await extract_agenda_updates(
        llm=mock_llm,
        messages=messages,
        current_items=[{"title": "기존 안건", "status": "pending"}],
    )

    assert len(result.items) >= 1
    assert any(item["title"] == "기존 안건" for item in result.items)

async def test_agenda_update_failure():
    """LLM 실패 시 기존 안건 유지"""
    # 기존 안건이 그대로 반환되는지 확인
```

### 통합 테스트
- `examples/agenda_based_meeting.py` 실행
- 안건 자동 추가/완료/보류 확인

## 구현 순서

1. **state.py 수정** - Agenda 모델 확장 (5분)
2. **agenda_manager.py 생성** - POC 함수 이식 (15분)
3. **workflow.py 수정** - process_response 통합 (10분)
4. **테스트 작성** - 기본 시나리오 검증 (15분)
5. **통합 테스트** - 실제 회의 시뮬레이션 (5분)

**예상 소요 시간**: 약 50분

## 검증 기준

- ✅ 회의 중 새 안건 자동 추가
- ✅ 안건 상태 자동 업데이트 (completed, deferred)
- ✅ LLM 실패 시 기존 안건 유지
- ✅ 모든 테스트 통과
- ✅ 성능: 매 발언당 <1초 추가 지연

## 향후 개선 사항

- 안건 우선순위 자동 조정
- 시간 초과 안건 자동 경고
- 안건 히스토리 추적
- 대시보드 시각화

## 참고

- POC 구현: `/home/e7217/projects/thetable-poc/thetable_poc/graph/agenda_extraction.py`
- 관련 이슈: 회의 흐름에 따른 동적 안건 관리 필요성
