# Supervisor Subgraph Wrapper Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wrap nested supervisors (like TechLead) as callable nodes to avoid langgraph-supervisor's `transfer_back_to_*` errors in hierarchical structures

**Architecture:** Create wrapper functions that invoke compiled supervisor subgraphs internally while appearing as simple nodes externally. TechLead supervisor will be compiled separately and invoked from within a wrapper node, encapsulating the Backend/Frontend team management.

**Tech Stack:** LangGraph, langgraph-supervisor, Python 3.12

---

## Background

Current issue: When TechLead (a supervisor with Backend/Frontend sub-agents) is nested under Coordinator, the `transfer_back_to_techlead` tool calls fail with:
```
ValueError: Found AIMessages with tool_calls that do not have a corresponding ToolMessage
```

This is a known limitation of langgraph-supervisor with 3-level nesting (Coordinator → TechLead → Backend/Frontend).

Solution: Use the "invoke inside a node" pattern from [LangGraph Subgraphs docs](https://docs.langchain.com/oss/python/langgraph/use-subgraphs).

---

## Task 1: Create wrapper node builder function

**Files:**
- Modify: `thetable/graph/agent_factory.py`
- Test: `tests/graph/test_agent_factory.py`

**Step 1: Write the failing test**

```python
# tests/graph/test_agent_factory.py 끝에 추가

def test_supervisor_wrapper_creation():
    """Supervisor를 wrapper 노드로 생성하는지 테스트"""
    from thetable.graph.agent_factory import build_agent_graph
    from thetable.core.profile import AgentProfile
    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(model="gpt-4o-mini", api_key="test-key")

    # TechLead supervisor 프로필
    profile = AgentProfile(
        name="TechLead",
        role="tech_lead",
        responsibilities=["기술 의사결정"],
        expertise=["Python"],
        agents=[
            AgentProfile(
                name="Backend",
                role="backend_engineer",
                responsibilities=["API 개발"],
                expertise=["Python"],
                agents=None
            )
        ]
    )

    result = build_agent_graph(profile, model)

    # Callable 함수여야 함
    assert callable(result)

    # name 속성이 있어야 함
    assert hasattr(result, 'name')
    assert result.name == "TechLead"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/graph/test_agent_factory.py::test_supervisor_wrapper_creation -v`
Expected: FAIL (현재는 compiled graph를 반환하므로)

**Step 3: Modify build_agent_graph to return wrapper for supervisors**

```python
# thetable/graph/agent_factory.py

def build_agent_graph(
    profile: AgentProfile,
    model: ChatOpenAI
) -> Any:
    """프로필에서 재귀적으로 에이전트 그래프 빌드

    Args:
        profile: 에이전트 프로필 (계층 구조 포함)
        model: LLM 모델

    Returns:
        Leaf 노드: create_react_agent
        Supervisor 노드: wrapper function (내부에서 compiled subgraph 실행)
    """

    if not profile.is_supervisor():
        # Leaf 노드: ReAct 에이전트 생성
        return create_react_agent(
            model=model,
            tools=[],
            name=profile.name,
            prompt=_build_agent_prompt(profile)
        )

    # Supervisor 노드: 하위 에이전트들 재귀 빌드
    child_agents = []
    for child_profile in profile.agents:
        child_agent = build_agent_graph(child_profile, model)
        child_agents.append(child_agent)

    # 내부 supervisor 그래프 컴파일
    internal_supervisor = create_supervisor(
        agents=child_agents,
        model=model,
        supervisor_name=f"{profile.name}_internal",
        prompt=build_supervisor_prompt(profile, profile.get_child_names())
    ).compile()

    # 외부에는 일반 노드처럼 보이는 wrapper 함수 생성
    def supervisor_wrapper(state):
        """Wrapper that invokes internal supervisor subgraph"""
        result = internal_supervisor.invoke(state)
        return result

    # 함수에 name 속성 추가 (langgraph-supervisor가 이름으로 식별)
    supervisor_wrapper.name = profile.name

    return supervisor_wrapper
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/graph/test_agent_factory.py::test_supervisor_wrapper_creation -v`
Expected: PASS

**Step 5: Run all agent_factory tests**

Run: `uv run pytest tests/graph/test_agent_factory.py -v`
Expected: All tests should pass

**Step 6: Commit**

```bash
git add thetable/graph/agent_factory.py tests/graph/test_agent_factory.py
git commit -m "feat: wrap supervisors in callable nodes for subgraph encapsulation"
```

---

## Task 2: Update existing supervisor test

**Files:**
- Modify: `tests/graph/test_agent_factory.py`

**Step 1: Read current supervisor test**

Read: `tests/graph/test_agent_factory.py` to find `test_supervisor_agent_creation`

**Step 2: Update test expectations**

현재 테스트는 supervisor가 compiled graph를 반환할 것으로 예상합니다. 이제 wrapper 함수를 반환하므로 테스트를 수정해야 합니다.

```python
# tests/graph/test_agent_factory.py - test_supervisor_agent_creation 수정

def test_supervisor_agent_creation():
    """Supervisor Agent 생성 테스트 (계층적)"""
    from thetable.graph.agent_factory import build_agent_graph
    from thetable.core.profile import AgentProfile
    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(model="gpt-4o-mini", api_key="test-key")

    # TechLead with Backend child
    profile = AgentProfile(
        name="TechLead",
        role="tech_lead",
        responsibilities=["기술 의사결정"],
        expertise=["시스템 설계"],
        agents=[
            AgentProfile(
                name="Backend",
                role="backend_engineer",
                responsibilities=["API 개발"],
                expertise=["Python"],
                agents=None
            )
        ]
    )

    supervisor = build_agent_graph(profile, model)

    # Supervisor는 이제 wrapper 함수로 반환됨
    assert callable(supervisor)
    assert hasattr(supervisor, 'name')
    assert supervisor.name == "TechLead"
```

**Step 3: Run test to verify it passes**

Run: `uv run pytest tests/graph/test_agent_factory.py::test_supervisor_agent_creation -v`
Expected: PASS

**Step 4: Commit**

```bash
git add tests/graph/test_agent_factory.py
git commit -m "test: update supervisor test for wrapper pattern"
```

---

## Task 3: Test workflow integration

**Files:**
- Test: `tests/graph/test_workflow.py`

**Step 1: Run existing workflow integration test**

Run: `uv run pytest tests/graph/test_workflow.py::test_create_meeting_workflow_integration -v`
Expected: Should still pass (wrapper is transparent to workflow)

**Step 2: If test passes, commit current state**

```bash
git add -A
git commit -m "refactor: complete supervisor wrapper implementation"
```

**Step 3: If test fails, debug and fix**

Check error message and adjust wrapper implementation as needed.

---

## Task 4: Manual CLI test

**Files:**
- None (manual testing)

**Step 1: Run CLI with simple message**

Run: `uv run thetable -m "회의를 시작합니다"`

**Expected behavior:**
1. Coordinator → transfer_to_host
2. Host: "회의 시작 인사"
3. Coordinator → transfer_to_pm
4. PM: "상태 보고"
5. Coordinator → transfer_to_techlead
6. TechLead wrapper invoked → internal supervisor runs
7. TechLead → transfer_to_backend (내부에서 처리)
8. Backend 작업 완료
9. Backend → transfer_back_to_techlead (내부에서 처리) ← 이제 에러 없음!
10. TechLead wrapper returns
11. Coordinator receives result
12. 회의 계속...

**Step 2: Check for errors**

If `ValueError: Found AIMessages with tool_calls...` error still occurs:
- Debug wrapper state management
- Check if state is properly passed through
- Verify internal supervisor configuration

**Step 3: If successful, document in commit**

```bash
git commit --allow-empty -m "docs: verified CLI execution with supervisor wrappers"
```

---

## Task 5: Add integration test with actual LLM call

**Files:**
- Create: `tests/integration/test_hierarchical_workflow.py`

**Step 1: Create integration test directory**

```bash
mkdir -p tests/integration
```

**Step 2: Write integration test**

```python
# tests/integration/test_hierarchical_workflow.py
"""Integration test for hierarchical workflow with nested supervisors"""
import pytest
from thetable.graph.workflow import create_meeting_workflow
from thetable.graph.state import MeetingState


@pytest.mark.integration
@pytest.mark.skip(reason="Requires OpenAI API key")
def test_hierarchical_workflow_execution():
    """Test that hierarchical workflow executes without tool_call errors"""
    workflow = create_meeting_workflow()

    initial_state: MeetingState = {
        "messages": [{"role": "user", "content": "회의를 시작합니다"}],
        "current_phase": "opening",
        "phase_history": [],
        "agents": [],
        "next_speaker": None,
        "current_task": None,
        "speaker_counts": {},
        "pending_mentions": [],
        "phase_required_speakers": {},
        "phase_goals": {},
        "start_time": 0.0,
        "phase_start_time": 0.0
    }

    # 실행
    result = workflow.invoke(initial_state)

    # 에러 없이 완료되어야 함
    assert result is not None
    assert "messages" in result

    # Host, PM, TechLead가 발언했어야 함
    assert result["speaker_counts"].get("Host", 0) > 0
    assert result["speaker_counts"].get("PM", 0) > 0
    # TechLead는 wrapper이므로 직접 카운트되지 않을 수 있음


@pytest.mark.integration
@pytest.mark.skip(reason="Requires OpenAI API key")
def test_techlead_internal_delegation():
    """Test that TechLead can delegate to Backend/Frontend internally"""
    workflow = create_meeting_workflow()

    # TechLead 단계로 직접 시작
    initial_state: MeetingState = {
        "messages": [{"role": "user", "content": "API 성능 최적화가 필요합니다"}],
        "current_phase": "issue_resolution",
        "phase_history": ["opening", "status_check"],
        "agents": [],
        "next_speaker": "TechLead",
        "current_task": "API 최적화",
        "speaker_counts": {"Host": 1, "PM": 1},
        "pending_mentions": [],
        "phase_required_speakers": {},
        "phase_goals": {},
        "start_time": 0.0,
        "phase_start_time": 0.0
    }

    result = workflow.invoke(initial_state)

    # TechLead 내부에서 Backend/Frontend 중 하나가 처리했어야 함
    # (구체적인 검증은 실제 응답 내용에 따라 조정)
    assert result is not None
```

**Step 3: Add pytest integration marker**

```python
# pyproject.toml에 추가 (또는 pytest.ini)
[tool.pytest.ini_options]
markers = [
    "integration: marks tests as integration tests (deselect with '-m \"not integration\"')",
]
```

**Step 4: Commit**

```bash
git add tests/integration/test_hierarchical_workflow.py pyproject.toml
git commit -m "test: add integration tests for hierarchical workflow"
```

---

## Verification Checklist

- [ ] `uv run pytest tests/graph/test_agent_factory.py -v` 전체 통과
- [ ] `uv run pytest tests/graph/test_workflow.py -v` 전체 통과
- [ ] `uv run thetable -m "회의 시작"` 에러 없이 실행
- [ ] TechLead가 Backend/Frontend로 위임 후 복귀 성공
- [ ] `transfer_back_to_techlead` 에러 발생하지 않음

---

## Rollback Plan

만약 이 접근이 실패하면:

1. **Alternative: 평탄화 (Plan B)**
   - YAML에서 Backend/Frontend를 최상위로 이동
   - TechLead를 단순 leaf 에이전트로 변경
   - 계층 구조 포기, 안정성 우선

2. **Alternative: StateGraph 전환 (Plan C)**
   - langgraph-supervisor 완전히 제거
   - 수동으로 StateGraph 구현
   - 더 많은 제어, 더 많은 코드

---

## Success Criteria

1. ✅ 모든 단위 테스트 통과
2. ✅ CLI 실행 시 `ValueError: tool_calls without ToolMessage` 에러 없음
3. ✅ TechLead → Backend/Frontend 위임 정상 작동
4. ✅ 기존 기능 유지 (Host, PM, DevOps, Designer 정상 작동)
