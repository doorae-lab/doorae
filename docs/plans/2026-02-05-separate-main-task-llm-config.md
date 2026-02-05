# Main/Task LLM 독립 설정 지원

**날짜:** 2026-02-05
**이슈:** #72
**브랜치:** feat/72

## 개요

Main LLM과 Task LLM을 서로 다른 제공자(OpenAI, Azure OpenAI, 로컬 LLM 등)에서 독립적으로 사용할 수 있도록 설정 구조를 개선합니다.

## 문제점

현재 Main과 Task LLM이 동일한 `openai_api_key`와 `openai_base_url`을 공유하여 다음 시나리오가 불가능:
- Main: OpenAI GPT-4o-mini, Task: Azure OpenAI GPT-3.5-turbo
- Main: 외부 OpenAI API, Task: 로컬 Ollama 서버

## 설계 결정 사항

### 접근 방식
- **Flat Fallback 방식** 채택
- Core 설정만 구현 (api_key, base_url)
- Property에서 strict 검증

### 설정 구조

```python
class Settings(BaseSettings):
    # === 공통 설정 (Fallback) ===
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None

    # === Main LLM 독립 설정 ===
    llm_main_api_key: Optional[str] = None
    llm_main_base_url: Optional[str] = None
    llm_main_model: str = "gpt-4o-mini"
    llm_main_temperature: float = 0.7
    llm_main_max_tokens: int = 4096

    # === Task LLM 독립 설정 ===
    llm_task_api_key: Optional[str] = None
    llm_task_base_url: Optional[str] = None
    llm_task_model: str = "gpt-4o-mini"
    llm_task_temperature: float = 0.0
    llm_task_max_tokens: int = 2048

    # === Property로 Fallback 처리 ===
    @property
    def main_api_key(self) -> str:
        """Main LLM API 키 (fallback: openai_api_key)"""
        key = self.llm_main_api_key or self.openai_api_key
        if not key:
            raise ValueError(
                "Main LLM API key is required.\n"
                "Please set one of the following in your .env file:\n"
                "  - LLM_MAIN_API_KEY (Main LLM 전용)\n"
                "  - OPENAI_API_KEY (공통 fallback)"
            )
        return key

    @property
    def main_base_url(self) -> Optional[str]:
        """Main LLM Base URL (fallback: openai_base_url)"""
        return self.llm_main_base_url or self.openai_base_url

    @property
    def task_api_key(self) -> str:
        """Task LLM API 키 (fallback: openai_api_key)"""
        key = self.llm_task_api_key or self.openai_api_key
        if not key:
            raise ValueError(
                "Task LLM API key is required.\n"
                "Please set one of the following in your .env file:\n"
                "  - LLM_TASK_API_KEY (Task LLM 전용)\n"
                "  - OPENAI_API_KEY (공통 fallback)"
            )
        return key

    @property
    def task_base_url(self) -> Optional[str]:
        """Task LLM Base URL (fallback: openai_base_url)"""
        return self.llm_task_base_url or self.openai_base_url
```

## .env 예시

### 시나리오 1: 단일 제공자 (기존 방식, 하위 호환)
```bash
OPENAI_API_KEY=sk-proj-xxx
LLM_MAIN_MODEL=gpt-4o-mini
LLM_TASK_MODEL=gpt-4o-mini
```

### 시나리오 2: Main은 OpenAI, Task는 Azure
```bash
OPENAI_API_KEY=sk-proj-xxx
LLM_MAIN_MODEL=gpt-4o-mini

LLM_TASK_API_KEY=azure-key-yyy
LLM_TASK_BASE_URL=https://myresource.openai.azure.com/...
LLM_TASK_MODEL=gpt-35-turbo
```

### 시나리오 3: Main은 외부, Task는 로컬 Ollama
```bash
OPENAI_API_KEY=sk-proj-xxx
LLM_MAIN_MODEL=gpt-4o-mini

LLM_TASK_BASE_URL=http://localhost:11434/v1
LLM_TASK_MODEL=llama3
```

## 구현 계획

### 1단계: Settings 클래스 수정
- `thetable/config/settings.py`
  - `openai_api_key`를 `Optional[str]`로 변경
  - `llm_main_api_key`, `llm_main_base_url` 추가
  - `llm_task_api_key`, `llm_task_base_url` 추가
  - 4개 property 추가

### 2단계: 환경 변수 예시 업데이트
- `.env.example` - 새로운 설정 항목 및 시나리오 예시 추가

### 3단계: 기존 코드 수정
- `thetable/graph/workflow.py`
  - `create_meeting_workflow()`: property 사용하도록 수정
- `thetable/agents/base_agent.py`
  - `_init_default_llm()`: property 사용하도록 수정

### 4단계: 테스트 작성
- `tests/config/test_settings.py`
  - `test_main_api_key_fallback`
  - `test_main_api_key_override`
  - `test_main_api_key_missing_raises_error`
  - `test_task_base_url_fallback`
  - `test_mixed_providers`

### 5단계: 검증
- 기존 .env (공통 키만 사용) → 정상 작동
- Main/Task 분리 설정 → 각각 다른 제공자 사용
- API 키 누락 → 명확한 에러 메시지
- 모든 단위 테스트 통과

## 체크리스트

**코드 수정:**
- [ ] `thetable/config/settings.py` - Settings 클래스 수정
- [ ] `thetable/graph/workflow.py` - Main/Task LLM 생성 로직 수정
- [ ] `thetable/agents/base_agent.py` - BaseAgent LLM 초기화 수정
- [ ] `.env.example` - 새 설정 항목 및 예시 추가

**테스트:**
- [ ] `tests/config/test_settings.py` - 5개 테스트 케이스 추가
- [ ] 모든 기존 테스트 통과 (하위 호환성 확인)

**검증:**
- [ ] 로컬에서 기존 설정으로 실행 → 정상 작동
- [ ] 로컬에서 분리 설정으로 실행 → 각각 다른 제공자 사용 확인

## 영향 범위

**수정 파일:** 3개
**새 테스트:** 5개
**하위 호환성:** ✅ 완전 유지
**마이그레이션:** 불필요 (기존 .env 그대로 작동)

## 기대 효과

1. **유연성 향상**: 다양한 LLM 프로바이더 조합 가능
2. **비용 최적화**: Main은 강력한 모델, Task는 저렴한 모델 사용
3. **멀티 클라우드**: OpenAI + Azure OpenAI 혼합 구성 가능
4. **로컬 개발**: Main은 외부 API, Task는 로컬 Ollama 사용
5. **하위 호환성**: 기존 설정 파일 그대로 작동
