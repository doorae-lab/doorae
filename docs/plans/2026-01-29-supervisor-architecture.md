# Supervisor 중심 아키텍처 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** thetable-poc의 Phase-as-Node 구조를 개선하여, Supervisor 패턴 기반의 Agent 중심 회의 시스템을 처음부터 구축

**Architecture:**
- Supervisor (Host Agent)가 phase를 보고 적절한 Agent에게 멘션을 걸어 발언 요청
- 각 Agent는 독립된 노드로 구성되며, 자신의 역할/책임에 맞게 응답
- Phase는 State로만 관리하며, Phase Controller가 명확한 전환 규칙 적용

**Tech Stack:**
- LangGraph (StateGraph, Checkpointer)
- LangChain (ChatOpenAI, Messages)
- Pydantic (Data validation)
- pytest (Testing)
- YAML (Agent profiles)

---

## Task 1: 프로젝트 기본 설정

**Files:**
- Create: `pyproject.toml`
- Create: `thetable/__init__.py`
- Create: `tests/__init__.py`
- Create: `README.md`

**Step 1: Write project configuration test**

```python
# tests/test_project_setup.py
def test_project_structure():
    """프로젝트 기본 구조 확인"""
    import thetable
    assert hasattr(thetable, '__version__')
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_project_setup.py -v`
Expected: FAIL - "ModuleNotFoundError: No module named 'thetable'"

**Step 3: Create project structure**

```toml
# pyproject.toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "thetable"
version = "0.1.0"
description = "AI-powered team meeting system with supervisor architecture"
requires-python = ">=3.10"
dependencies = [
    "langgraph>=0.2.0",
    "langchain>=0.3.0",
    "langchain-openai>=0.2.0",
    "pydantic>=2.0.0",
    "pyyaml>=6.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-mock>=3.12.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

```python
# thetable/__init__.py
"""TheTable - Supervisor 기반 AI 회의 시스템"""

__version__ = "0.1.0"
```

```python
# tests/__init__.py
"""Test package"""
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_project_setup.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pyproject.toml thetable/__init__.py tests/__init__.py
git commit -m "feat: initialize project structure with pyproject.toml"
```

---

## Task 2: Agent Profile 시스템

**Files:**
- Create: `thetable/core/profile.py`
- Create: `config/agent_profiles.yaml`
- Create: `tests/core/test_profile.py`

**Step 1: Write the failing test**

```python
# tests/core/test_profile.py
import pytest
from thetable.core.profile import AgentProfile, load_agent_profiles


def test_agent_profile_creation():
    """Agent Profile 생성 테스트"""
    profile = AgentProfile(
        name="PM",
        role="project_manager",
        responsibilities=["프로젝트 일정 관리", "진행 상황 보고"],
        expertise=["일정 계획", "자원 관리"],
        phase_triggers={"status_check": "자동 발언"}
    )

    assert profile.name == "PM"
    assert profile.role == "project_manager"
    assert len(profile.responsibilities) == 2
    assert "status_check" in profile.phase_triggers


def test_load_agent_profiles_from_yaml():
    """YAML에서 Agent Profile 로드 테스트"""
    profiles = load_agent_profiles("config/agent_profiles.yaml")

    assert "PM" in profiles
    assert "TechLead" in profiles
    assert profiles["PM"].role == "project_manager"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_profile.py -v`
Expected: FAIL - "ModuleNotFoundError: No module named 'thetable.core.profile'"

**Step 3: Write minimal implementation**

```python
# thetable/core/__init__.py
"""Core components"""
```

```python
# thetable/core/profile.py
"""Agent profile system"""
from typing import Dict, List
from pydantic import BaseModel
import yaml


class AgentProfile(BaseModel):
    """Agent의 역할, 책임, 전문성 정의"""
    name: str
    role: str
    responsibilities: List[str]
    expertise: List[str]
    phase_triggers: Dict[str, str] = {}

    def matches_phase(self, phase: str) -> bool:
        """특정 phase에서 자동 발언해야 하는지 확인"""
        return phase in self.phase_triggers


def load_agent_profiles(yaml_path: str) -> Dict[str, AgentProfile]:
    """YAML 파일에서 Agent Profile 로드"""
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    profiles = {}
    for agent_data in data.get('agents', []):
        profile = AgentProfile(**agent_data)
        profiles[profile.name] = profile

    return profiles
