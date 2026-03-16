"""AgentNodeExecutor Host 중재 프롬프트 테스트."""

from unittest.mock import MagicMock

import pytest

from doorae.core.profile import AgentProfile
from doorae.graph.nodes.agent import AgentNodeExecutor


def _make_profile(name: str, role: str = "participant") -> AgentProfile:
    return AgentProfile(
        name=name,
        role=role,
        responsibilities=["진행"],
        expertise=["퍼실리테이션"],
    )


class TestHostMediationInstructions:
    """Host 프롬프트에 중재 지침이 포함되는지 테스트."""

    def test_host_prompt_includes_mediation_instructions(self):
        """Host의 프롬프트에 중재 지침 섹션이 포함된다."""
        profile = _make_profile("Host", "진행자")
        executor = AgentNodeExecutor(
            profile=profile, model=MagicMock()
        )

        prompt = executor._build_agent_prompt(
            all_agent_names=["Host", "PM", "TechLead"],
        )

        assert "회의 중재 지침" in prompt
        assert "반복 논점 차단" in prompt
        assert "미발언자 참여 유도" in prompt
        assert "피드백 루프 차단" in prompt

    def test_non_host_prompt_excludes_mediation(self):
        """비-Host 에이전트 프롬프트에는 중재 지침이 없다."""
        profile = _make_profile("PM", "프로젝트 매니저")
        executor = AgentNodeExecutor(
            profile=profile, model=MagicMock()
        )

        prompt = executor._build_agent_prompt(
            all_agent_names=["Host", "PM", "TechLead"],
        )

        assert "회의 중재 지침" not in prompt
        assert "반복 논점 차단" not in prompt

    def test_host_prompt_mediation_before_end_protocol(self):
        """중재 지침이 회의 종료 프로토콜보다 앞에 나온다."""
        profile = _make_profile("Host", "진행자")
        executor = AgentNodeExecutor(
            profile=profile, model=MagicMock()
        )

        prompt = executor._build_agent_prompt(
            all_agent_names=["Host", "PM"],
        )

        mediation_pos = prompt.index("회의 중재 지침")
        end_protocol_pos = prompt.index("회의 종료 프로토콜")
        assert mediation_pos < end_protocol_pos
