"""안건 관리 Tool 단위 테스트"""

from doorae.graph.agenda_tools import (
    create_propose_tool,
    create_approve_tool,
    create_reject_tool,
)


class TestProposeAgendaTool:
    """propose_agenda Tool 테스트"""

    def test_propose_records_action(self):
        """제안 시 container에 액션이 기록되는지 확인"""
        container = []
        tool = create_propose_tool(container, "PM")
        tool.invoke({"title": "신규 기능 논의", "description": "Q3 로드맵 검토"})

        assert len(container) == 1
        assert container[0]["action"] == "propose"
        assert container[0]["data"]["title"] == "신규 기능 논의"
        assert container[0]["data"]["description"] == "Q3 로드맵 검토"
        assert container[0]["data"]["proposed_by"] == "PM"
        assert container[0]["data"]["status"] == "pending"

    def test_propose_without_description(self):
        """설명 없이 제안해도 동작하는지 확인"""
        container = []
        tool = create_propose_tool(container, "TechLead")
        tool.invoke({"title": "성능 개선"})

        assert container[0]["data"]["description"] == ""
        assert container[0]["data"]["proposed_by"] == "TechLead"

    def test_propose_returns_confirmation_string(self):
        """제안 시 확인 문자열이 반환되는지 확인"""
        container = []
        tool = create_propose_tool(container, "PM")
        result = tool.invoke({"title": "테스트 안건"})

        assert isinstance(result, str)
        assert "테스트 안건" in result


class TestApproveAgendaTool:
    """approve_agenda Tool 테스트"""

    def test_approve_records_action(self):
        """승인 시 container에 액션이 기록되는지 확인"""
        container = []
        proposals = [
            {"title": "신규 기능", "description": "", "proposed_by": "PM", "status": "pending"},
        ]
        tool = create_approve_tool(container, proposals)
        tool.invoke({"proposal_index": 0})

        assert len(container) == 1
        assert container[0]["action"] == "approve"
        assert container[0]["index"] == 0
        assert container[0]["data"]["title"] == "신규 기능"

    def test_approve_invalid_index_returns_error(self):
        """유효하지 않은 인덱스에 대한 오류 처리"""
        container = []
        proposals = [{"title": "안건1"}]
        tool = create_approve_tool(container, proposals)
        result = tool.invoke({"proposal_index": 5})

        # 오류 메시지 반환, container에 기록 없음
        assert "오류" in result
        assert len(container) == 0

    def test_approve_negative_index_returns_error(self):
        """음수 인덱스에 대한 오류 처리"""
        container = []
        proposals = [{"title": "안건1"}]
        tool = create_approve_tool(container, proposals)
        result = tool.invoke({"proposal_index": -1})

        assert "오류" in result
        assert len(container) == 0

    def test_approve_empty_proposals_returns_error(self):
        """후보가 없을 때 오류 처리"""
        container = []
        proposals = []
        tool = create_approve_tool(container, proposals)
        result = tool.invoke({"proposal_index": 0})

        assert "오류" in result
        assert len(container) == 0


class TestRejectAgendaTool:
    """reject_agenda Tool 테스트"""

    def test_reject_records_action(self):
        """거절 시 container에 액션이 기록되는지 확인"""
        container = []
        proposals = [
            {"title": "중복 안건", "proposed_by": "PM"},
        ]
        tool = create_reject_tool(container, proposals)
        tool.invoke({"proposal_index": 0, "reason": "기존 안건과 중복"})

        assert len(container) == 1
        assert container[0]["action"] == "reject"
        assert container[0]["index"] == 0
        assert container[0]["reason"] == "기존 안건과 중복"

    def test_reject_without_reason(self):
        """사유 없이 거절해도 동작하는지 확인"""
        container = []
        proposals = [{"title": "안건1"}]
        tool = create_reject_tool(container, proposals)
        tool.invoke({"proposal_index": 0})

        assert container[0]["reason"] == ""

    def test_reject_invalid_index_returns_error(self):
        """유효하지 않은 인덱스에 대한 오류 처리"""
        container = []
        proposals = [{"title": "안건1"}]
        tool = create_reject_tool(container, proposals)
        result = tool.invoke({"proposal_index": 10})

        assert "오류" in result
        assert len(container) == 0

    def test_reject_returns_confirmation_string(self):
        """거절 시 확인 문자열이 반환되는지 확인"""
        container = []
        proposals = [{"title": "거절 대상 안건", "proposed_by": "PM"}]
        tool = create_reject_tool(container, proposals)
        result = tool.invoke({"proposal_index": 0, "reason": "비관련 주제"})

        assert isinstance(result, str)
        assert "거절" in result


class TestMultipleActions:
    """여러 액션 조합 테스트"""

    def test_multiple_proposals(self):
        """여러 안건 제안이 모두 기록되는지 확인"""
        container = []
        tool = create_propose_tool(container, "PM")

        tool.invoke({"title": "안건 A"})
        tool.invoke({"title": "안건 B"})
        tool.invoke({"title": "안건 C"})

        assert len(container) == 3
        titles = [c["data"]["title"] for c in container]
        assert "안건 A" in titles
        assert "안건 B" in titles
        assert "안건 C" in titles

    def test_approve_and_reject_different_proposals(self):
        """approve와 reject가 각각 다른 후보에 동작하는지 확인"""
        container = []
        proposals = [
            {"title": "안건 1", "proposed_by": "PM"},
            {"title": "안건 2", "proposed_by": "TechLead"},
        ]
        approve_tool = create_approve_tool(container, proposals)
        reject_tool = create_reject_tool(container, proposals)

        approve_tool.invoke({"proposal_index": 0})
        reject_tool.invoke({"proposal_index": 1, "reason": "범위 외"})

        assert len(container) == 2
        assert container[0]["action"] == "approve"
        assert container[0]["index"] == 0
        assert container[1]["action"] == "reject"
        assert container[1]["index"] == 1