```

```yaml
# config/agent_profiles.yaml
agents:
  - name: PM
    role: project_manager
    responsibilities:
      - 프로젝트 일정 관리
      - 진행 상황 보고
      - 리스크 식별
    expertise:
      - 일정 계획
      - 자원 관리
    phase_triggers:
      status_check: "프로젝트 현황을 보고하세요"

  - name: TechLead
    role: tech_lead
    responsibilities:
      - 기술 의사결정
      - 아키텍처 설계
      - 코드 리뷰
    expertise:
      - 시스템 설계
      - 성능 최적화
    phase_triggers:
      issue_resolution: "기술적 해결 방안을 제시하세요"

  - name: Designer
    role: designer
    responsibilities:
      - UI/UX 설계
      - 사용자 경험 개선
    expertise:
      - 인터페이스 디자인
      - 사용성 테스트
    phase_triggers: {}
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_profile.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add thetable/core/profile.py config/agent_profiles.yaml tests/core/test_profile.py
git commit -m "feat: implement agent profile system with YAML loader"
```

---

## Task 3: State 정의

**Files:**
- Create: `thetable/graph/state.py`
- Create: `tests/graph/test_state.py`

**Step 1: Write the failing test**

```python
# tests/graph/test_state.py
from thetable.graph.state import MeetingState, AgentInfo


def test_agent_info_creation():
    """AgentInfo 생성 테스트"""
    agent = AgentInfo(
        name="PM",
        role="project_manager",
        profile_key="PM"
    )

    assert agent.name == "PM"
    assert agent.role == "project_manager"


def test_meeting_state_structure():
    """MeetingState 구조 테스트"""
    from typing import get_type_hints
    hints = get_type_hints(MeetingState)

    assert 'messages' in hints
    assert 'current_phase' in hints
    assert 'agents' in hints
    assert 'next_speaker' in hints
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/graph/test_state.py -v`
Expected: FAIL - "ModuleNotFoundError: No module named 'thetable.graph.state'"

**Step 3: Write minimal implementation**

```python
# thetable/graph/__init__.py
"""Graph components for workflow"""
```

```python
# thetable/graph/state.py
"""Meeting state definition"""
from typing import Annotated, List, Optional, Dict, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from pydantic import BaseModel


class AgentInfo(BaseModel):
    """Agent 기본 정보"""
    name: str
    role: str
    profile_key: str  # agent_profiles.yaml의 키


class MeetingState(TypedDict):
    """회의 상태"""

    # 대화 히스토리 (자동 누적)
    messages: Annotated[List[BaseMessage], add_messages]

    # Phase 관리
    current_phase: str  # "opening", "status_check", "issue_resolution", "closing"
    phase_history: List[str]  # Phase 전환 이력

    # Agent 관리
    agents: List[AgentInfo]
    next_speaker: Optional[str]  # 다음 발언자 이름
    current_task: Optional[str]  # Supervisor가 부여한 task

    # 발언 추적
    speaker_counts: Dict[str, int]
    pending_mentions: List[str]

    # Phase 제약
    phase_required_speakers: Dict[str, List[str]]  # Phase별 필수 발언자
    phase_goals: Dict[str, str]  # Phase별 목표

    # 메타데이터
    start_time: float
    phase_start_time: float
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/graph/test_state.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add thetable/graph/state.py tests/graph/test_state.py
git commit -m "feat: define MeetingState with TypedDict and AgentInfo"
```

---

## Task 4: Base Agent 구현

**Files:**
- Create: `thetable/agents/base_agent.py`
- Create: `tests/agents/test_base_agent.py`

**Step 1: Write the failing test**

```python
# tests/agents/test_base_agent.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from thetable.agents.base_agent import BaseAgent
from thetable.core.profile import AgentProfile


@pytest.fixture
def mock_llm():
    """Mock LLM"""
    llm = AsyncMock()
    llm.ainvoke = AsyncMock(return_value=MagicMock(content="Test response"))
    return llm


@pytest.fixture
def agent_profile():
    """Test agent profile"""
    return AgentProfile(
        name="TestAgent",
        role="tester",
        responsibilities=["테스트 수행"],
        expertise=["테스트 자동화"]
    )


@pytest.mark.asyncio
async def test_base_agent_generate_response(mock_llm, agent_profile):
    """BaseAgent 응답 생성 테스트"""
    agent = BaseAgent(
        name="TestAgent",
        profile=agent_profile,
        llm=mock_llm
    )

    context = {
        "phase": "status_check",
        "task": "현황을 보고하세요",
        "recent_messages": []
    }

    response = await agent.generate_response(context)

    assert response == "Test response"
    assert mock_llm.ainvoke.called
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/agents/test_base_agent.py -v`
Expected: FAIL - "ModuleNotFoundError: No module named 'thetable.agents.base_agent'"

**Step 3: Write minimal implementation**

```python
# thetable/agents/__init__.py
"""Agent implementations"""
```

```python
# thetable/agents/base_agent.py
"""Base agent with LLM integration"""
from typing import Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from thetable.core.profile import AgentProfile


