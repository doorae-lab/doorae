from unittest.mock import MagicMock

from doorae.core.profile import AgentProfile
from doorae.graph.sub_agent_tool import create_sub_agent_tool


def test_create_sub_agent_tool_name_and_description():
    sub_profile = AgentProfile(
        name="Backend",
        role="backend_engineer",
        responsibilities=["API 설계", "DB 최적화"],
        expertise=["Python", "PostgreSQL"],
    )

    tool = create_sub_agent_tool(
        sub_profile=sub_profile,
        model=MagicMock(),
        parent_name="TechLead",
        mcp_tools={},
    )

    assert tool.name == "ask_backend"
    assert "상위 에이전트: TechLead" in tool.description
    assert "책임: API 설계, DB 최적화" in tool.description
    assert "전문분야: Python, PostgreSQL" in tool.description
