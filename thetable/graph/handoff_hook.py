"""Post-model hook for Coordinator handoff logic

Coordinator가 텍스트를 출력하는 경우 판단 계층에서
적절한 도구 호출을 주입하여 라우팅을 보장합니다.
"""
from uuid import uuid4


def create_handoff_hook(agent_names: list[str]):
    """Coordinator 출력에서 대상 에이전트를 판단하여 도구 호출 주입

    Args:
        agent_names: 라우팅 가능한 에이전트 이름 목록

    Returns:
        post_model_hook 함수
    """

    def handoff_hook(state: dict) -> dict:
        """텍스트 출력에서 에이전트 언급을 탐지하고 도구 호출 주입"""
        messages = state.get('messages', [])
        if not messages:
            return {}

        last_msg = messages[-1]

        # 이미 도구 호출이 있으면 패스
        if getattr(last_msg, 'tool_calls', []):
            return {}

        # 텍스트에서 대상 에이전트 추출
        content = getattr(last_msg, 'content', '')
        if not content:
            return {}

        target = extract_target_agent(content, agent_names)

        if target:
            # 도구 호출 주입
            # langgraph-supervisor는 에이전트 이름을 소문자로 정규화
            normalized_target = target.lower()
            tool_call = {
                'name': f'transfer_to_{normalized_target}',
                'args': {},
                'id': f'hook_generated_{uuid4().hex[:8]}',
                'type': 'tool_call'
            }
            last_msg.tool_calls = [tool_call]
            return {"messages": [last_msg]}

        return {}

    return handoff_hook


def extract_target_agent(content: str, agent_names: list[str]) -> str | None:
    """텍스트에서 언급된 에이전트 이름 추출

    Args:
        content: 분석할 텍스트
        agent_names: 가능한 에이전트 이름 목록

    Returns:
        탐지된 에이전트 이름, 없으면 None

    Note:
        한국어 호칭 패턴 고려 (예: "PM님", "TechLead님")
        부분 매칭도 지원 (예: "Dev" → "DevOps")
    """
    # 1. 정확한 매칭 우선
    for name in agent_names:
        if name in content or f'{name}님' in content:
            return name

    # 2. 부분 매칭 (대소문자 무시)
    content_lower = content.lower()
    for name in agent_names:
        name_lower = name.lower()
        # 부분 문자열 매칭
        if name_lower in content_lower or f'{name_lower}님' in content_lower:
            return name

    return None