class BaseAgent:
    """기본 Agent 클래스"""

    def __init__(
        self,
        name: str,
        profile: AgentProfile,
        llm: Optional[ChatOpenAI] = None,
    ):
        self.name = name
        self.profile = profile
        self._llm = llm or self._init_default_llm()

    def _init_default_llm(self) -> ChatOpenAI:
        """기본 LLM 초기화"""
        return ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7
        )

    def _build_system_prompt(self) -> str:
        """시스템 프롬프트 생성"""
        return f"""You are {self.name}, a {self.profile.role}.

Your responsibilities:
{chr(10).join(f'- {r}' for r in self.profile.responsibilities)}

Your expertise:
{chr(10).join(f'- {e}' for e in self.profile.expertise)}

Respond according to your role and the given task.
"""

    def _build_user_prompt(self, context: Dict[str, Any]) -> str:
        """사용자 프롬프트 생성"""
        parts = []

        if "phase" in context:
            parts.append(f"Current phase: {context['phase']}")

        if "task" in context:
            parts.append(f"\nTask: {context['task']}")

        if "recent_messages" in context and context["recent_messages"]:
            parts.append("\nRecent conversation:")
            for msg in context["recent_messages"][-5:]:
                parts.append(f"{msg.name}: {msg.content}")

        return "\n".join(parts)

    async def generate_response(self, context: Dict[str, Any]) -> str:
        """응답 생성"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self._build_system_prompt()),
            ("human", self._build_user_prompt(context))
        ])

        chain = prompt | self._llm | StrOutputParser()
        response = await chain.ainvoke({})

        return response
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/agents/test_base_agent.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add thetable/agents/base_agent.py tests/agents/test_base_agent.py
git commit -m "feat: implement BaseAgent with LLM integration"
```

---

## Task 5: Supervisor Agent 구현

**Files:**
- Create: `thetable/agents/supervisor.py`
- Create: `tests/agents/test_supervisor.py`

**Step 1: Write the failing test**

```python
# tests/agents/test_supervisor.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from thetable.agents.supervisor import SupervisorAgent
from thetable.core.profile import AgentProfile


@pytest.fixture
def mock_llm():
    """Mock LLM that returns orchestration decision"""
    llm = AsyncMock()
    response = MagicMock()
    response.content = '{"next_speaker": "PM", "task": "@PM 현황을 보고하세요", "reason": "status_check phase이므로"}'
    llm.ainvoke = AsyncMock(return_value=response)
    return llm


@pytest.fixture
def supervisor_profile():
    """Supervisor profile"""
    return AgentProfile(
        name="Host",
        role="host",
        responsibilities=["회의 진행", "발언자 선택"],
        expertise=["회의 조율"]
    )


@pytest.fixture
def agent_profiles_dict():
    """Agent profiles for context"""
    return {
        "PM": AgentProfile(
            name="PM",
            role="project_manager",
            responsibilities=["프로젝트 관리"],
            expertise=["일정 계획"]
        ),
        "TechLead": AgentProfile(
            name="TechLead",
            role="tech_lead",
            responsibilities=["기술 의사결정"],
            expertise=["시스템 설계"]
        )
    }


@pytest.mark.asyncio
async def test_supervisor_select_next_speaker(
    mock_llm,
    supervisor_profile,
    agent_profiles_dict
):
    """Supervisor가 다음 발언자 선택 테스트"""
    supervisor = SupervisorAgent(
        name="Host",
        profile=supervisor_profile,
        llm=mock_llm
    )

    context = {
        "current_phase": "status_check",
        "recent_messages": [],
        "agent_profiles": agent_profiles_dict,
        "candidates": ["PM", "TechLead"]
    }

    decision = await supervisor.select_next_speaker(context)

    assert decision["next_speaker"] == "PM"
    assert "@PM" in decision["task"]
    assert "reason" in decision
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/agents/test_supervisor.py -v`
Expected: FAIL - "ModuleNotFoundError: No module named 'thetable.agents.supervisor'"

**Step 3: Write minimal implementation**

```python
# thetable/agents/supervisor.py
"""Supervisor agent for orchestration"""
import json
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from thetable.agents.base_agent import BaseAgent


class SupervisorAgent(BaseAgent):
    """회의 진행을 조율하는 Supervisor Agent"""

    def _format_agent_profiles(self, profiles: Dict[str, Any]) -> str:
        """Agent profile 정보를 포맷팅"""
        lines = []
        for name, profile in profiles.items():
            lines.append(f"\n{name} ({profile.role}):")
            lines.append(f"  Responsibilities: {', '.join(profile.responsibilities)}")
            lines.append(f"  Expertise: {', '.join(profile.expertise)}")
        return "\n".join(lines)

    async def select_next_speaker(self, context: Dict[str, Any]) -> Dict[str, str]:
        """다음 발언자 선택 및 task 부여"""
        phase = context.get("current_phase", "")
        agent_profiles = context.get("agent_profiles", {})
        candidates = context.get("candidates", [])
        recent_messages = context.get("recent_messages", [])

        prompt_text = f"""You are the meeting host/supervisor.

Current phase: {phase}

Available participants:
{self._format_agent_profiles(agent_profiles)}

Candidates: {', '.join(candidates)}

Recent conversation:
{self._format_recent_messages(recent_messages)}

Based on the current phase, decide:
1. Who should speak next? (select from candidates, or 'FINISH' to complete phase)
2. What specific task/question should you give them?
3. Why did you select them?

