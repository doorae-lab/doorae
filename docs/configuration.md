# 설정 파일 가이드

> Doorae을 내 입맛에 맞게 설정하는 방법을 알아봐요.

---

## 설정 파일이 뭔가요?

Doorae은 **4개의 설정 파일**로 동작 방식을 조정해요.

### 📁 설정 파일 목록

| 파일 | 역할 | 비유 |
|------|------|------|
| `.env` | 비밀번호와 API 키 관리 | 비밀번호 메모장 |
| `agent_profiles.yaml` | 참여자 정보 설정 | 참여자 명단 |
| `agendas.yaml` | 회의 안건 목록 | 회의 주제 목록 |
| `mcp_servers.json` | 외부 도구 연결 설정 | 도구함 목록 |

> 💡 **쉽게 말하면...**
> 설정 파일은 Doorae의 조정 손잡이예요. 코드를 수정하지 않고도 참여자, 안건, 도구를 바꿀 수 있어요.

---

## .env 파일 (비밀번호 메모장)

### 🔐 역할

**비유**: 비밀번호 메모장

**저장하는 내용**
- AI 서비스 API 키 (출입증)
- GitHub 접근 토큰
- 회의 설정값
- 비밀로 유지해야 하는 정보

### 주요 설정 항목

#### AI 기본 설정

**공통 API 키 (필수)**
```
OPENAI_API_KEY=sk-your-key-here
```
- 대화용 AI와 분석용 AI가 공통으로 사용해요
- 없으면 Doorae이 실행되지 않아요

**서비스 주소 (선택)**
```
OPENAI_BASE_URL=https://api.openai.com/v1
```
- OpenAI가 아닌 다른 서비스를 쓸 때 필요해요
- 예: OpenRouter, Azure OpenAI

#### 대화용 AI 설정

**전용 API 키 (선택)**
```
LLM_MAIN_API_KEY=sk-main-key
```
- 없으면 OPENAI_API_KEY를 사용해요

**모델 이름**
```
LLM_MAIN_MODEL=gpt-4o-mini
```
- 기본값: gpt-4o-mini
- 다른 모델: deepseek-v3.2, gpt-4o 등

**창의성 조절**
```
LLM_MAIN_TEMPERATURE=0.7
```
- 0.7: 창의적 (기본값)
- 0.0: 일관적
- 1.0: 매우 창의적

**최대 글자 수**
```
LLM_MAIN_MAX_TOKENS=4096
```
- 발언 길이 제한
- 기본값: 4096 (충분함)

#### 분석용 AI 설정

**전용 API 키 (선택)**
```
LLM_TASK_API_KEY=sk-task-key
```

**모델 이름**
```
LLM_TASK_MODEL=gpt-4o-mini
```
- 기본값: gpt-4o-mini
- 저렴한 모델: gemini-2.5-flash

**창의성 조절**
```
LLM_TASK_TEMPERATURE=0.0
```
- 항상 0.0으로 설정 (일관성 중요)

**최대 글자 수**
```
LLM_TASK_MAX_TOKENS=2048
```
- 짧은 답변만 필요
- 기본값: 2048

#### 회의 안전 설정

**최대 턴 수**
```
MAX_TURNS=1000
```
- 회의가 너무 길어지면 자동 종료
- 기본값: 1000번

**대화 요약 시점**
```
MAX_MESSAGES_BEFORE_SUMMARY=5
```
- 메시지 몇 개부터 요약할지
- 기본값: 5개

#### GitHub 도구 설정

**접근 토큰 (MCP 사용 시 필수)**
```
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_token
```
- GitHub 도구를 쓰려면 필요해요
- GitHub 설정에서 만들 수 있어요

> 🤔 **이해했나요?**
> Q: API 키를 2개 설정하면 뭐가 좋아요?
> A: 대화용은 좋은 AI, 분석용은 저렴한 AI를 써서 비용을 70% 절약할 수 있어요.

---

## agent_profiles.yaml (참여자 명단)

### 👥 역할

**비유**: 참여자 명단

**정의하는 내용**
- 참여자 이름
- 역할과 책임
- 전문 분야
- 사용할 도구
- 추가 지시사항

### 기본 구조

```
참여자:
  이름: Host
  역할: 회의 진행자
  책임:
    - 회의 시작
    - 안건 소개
    - 발언 기회 조정
    - 회의 마무리
  전문성:
    - 회의 진행
    - 시간 관리
  사용 도구:
    - github
  추가 정보:
    저장소: doorae-lab/doorae
```

### 필수 항목

**이름 (name)**
- 참여자를 부르는 이름이에요
- 유일해야 해요 (중복 불가)
- 예: Host, PM, TechLead

**역할 (role)**
- 참여자의 직책이나 역할이에요
- 예: host, project_manager, tech_lead

