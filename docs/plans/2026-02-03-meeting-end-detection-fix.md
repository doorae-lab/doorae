# 회의 종료 감지 실패 문제 해결

**날짜**: 2026-02-03
**상태**: 설계 완료
**우선순위**: 높음 (Critical)

## 문제 요약

LangSmith 트레이스 분석 결과, 회의 시스템에 3가지 심각한 문제 발견:

1. **끝나지 않는 회의**: Host가 "회의를 종료합니다" 발언 후에도 회의가 계속 진행
2. **무한 안건 생성**: 초기 7개 → 최종 30개 (평균 0.4개/턴 속도로 증가)
3. **리소스 낭비**: 21.9분 실행, 73만 토큰 사용 후 네트워크 에러로 강제 종료

## 트레이스 분석 데이터

### Trace ID: `019c2204-e6ba-7dd2-9d45-4c9fab9c7180`

**실행 정보**:
- 총 실행 시간: 21.9분
- 총 토큰: 731,665
- 자식 실행: 665개
- 최종 상태: error (CancelledError)

**안건 증가 패턴**:
```
턴  5: 안건  7개 (초기)
턴 29: 안건 16개 (+9개, 24턴간)
턴 63: 안건 30개 (+14개, 34턴간)
```

**마지막 4개 메시지** (63턴째):
1. Host: "회의를 **공식적으로 종료**합니다..."
2. TechLead: 이슈 생성 완료 보고
3. PM: 체크포인트 일정 확정
4. Host: "**회의를 종료**합니다"

**상태**:
- `meeting_ended = False` (종료되지 않음!)
- 완료 안건: 24개, 진행중: 4개, 대기: 2개

## 근본 원인 분석

### 1. 회의 종료 감지 로직 결함

**문제 코드** (`thetable/graph/workflow.py:242-248`):
```python
all_agendas_done = all(a["status"] in ["completed", "deferred"] for a in new_agendas)
if speaker_name == "Host" and all_agendas_done:  # ← 이 조건 때문!
    if detect_meeting_end_keyword(content):
        meeting_ended = True
```

**문제점**:
- `all_agendas_done`이 False이면 `if` 블록 전체가 실행되지 않음
- 즉, `detect_meeting_end_keyword()` 함수 호출 자체가 안 일어남
- 트레이스에서 `all_agendas_done = False` (진행 중/대기 안건 존재)
- 따라서 Host가 "회의를 종료합니다" 발언해도 **키워드 검사 자체를 안 함**

**시나리오**:
1. Host: "회의를 종료합니다" 발언
2. `all_agendas_done = False` (진행 중 안건 있음)
3. `if speaker_name == "Host" and False:` → 조건 실패
4. 키워드 검사 함수 **호출조차 안 됨**
5. `meeting_ended`는 False로 유지
6. 회의 계속 진행

### 2. 무한 안건 생성

**원인** (`thetable/graph/workflow.py:252-270`):
```python
# 7. 안건 동적 업데이트 (매 발언마다)
agenda_result = await extract_agenda_updates(
    llm=model,
    messages=recent_messages,
    current_items=new_agendas,
)
```

**문제점**:
- 매 턴마다 LLM이 안건을 동적으로 업데이트
- 안건 추가에 대한 제한 없음 (최대 개수, 생성 빈도 등)
- 프롬프트에 "기존 안건 삭제 금지" 규칙만 있고 "추가 제한" 없음
- 34턴 동안 14개 안건 추가 (평균 0.41개/턴)

### 3. 순환 참조

**악순환 패턴**:
1. Host가 종료 발언
2. 새로운 안건이 생성됨 ("회의 마무리" 등)
3. `all_agendas_done = False`
4. 종료 감지 안 됨
5. 회의 계속 → 1번으로 돌아감

## 해결 방안

### 우선순위 1: 회의 종료 감지 로직 개선 ✅

**핵심**: `all_agendas_done` 조건을 종료 키워드 감지에서 제거

#### 변경 1: `thetable/graph/workflow.py`

**위치**: 242-250줄

**Before**:
```python
all_agendas_done = all(a["status"] in ["completed", "deferred"] for a in new_agendas)
if speaker_name == "Host" and all_agendas_done:
    if detect_meeting_end_keyword(content):
        meeting_ended = True
    elif await detect_meeting_end_llm(content, model):
        meeting_ended = True
```

**After**:
```python
if speaker_name == "Host":
    # 1단계: 키워드 감지 (최우선, 안건 상태 무관)
    if detect_meeting_end_keyword(content):
        meeting_ended = True

    # 2단계: LLM 분석 (키워드 미감지 + 안건 대부분 완료)
    elif len(new_agendas) > 0:
        completed_count = sum(1 for a in new_agendas
                            if a["status"] in ["completed", "deferred"])
        completion_rate = completed_count / len(new_agendas)

        # 80% 이상 완료 시에만 LLM 분석 (토큰 절약)
        if completion_rate >= 0.8:
            meeting_ended = await detect_meeting_end_llm(content, model)
```

**효과**:
- Host의 종료 키워드 발언 시 **즉시 감지**
- 안건 상태와 무관하게 명시적 종료 시그널 우선 처리
- LLM 분석은 안건 80% 완료 시에만 작동 (토큰 절약)

#### 변경 2: `thetable/agents/base_agent.py`

**위치**: `_build_system_prompt()` 함수