Respond in JSON format:
{{
    "next_speaker": "name or FINISH",
    "task": "@name specific task here",
    "reason": "explanation"
}}
"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", self._build_system_prompt()),
            ("human", prompt_text)
        ])

        chain = prompt | self._llm | StrOutputParser()
        response = await chain.ainvoke({})

        # Parse JSON response
        try:
            decision = json.loads(response)
        except json.JSONDecodeError:
            # Fallback to first candidate
            decision = {
                "next_speaker": candidates[0] if candidates else "FINISH",
                "task": f"@{candidates[0]} Please share your thoughts",
                "reason": "JSON parsing failed, fallback to first candidate"
            }

        return decision

    def _format_recent_messages(self, messages) -> str:
        """최근 메시지 포맷팅"""
        if not messages:
            return "(No messages yet)"

        lines = []
        for msg in messages[-5:]:
            name = getattr(msg, 'name', 'Unknown')
            content = getattr(msg, 'content', '')
            lines.append(f"{name}: {content}")
        return "\n".join(lines)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/agents/test_supervisor.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add thetable/agents/supervisor.py tests/agents/test_supervisor.py
git commit -m "feat: implement SupervisorAgent for orchestration"
```

---

## Task 6: Workflow 노드 - Supervisor 노드

**Files:**
- Create: `thetable/graph/nodes.py`
- Create: `tests/graph/test_nodes.py`

**Step 1: Write the failing test**

```python
# tests/graph/test_nodes.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from thetable.graph.nodes import supervisor_node
from thetable.graph.state import MeetingState, AgentInfo


@pytest.fixture
def mock_supervisor():
    """Mock supervisor agent"""
    supervisor = MagicMock()
    supervisor.select_next_speaker = AsyncMock(return_value={
        "next_speaker": "PM",
        "task": "@PM 현황을 보고하세요",
        "reason": "status_check phase"
    })
    return supervisor


@pytest.fixture
def meeting_state():
    """Test meeting state"""
    return {
        "messages": [],
        "current_phase": "status_check",
        "agents": [
            AgentInfo(name="PM", role="project_manager", profile_key="PM"),
            AgentInfo(name="TechLead", role="tech_lead", profile_key="TechLead")
        ],
        "next_speaker": None,
        "current_task": None,
        "speaker_counts": {},
        "pending_mentions": [],
        "phase_required_speakers": {},
        "phase_goals": {},
        "start_time": 0.0,
        "phase_start_time": 0.0,
        "phase_history": []
    }


@pytest.mark.asyncio
async def test_supervisor_node(mock_supervisor, meeting_state, monkeypatch):
    """Supervisor 노드 실행 테스트"""
    # Mock get_supervisor to return our mock
    monkeypatch.setattr(
        "thetable.graph.nodes.get_supervisor",
        lambda state: mock_supervisor
    )

    result = await supervisor_node(meeting_state)

    assert result["next_speaker"] == "PM"
    assert "@PM" in result["current_task"]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/graph/test_nodes.py -v`
Expected: FAIL - "ModuleNotFoundError: No module named 'thetable.graph.nodes'"

**Step 3: Write minimal implementation**

```python
# thetable/graph/nodes.py
"""Workflow nodes"""
from typing import Dict, Any
from langchain_core.messages import AIMessage, HumanMessage

from thetable.graph.state import MeetingState
from thetable.agents.supervisor import SupervisorAgent
from thetable.core.profile import load_agent_profiles


# Global cache for agents
_supervisor_cache = None
_agent_profiles_cache = None


def get_supervisor(state: MeetingState) -> SupervisorAgent:
    """Supervisor Agent 가져오기 (캐싱)"""
    global _supervisor_cache, _agent_profiles_cache

    if _supervisor_cache is None:
        if _agent_profiles_cache is None:
            _agent_profiles_cache = load_agent_profiles("config/agent_profiles.yaml")

        # Host profile (supervisor)
        host_profile = _agent_profiles_cache.get("Host")
        if host_profile is None:
            from thetable.core.profile import AgentProfile
            host_profile = AgentProfile(
                name="Host",
                role="host",
                responsibilities=["회의 진행", "발언자 선택"],
                expertise=["회의 조율"]
            )

        _supervisor_cache = SupervisorAgent(
            name="Host",
            profile=host_profile
        )

    return _supervisor_cache