**책임 (responsibilities)**
- 참여자가 해야 할 일 목록이에요
- 최소 1개 이상 필요해요

**전문성 (expertise)**
- 참여자가 잘하는 분야예요
- 최소 1개 이상 필요해요

### 선택 항목

**사용 도구 (mcp_tools)**
- 이 참여자가 쓸 외부 도구예요
- 예: github, jira, slack

**추가 정보 (metadata)**
- 도구 사용에 필요한 정보예요
- 예: GitHub 저장소 이름

**추가 지시사항 (additional_instructions)**
- 참여자에게 특별히 시킬 일이에요
- 예: "GitHub 도구를 적극 사용하세요"

**에이전트별 LLM 설정 (llm)**
- 특정 참여자만 다른 모델/provider를 쓰고 싶을 때 사용해요
- 지정한 필드만 덮어쓰고 나머지는 `.env` 전역 `LLM_MAIN_*` 값으로 자동 fallback 돼요
- 설정 가능 필드: `model`, `api_key`, `base_url`, `temperature`, `max_tokens`

예시:
```yaml
- name: PM
  role: project_manager
  responsibilities: [프로젝트 일정 관리]
  expertise: [일정 계획]
  llm:
    model: "openai/gpt-4.1-mini"
    temperature: 0.2
    max_tokens: 1200
```

### 예시: Host 참여자

```
이름: Host
역할: host
책임:
  - 회의 시작 인사
  - 안건 소개
  - 발언자 지정
  - 회의 정리
전문성:
  - 회의 진행
  - 의견 조율
사용 도구:
  - github
추가 정보:
  저장소: doorae-lab/doorae
  추가 지시사항: |
    GitHub 이슈와 PR 상태를 자주 확인하세요.
    데이터 기반으로 발언하세요.
```

> 💡 **쉽게 말하면...**
> 참여자 명단은 "누가, 무슨 역할을, 어떤 도구로 하는지" 정리한 목록이에요. 여기에 새 참여자를 추가하면 회의에 바로 참여할 수 있어요.

---

## agendas.yaml (회의 주제 목록)

### 📝 역할

**비유**: 회의 주제 목록

**정의하는 내용**
- 안건 제목
- 안건 설명
- 필수 발언자

### 기본 구조

```
안건:
  - 제목: 프로젝트 현황 공유
    설명: 현재 진행 상황과 이슈를 공유합니다
    필수 발언자:
      - PM
      - TechLead

  - 제목: 다음 주 계획
    설명: 다음 주 일정을 수립합니다
    필수 발언자:
      - PM
```

### 필수 항목

**제목 (title)**
- 안건의 제목이에요
- 짧고 명확하게 써요
- 예: "프로젝트 현황 공유"

**설명 (description)**
- 안건의 자세한 내용이에요
- 무엇을 논의할지 설명해요

### 선택 항목

**필수 발언자 (required_speakers)**
- 이 안건에서 꼭 말해야 하는 사람이에요
- 없으면 모든 참여자에게 기회가 가요
- 예: PM, TechLead

### 안건 추가 방법

1. `config/agendas.yaml` 파일을 열어요
2. 제일 아래에 새 안건을 추가해요
3. 제목, 설명, 필수 발언자를 적어요
4. 저장하고 Doorae을 실행해요

> 🤔 **이해했나요?**
> Q: 필수 발언자를 안 정하면 어떻게 되나요?
> A: 모든 참여자가 발언 기회를 가져요. Host가 누구에게 물어볼지 자유롭게 정해요.

---

## mcp_servers.json (도구함 목록)

### 🛠️ 역할

**비유**: 도구함 목록

**정의하는 내용**
- 어떤 외부 도구를 사용할지
- 도구에 어떻게 접속할지
- 필요한 비밀번호는 무엇인지

### GitHub 설정 예시

```
도구 서버:
  github:
    실행 명령: go
    명령 인자:
      - run
      - github.com/github/github-mcp-server/cmd/github-mcp-server@latest
      - stdio
    환경 변수:
      GITHUB_PERSONAL_ACCESS_TOKEN: ${GITHUB_PERSONAL_ACCESS_TOKEN}
```

### 구성 요소

**서버 이름**
- 도구의 이름이에요
- 예: github, jira, slack

**실행 명령 (command)**
- 도구를 실행하는 명령어예요
- 예: go, python, npx

**명령 인자 (args)**
- 명령어 뒤에 붙는 옵션이에요

**환경 변수 (env)**
- 도구가 필요로 하는 비밀번호예요
- `${변수명}` 형식으로 .env에서 가져와요

### 새 도구 추가 예시

**Jira 추가**
```
도구 서버:
  github: (기존)
  jira:
    실행 명령: npx
    명령 인자:
      - jira-mcp-server
    환경 변수:
      JIRA_API_TOKEN: ${JIRA_API_TOKEN}
      JIRA_DOMAIN: ${JIRA_DOMAIN}
```