**추가 코드**:
```python
def _build_system_prompt(self) -> str:
    """시스템 프롬프트 생성"""
    prompt = f"""You are {self.name}, a {self.profile.role}.

Your responsibilities:
{chr(10).join(f'- {r}' for r in self.profile.responsibilities)}

Your expertise:
{chr(10).join(f'- {e}' for e in self.profile.expertise)}

Respond according to your role and the given task.
"""

    # metadata에서 추가 지시사항 로드
    if "additional_instructions" in self.profile.metadata:
        prompt += f"\n\n{self.profile.metadata['additional_instructions']}"

    return prompt
```

#### 변경 3: `config/agent_profiles.yaml`

**Host 프로필 개선**:
```yaml
agents:
  - name: Host
    role: host
    responsibilities:
      - 회의 시작 인사 및 안건 소개
      - 안건 진행 상황 관리
      - 토론 중재 및 의견 요청
      - 안건 완료 시 다음 안건으로 전환 안내
      - 회의 요약 및 마무리
      - '회의 완전 종료 시에만 "회의를 종료합니다" 등의 명시적 종료 시그널 발언 (안건 미완료 시 사용 금지)'
    expertise:
      - 회의 퍼실리테이션
      - 시간 관리
      - 갈등 조정
      - 안건 진행 관리
    phase_triggers: {}
    metadata:
      additional_instructions: |
        ## 회의 종료 프로토콜 (CRITICAL)

        **회의 종료 조건** (모두 충족되어야 함):
        1. 모든 주요 안건이 논의 완료되었거나 명시적으로 보류 결정됨
        2. 참여자들에게 추가 논의 사항 확인 완료
        3. 회의 요약 및 다음 액션 아이템 정리 완료

        **종료 시그널 발언 규칙**:
        - 위 3가지 조건이 모두 충족된 경우에만 아래 표현 사용:
          * "회의를 종료합니다"
          * "회의를 마치겠습니다"
          * "이상으로 회의를 마무리하겠습니다"

        **금지 사항**:
        - 안건이 아직 진행 중일 때 종료 표현 사용 금지
        - 중간 요약 시에는 "현재까지 정리", "중간 점검" 등의 표현 사용
        - 불확실할 때는 "추가로 논의할 사항이 있으신가요?" 질문 우선
```

**효과**:
1. **Responsibilities**: Host가 책임사항으로 명확히 인지
2. **Additional Instructions**: 상세한 프로토콜로 조기 종료 방지

### 우선순위 2: 안건 생성 제한 (후속 작업)

**참고**: 현재는 종료 감지 개선에 집중, 안건 생성 제한은 별도 이슈로 추진

**향후 개선 방안**:
- 최대 안건 개수 제한 (예: 20개)
- 안건 생성 빈도 제한 (예: 5턴마다 1회)
- 중복 안건 자동 병합

### 우선순위 3: 추가 안전장치 (선택적)

**최대 턴 수 축소**:
- 현재: 1000턴
- 권장: 50-100턴

**실행 시간 제한**:
- 예: 10분 타임아웃

## 기대 효과

### Before (문제 상황)
1. Host: "회의를 종료합니다" 발언
2. `all_agendas_done = False` (진행 중 안건 있음)
3. 키워드 검사 **실행 안 됨** ❌
4. 회의 계속 진행
5. 21분 실행 후 에러로 강제 종료

### After (수정 후)
1. Host: "회의를 종료합니다" 발언
2. 키워드 검사 **즉시 실행** ✅
3. `meeting_ended = True`
4. `condition_router`에서 `END`로 라우팅
5. **회의 정상 종료!** 🎉

### 측정 가능한 개선

✅ Host가 안건 미완료 시 종료 키워드 사용하지 않음 (프롬프트 개선)
✅ Host가 조건 충족 시 명시적 종료 발언
✅ 종료 키워드 발언 즉시 `meeting_ended = True`
✅ 21분 무한 실행 문제 해결
✅ 안건 30개 생성 문제 완화 (종료 시점 빨라짐)
✅ 리소스 낭비 방지 (토큰, 실행 시간)

## 검증 방법

### 수동 테스트

1. `uv run python -m thetable` 실행
2. "회의를 시작합니다" 입력
3. 안건 진행 중 Host 발언 확인 → 종료 키워드 없어야 함
4. 모든 안건 완료 후 Host 발언 → "회의를 종료합니다" 포함
5. 회의 정상 종료 확인

### LangSmith 트레이스 확인

- `meeting_ended` 플래그 변경 시점 추적
- Host의 종료 발언과 플래그 설정 시점 일치 확인
- 안건 완료율과 LLM 분석 실행 여부 확인
- 실행 시간 < 5분 확인
- 안건 개수 < 15개 확인

## 구현 순서

1. ✅ 문제 분석 및 설계 완료
2. `thetable/graph/workflow.py` 수정
3. `thetable/agents/base_agent.py` 수정
4. `config/agent_profiles.yaml` 수정
5. 테스트 실행 및 검증
6. LangSmith 트레이스 확인
7. 후속 이슈 생성 (안건 생성 제한)

## 참고 자료

- **트레이스 ID**: `019c2204-e6ba-7dd2-9d45-4c9fab9c7180`
- **분석 도구**: `uvx langsmith-fetch`
- **관련 커밋**:
  - e8e26d3: fix: 스트리밍 필터링 및 회의 종료 조건 개선 (#46)
  - 4716f7f: feat: 회의 흐름에 따른 동적 안건 관리 시스템 구현 (#42)

## 후속 작업

1. 안건 생성 제한 시스템 구현 (#XX)
2. 최대 턴 수 및 시간 제한 강화 (#XX)
3. 회의 종료 조건 모니터링 대시보드 (#XX)