async def supervisor_node(state: MeetingState) -> Dict[str, Any]:
    """Supervisor가 다음 발언자 선택"""
    supervisor = get_supervisor(state)

    # 후보자 목록 (Host 제외)
    candidates = [agent.name for agent in state["agents"] if agent.name != "Host"]

    # Agent profiles 로드
    global _agent_profiles_cache
    if _agent_profiles_cache is None:
        _agent_profiles_cache = load_agent_profiles("config/agent_profiles.yaml")

    context = {
        "current_phase": state["current_phase"],
        "recent_messages": state["messages"],
        "agent_profiles": _agent_profiles_cache,
        "candidates": candidates,
        "speaker_counts": state.get("speaker_counts", {}),
        "pending_mentions": state.get("pending_mentions", [])
    }

    decision = await supervisor.select_next_speaker(context)

    return {
        "next_speaker": decision["next_speaker"],
        "current_task": decision["task"]
    }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/graph/test_nodes.py::test_supervisor_node -v`
Expected: PASS

**Step 5: Commit**

```bash
git add thetable/graph/nodes.py tests/graph/test_nodes.py
git commit -m "feat: implement supervisor_node for speaker selection"
```

---

## Task 7: Workflow 노드 - Agent 노드

**Files:**
- Modify: `thetable/graph/nodes.py`
- Modify: `tests/graph/test_nodes.py`

**Step 1: Write the failing test**

```python
# tests/graph/test_nodes.py (추가)
@pytest.fixture
def mock_agent():
    """Mock agent"""
    agent = MagicMock()
    agent.name = "PM"
    agent.generate_response = AsyncMock(return_value="프로젝트 진행 중입니다")
    return agent


@pytest.mark.asyncio
async def test_agent_node_factory(mock_agent, meeting_state, monkeypatch):
    """Agent 노드 팩토리 테스트"""
    from thetable.graph.nodes import create_agent_node

    # Mock get_agent
    monkeypatch.setattr(
        "thetable.graph.nodes.get_agent",
        lambda state, name: mock_agent
    )

    # Create agent node
    pm_node = create_agent_node("PM")

    # Set task in state
    meeting_state["current_task"] = "@PM 현황을 보고하세요"

    result = await pm_node(meeting_state)

    assert "messages" in result
    assert len(result["messages"]) == 1
    assert result["messages"][0].name == "PM"
    assert result["messages"][0].content == "프로젝트 진행 중입니다"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/graph/test_nodes.py::test_agent_node_factory -v`
Expected: FAIL - "ImportError: cannot import name 'create_agent_node'"

**Step 3: Write minimal implementation**

```python
# thetable/graph/nodes.py (추가)
from thetable.agents.base_agent import BaseAgent


# Agent cache
_agents_cache: Dict[str, BaseAgent] = {}


def get_agent(state: MeetingState, agent_name: str) -> BaseAgent:
    """Agent 가져오기 (캐싱)"""
    global _agents_cache, _agent_profiles_cache

    if agent_name not in _agents_cache:
        if _agent_profiles_cache is None:
            _agent_profiles_cache = load_agent_profiles("config/agent_profiles.yaml")

        profile = _agent_profiles_cache.get(agent_name)
        if profile is None:
            raise ValueError(f"Profile not found for agent: {agent_name}")

        _agents_cache[agent_name] = BaseAgent(
            name=agent_name,
            profile=profile
        )

    return _agents_cache[agent_name]


def create_agent_node(agent_name: str):
    """Agent 노드 생성 팩토리"""
    async def agent_node(state: MeetingState) -> Dict[str, Any]:
        """Agent가 발언"""
        agent = get_agent(state, agent_name)

        context = {
            "phase": state["current_phase"],
            "task": state.get("current_task", ""),
            "recent_messages": state["messages"]
        }

        response = await agent.generate_response(context)

        # 발언 횟수 업데이트
        speaker_counts = state.get("speaker_counts", {}).copy()
        speaker_counts[agent_name] = speaker_counts.get(agent_name, 0) + 1

        return {
            "messages": [AIMessage(content=response, name=agent_name)],
            "speaker_counts": speaker_counts
        }

    return agent_node
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/graph/test_nodes.py::test_agent_node_factory -v`
Expected: PASS

**Step 5: Commit**

```bash
git add thetable/graph/nodes.py tests/graph/test_nodes.py
git commit -m "feat: implement create_agent_node factory for agent nodes"
```

---

## Task 8: Phase Controller

**Files:**
- Create: `thetable/graph/phase_controller.py`
- Create: `tests/graph/test_phase_controller.py`

**Step 1: Write the failing test**

```python
# tests/graph/test_phase_controller.py
from thetable.graph.phase_controller import PhaseController, should_transition_phase


def test_phase_controller_initialization():
    """PhaseController 초기화 테스트"""
    controller = PhaseController()

    assert controller.current_phase == "opening"
    assert "status_check" in controller.phase_sequence


def test_should_transition_phase_required_speakers():
    """필수 발언자 완료 시 phase 전환 테스트"""
    state = {
        "current_phase": "status_check",
        "speaker_counts": {"PM": 1, "TechLead": 1},
        "phase_required_speakers": {
            "status_check": ["PM", "TechLead"]
        }
    }

    assert should_transition_phase(state) is True


def test_should_transition_phase_not_all_spoke():
    """필수 발언자 미완료 시 phase 전환 안 함"""
    state = {
        "current_phase": "status_check",
        "speaker_counts": {"PM": 1},
        "phase_required_speakers": {
            "status_check": ["PM", "TechLead"]
        }
    }

    assert should_transition_phase(state) is False
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/graph/test_phase_controller.py -v`
Expected: FAIL - "ModuleNotFoundError: No module named 'thetable.graph.phase_controller'"

**Step 3: Write minimal implementation**

```python
# thetable/graph/phase_controller.py
"""Phase transition control"""
from typing import List, Dict, Any