**Slack 추가 (HTTP 방식)**
```
도구 서버:
  slack:
    주소: https://slack-mcp.example.com
    전송 방식: streamable_http
    헤더:
      Authorization: Bearer ${SLACK_BOT_TOKEN}
```

> 💡 **쉽게 말하면...**
> 도구함 목록은 "어떤 도구를 어떻게 연결할지" 정리한 파일이에요. 새 도구를 추가하려면 이 파일에 정보를 적으면 돼요.

---

## 추천 설정

### 초보자용 (간단함)

**목표**: 빠르게 시작하기

**.env 파일**
```
OPENAI_API_KEY=sk-your-key
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your-token
```

**특징**
- 최소한의 설정만 해요
- OpenAI 하나로 모든 AI 사용
- 빠르게 테스트할 수 있어요

---

### 중급자용 (비용 절약)

**목표**: 비용 70% 절약하기

**.env 파일**
```
OPENAI_API_KEY=your-openrouter-key
OPENAI_BASE_URL=https://openrouter.ai/api/v1

LLM_MAIN_MODEL=deepseek/deepseek-v3.2
LLM_TASK_MODEL=google/gemini-2.5-flash

GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your-token
```

**특징**
- OpenRouter로 저렴한 모델 사용
- 대화용은 품질 좋은 모델
- 분석용은 빠르고 저렴한 모델

---

### 고급자용 (최대 절약)

**목표**: 여러 서비스 조합으로 최저 비용

**.env 파일**
```
# 대화용: OpenRouter
LLM_MAIN_API_KEY=your-openrouter-key
LLM_MAIN_BASE_URL=https://openrouter.ai/api/v1
LLM_MAIN_MODEL=deepseek/deepseek-v3.2

# 분석용: Azure OpenAI
LLM_TASK_API_KEY=your-azure-key
LLM_TASK_BASE_URL=https://your-azure.openai.azure.com
LLM_TASK_MODEL=gpt-35-turbo

GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your-token
```

**특징**
- 각 AI를 다른 서비스로 사용
- 최저 비용 조합
- 복잡하지만 비용 최소화

---

## 설정 변경 시 주의사항

### ⚠️ 주의할 점

**API 키는 비밀로**
- .env 파일을 다른 사람과 공유하지 마세요
- GitHub에 올리지 마세요
- `.gitignore`에 추가되어 있는지 확인하세요

**설정 파일 형식**
- YAML 파일은 들여쓰기가 중요해요
- 공백 2개 또는 4개로 일관성 있게 써요
- 탭 대신 공백을 사용해요

**변경 후 재시작**
- 설정을 바꾸면 Doorae을 다시 실행해야 해요
- 실행 중에는 반영되지 않아요

**참여자 이름 일치**
- agendas.yaml의 필수 발언자 이름
- agent_profiles.yaml의 참여자 이름
- 정확히 같아야 해요 (대소문자 구분)

> 🤔 **이해했나요?**
> Q: 설정을 바꾸면 바로 적용되나요?
> A: 아니요. Doorae을 종료하고 다시 실행해야 새 설정이 적용돼요.

---

## 문제 해결

### API 키 오류

**증상**: "API key is required" 에러

**해결**
1. .env 파일이 프로젝트 루트에 있는지 확인
2. OPENAI_API_KEY가 설정되어 있는지 확인
3. API 키 앞뒤에 공백이 없는지 확인

---

### GitHub 도구 오류

**증상**: "github 서버 건너뜀" 경고

**해결**
1. .env에 GITHUB_PERSONAL_ACCESS_TOKEN 확인
2. GitHub에서 토큰을 만들었는지 확인
3. 토큰 권한(repo, issues)이 있는지 확인

---

### 참여자 없음 오류

**증상**: "Agent not found" 에러

**해결**
1. agent_profiles.yaml에 참여자가 있는지 확인
2. 이름 철자가 정확한지 확인
3. YAML 형식이 올바른지 확인

---

### 안건 진행 안 됨

**증상**: 안건이 시작되지 않음

**해결**
1. agendas.yaml에 안건이 있는지 확인
2. 필수 발언자 이름이 정확한지 확인
3. YAML 형식이 올바른지 확인

---

> 💡 **핵심 정리**
>
> - 4개 설정 파일: .env, agent_profiles.yaml, agendas.yaml, mcp_servers.json
> - .env는 비밀번호 메모장 (API 키 저장)
> - agent_profiles.yaml은 참여자 명단
> - agendas.yaml은 회의 주제 목록
> - mcp_servers.json은 도구함 목록
> - 설정 변경 후에는 반드시 재시작

---

## 다음 문서

- [future-direction.md](./future-direction.md): 앞으로 추가될 기능을 알아봐요
- [roadmap.md](./roadmap.md): 개발 일정과 계획을 확인해요