class PhaseController:
    """Phase 전환 제어"""

    def __init__(self):
        self.phase_sequence = [
            "opening",
            "status_check",
            "issue_resolution",
            "closing"
        ]
        self.current_phase = "opening"

    def get_next_phase(self, current_phase: str) -> str:
        """다음 phase 가져오기"""
        try:
            idx = self.phase_sequence.index(current_phase)
            if idx + 1 < len(self.phase_sequence):
                return self.phase_sequence[idx + 1]
        except ValueError:
            pass
        return "closing"  # Default to closing if unknown


def should_transition_phase(state: Dict[str, Any]) -> bool:
    """Phase 전환 조건 확인"""
    current_phase = state["current_phase"]
    speaker_counts = state.get("speaker_counts", {})
    required_speakers = state.get("phase_required_speakers", {}).get(current_phase, [])

    # 필수 발언자가 없으면 전환 가능
    if not required_speakers:
        return True

    # 모든 필수 발언자가 발언했는지 확인
    for speaker in required_speakers:
        if speaker_counts.get(speaker, 0) == 0:
            return False

    return True
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/graph/test_phase_controller.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add thetable/graph/phase_controller.py tests/graph/test_phase_controller.py
git commit -m "feat: implement PhaseController with transition rules"
```

---

## Task 9: Workflow 구성

**Files:**
- Create: `thetable/graph/workflow.py`
- Create: `tests/graph/test_workflow.py`

**Step 1: Write the failing test**

```python
# tests/graph/test_workflow.py
import pytest
from thetable.graph.workflow import create_workflow


def test_create_workflow():
    """Workflow 생성 테스트"""
    workflow = create_workflow(agent_names=["PM", "TechLead"])

    assert workflow is not None
    # LangGraph app has nodes
    assert hasattr(workflow, 'nodes')


def test_workflow_has_required_nodes():
    """필수 노드 존재 확인"""
    workflow = create_workflow(agent_names=["PM", "TechLead"])

    node_names = list(workflow.nodes.keys())

    assert "supervisor" in node_names
    assert "pm_agent" in node_names
    assert "tech_lead_agent" in node_names
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/graph/test_workflow.py -v`
Expected: FAIL - "ModuleNotFoundError: No module named 'thetable.graph.workflow'"

**Step 3: Write minimal implementation**

```python
# thetable/graph/workflow.py
"""Workflow definition"""
from typing import List, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from thetable.graph.state import MeetingState
from thetable.graph.nodes import supervisor_node, create_agent_node
from thetable.graph.phase_controller import should_transition_phase, PhaseController


def route_from_supervisor(state: MeetingState) -> str:
    """Supervisor 결정에 따라 라우팅"""
    next_speaker = state.get("next_speaker")

    if next_speaker == "FINISH":
        # Phase 전환 조건 확인
        if should_transition_phase(state):
            return "phase_transition"
        else:
            # 아직 필수 발언자가 안 끝남, supervisor로 다시
            return "supervisor"

    # Agent 이름을 노드 이름으로 변환 (소문자 + _agent)
    agent_node_name = f"{next_speaker.lower()}_agent"
    return agent_node_name


def phase_transition_node(state: MeetingState) -> dict:
    """Phase 전환"""
    controller = PhaseController()
    current_phase = state["current_phase"]
    next_phase = controller.get_next_phase(current_phase)

    if next_phase == "closing":
        # 회의 종료
        return {
            "current_phase": next_phase,
            "next_speaker": None
        }

    return {
        "current_phase": next_phase,
        "phase_history": state.get("phase_history", []) + [current_phase],
        "phase_start_time": __import__('time').time(),
        "next_speaker": None  # Reset speaker
    }


def create_workflow(agent_names: List[str]):
    """Workflow 생성"""
    workflow = StateGraph(MeetingState)

    # Supervisor 노드
    workflow.add_node("supervisor", supervisor_node)

    # Agent 노드들
    for agent_name in agent_names:
        node_name = f"{agent_name.lower()}_agent"
        workflow.add_node(node_name, create_agent_node(agent_name))

    # Phase transition 노드
    workflow.add_node("phase_transition", phase_transition_node)

    # Edges
    # START → supervisor
    workflow.set_entry_point("supervisor")

    # Supervisor → [agents or phase_transition]
    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            **{f"{name.lower()}_agent": f"{name.lower()}_agent" for name in agent_names},
            "phase_transition": "phase_transition",
            "supervisor": "supervisor"  # Loop back if not ready
        }
    )

    # Agent → supervisor (모든 agent가 supervisor로 돌아감)
    for agent_name in agent_names:
        node_name = f"{agent_name.lower()}_agent"
        workflow.add_edge(node_name, "supervisor")

    # Phase transition → supervisor or END
    def route_from_phase_transition(state: MeetingState) -> Literal["supervisor", "end"]:
        if state["current_phase"] == "closing":
            return "end"
        return "supervisor"

    workflow.add_conditional_edges(
        "phase_transition",
        route_from_phase_transition,
        {
            "supervisor": "supervisor",
            "end": END
        }
    )

    # Compile
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)

    return app
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/graph/test_workflow.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add thetable/graph/workflow.py tests/graph/test_workflow.py
git commit -m "feat: implement workflow with supervisor pattern and phase transitions"
```

---

## Task 10: 설정 시스템

**Files:**
- Create: `thetable/config/__init__.py`
- Create: `thetable/config/settings.py`
- Create: `.env.example`
- Create: `tests/config/test_settings.py`

**Step 1: Write the failing test**

```python
# tests/config/test_settings.py
import os
import pytest
from thetable.config.settings import Settings, load_settings


def test_settings_from_env(monkeypatch):
    """환경 변수에서 설정 로드 테스트"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
    monkeypatch.setenv("LLM_MODEL", "gpt-4")

    settings = Settings()

    assert settings.openai_api_key == "test-key-123"
    assert settings.llm_model == "gpt-4"


def test_load_settings_singleton():
    """load_settings가 싱글톤으로 동작하는지 테스트"""
    settings1 = load_settings()
    settings2 = load_settings()

    assert settings1 is settings2
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/config/test_settings.py -v`
Expected: FAIL - "ModuleNotFoundError: No module named 'thetable.config.settings'"

**Step 3: Write minimal implementation**

```python
# thetable/config/__init__.py
"""Configuration package"""
```

```python
# thetable/config/settings.py
"""Settings management"""
import os
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class Settings(BaseModel):
    """Application settings"""

    openai_api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    llm_model: str = Field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o-mini"))
    llm_temperature: float = Field(default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.7")))

    agent_profiles_path: str = Field(default="config/agent_profiles.yaml")


_settings_instance: Optional[Settings] = None


def load_settings() -> Settings:
    """싱글톤 패턴으로 설정 로드"""
    global _settings_instance

    if _settings_instance is None:
        _settings_instance = Settings()

    return _settings_instance
```

```bash
# .env.example
# OpenAI API Configuration
OPENAI_API_KEY=your-api-key-here
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.7

# Agent Configuration
AGENT_PROFILES_PATH=config/agent_profiles.yaml
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/config/test_settings.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add thetable/config/settings.py .env.example tests/config/test_settings.py
git commit -m "feat: implement settings system with dotenv support"
```

---

## Task 11: CLI/Main 실행 파일

**Files:**
- Create: `thetable/main.py`
- Create: `tests/test_main.py`

**Step 1: Write the failing test**

```python
# tests/test_main.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from thetable.main import run_meeting


@pytest.mark.asyncio
async def test_run_meeting():
    """회의 실행 테스트"""
    with patch("thetable.main.create_workflow") as mock_create_workflow:
        mock_app = MagicMock()
        mock_app.ainvoke = AsyncMock(return_value={
            "messages": [],
            "current_phase": "closing"
        })
        mock_create_workflow.return_value = mock_app

        result = await run_meeting(agent_names=["PM", "TechLead"])

        assert result is not None
        assert mock_create_workflow.called
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_main.py -v`
Expected: FAIL - "ModuleNotFoundError: No module named 'thetable.main'"

**Step 3: Write minimal implementation**

```python
# thetable/main.py
"""Main entry point"""
import asyncio
import time
from typing import List, Optional

from thetable.graph.workflow import create_workflow
from thetable.graph.state import MeetingState, AgentInfo
from thetable.config.settings import load_settings


async def run_meeting(
    agent_names: List[str],
    initial_phase: str = "opening",
    config: Optional[dict] = None
) -> dict:
    """회의 실행"""
    # Settings 로드
    settings = load_settings()

    # Workflow 생성
    app = create_workflow(agent_names=agent_names)

    # 초기 상태
    initial_state: MeetingState = {
        "messages": [],
        "current_phase": initial_phase,
        "phase_history": [],
        "agents": [
            AgentInfo(name=name, role="", profile_key=name)
            for name in agent_names
        ],
        "next_speaker": None,
        "current_task": None,
        "speaker_counts": {},
        "pending_mentions": [],
        "phase_required_speakers": {
            "status_check": ["PM"],
            "issue_resolution": ["TechLead"]
        },
        "phase_goals": {},
        "start_time": time.time(),
        "phase_start_time": time.time()
    }

    # 실행
    final_state = await app.ainvoke(
        initial_state,
        config={"configurable": {"thread_id": "meeting-1"}}
    )

    return final_state


def main():
    """CLI entry point"""
    print("🎯 TheTable - Supervisor 아키텍처 회의 시스템")
    print("=" * 50)

    # 기본 agent 구성
    agent_names = ["PM", "TechLead"]

    print(f"참여자: {', '.join(agent_names)}")
    print("회의를 시작합니다...\n")

    # 회의 실행
    result = asyncio.run(run_meeting(agent_names=agent_names))

    print("\n" + "=" * 50)
    print("✅ 회의가 종료되었습니다.")
    print(f"총 메시지: {len(result['messages'])}개")
    print(f"최종 Phase: {result['current_phase']}")


if __name__ == "__main__":
    main()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_main.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add thetable/main.py tests/test_main.py
git commit -m "feat: implement main entry point and run_meeting function"
```

---

## Task 12: Agent Profile에 Host 추가

**Files:**
- Modify: `config/agent_profiles.yaml`

**Step 1: Host profile 추가**

```yaml
# config/agent_profiles.yaml (기존 내용 위에 추가)
agents:
  - name: Host
    role: host
    responsibilities:
      - 회의 진행 및 조율
      - 다음 발언자 선택
      - Phase 전환 관리
    expertise:
      - 회의 퍼실리테이션
      - 시간 관리
    phase_triggers: {}

  # ... (기존 PM, TechLead, Designer)
```

**Step 2: Commit**

```bash
git add config/agent_profiles.yaml
git commit -m "feat: add Host profile to agent_profiles.yaml"
```

---

## Task 13: README 작성

**Files:**
- Create: `README.md`

**Step 1: README 작성**

```markdown
# TheTable - Supervisor Architecture

> Supervisor 패턴 기반 AI 회의 시스템

## 아키텍처

### Supervisor 중심 설계

```
supervisor → [pm_agent | tech_lead_agent] → supervisor
     ↓                                            ↑
phase_controller                                  │
     ↓                                            │
next_phase ────────────────────────────────────→ │
```

**핵심 원리:**
- Supervisor (Host Agent)가 phase를 보고 적절한 Agent에게 멘션
- 각 Agent는 독립된 노드로 자신의 역할/책임에 맞게 응답
- Phase는 State로 관리, Phase Controller가 명확한 전환 규칙 적용

## 설치

```bash
# 저장소 클론
git clone https://github.com/yourusername/thetable.git
cd thetable

# 의존성 설치
pip install -e ".[dev]"

# 환경 변수 설정
cp .env.example .env
# .env 파일에서 OPENAI_API_KEY 설정
```

## 사용법

```bash
# 회의 실행
python -m thetable.main
```

## 프로젝트 구조

```
thetable/
├── agents/              # Agent 구현
│   ├── base_agent.py   # 기본 Agent
│   └── supervisor.py   # Supervisor Agent
├── core/               # 핵심 컴포넌트
│   └── profile.py      # Agent Profile 시스템
├── graph/              # Workflow 정의
│   ├── state.py        # MeetingState
│   ├── nodes.py        # Workflow 노드들
│   ├── workflow.py     # Workflow 구성
│   └── phase_controller.py  # Phase 전환 제어
├── config/             # 설정
│   └── settings.py     # Settings 관리
└── main.py             # Entry point

config/
└── agent_profiles.yaml  # Agent 역할/책임 정의

tests/                   # 테스트
```

## Agent Profile 시스템

Agent의 역할, 책임, 전문성을 `config/agent_profiles.yaml`에 정의:

```yaml
agents:
  - name: PM
    role: project_manager
    responsibilities:
      - 프로젝트 일정 관리
      - 진행 상황 보고
    expertise:
      - 일정 계획
      - 자원 관리
    phase_triggers:
      status_check: "프로젝트 현황을 보고하세요"
```

## 테스트

```bash
# 모든 테스트 실행
pytest

# 특정 테스트만 실행
pytest tests/agents/test_supervisor.py -v
```

## 라이선스

MIT License
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add comprehensive README with architecture overview"
```

---

## 완료 및 다음 단계

구현 계획이 완료되었습니다!

### 구현된 컴포넌트:
1. ✅ 프로젝트 기본 설정
2. ✅ Agent Profile 시스템
3. ✅ State 정의
4. ✅ Base Agent
5. ✅ Supervisor Agent
6. ✅ Workflow 노드 (supervisor, agent)
7. ✅ Phase Controller
8. ✅ Workflow 구성
9. ✅ 설정 시스템
10. ✅ CLI/Main 실행 파일
11. ✅ Agent Profile에 Host 추가
12. ✅ README

### 테스트 커버리지:
- 단위 테스트: 모든 핵심 컴포넌트
- Mock 사용: LLM 호출 부분
- 비동기 테스트: pytest-asyncio 활용

### 다음 단계 제안:
1. **통합 테스트 추가**: 실제 LLM 호출하는 E2E 테스트
2. **Human-in-the-loop**: 사람 참가자 지원
3. **MCP 도구 통합**: GitHub, Jira 등 외부 도구 연동
4. **스트리밍 응답**: 실시간 응답 표시
5. **회의 기록 저장**: 데이터베이스에 회의 내용 영구 저장
