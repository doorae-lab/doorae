from unittest.mock import MagicMock
from collections.abc import Callable, Mapping, Sequence
from typing import cast

from thetable.core.profile import AgentProfile
from thetable.graph.nodes.agent import AgentNode


def _create_node() -> AgentNode:
    profile = AgentProfile(
        name="Host",
        role="host",
        responsibilities=["test"],
        expertise=["test"],
    )
    return AgentNode(profile=profile, model=MagicMock())


def _apply_actions(
    node: AgentNode,
    actions: Sequence[Mapping[str, object]],
    pending_proposals: Sequence[Mapping[str, str]],
    agendas: Sequence[Mapping[str, str]],
) -> dict[str, object]:
    apply_fn = cast(
        Callable[
            [
                Sequence[Mapping[str, object]],
                Sequence[Mapping[str, str]],
                Sequence[Mapping[str, str]],
            ],
            dict[str, object],
        ],
        getattr(node, "_apply_agenda_actions"),
    )
    return apply_fn(actions, pending_proposals, agendas)


def test_apply_agenda_actions_propose_adds_pending_only():
    node = _create_node()
    pending_proposals = [{"title": "기존 제안", "proposed_by": "PM", "status": "pending"}]
    agendas = [{"title": "현재 안건", "status": "in_progress"}]
    proposal = {
        "title": "신규 제안",
        "description": "설명",
        "proposed_by": "Dev",
        "status": "pending",
    }
    actions = [{"action": "propose", "data": proposal}]

    result = _apply_actions(node, actions, pending_proposals, agendas)

    assert result["pending_proposals"] == [*pending_proposals, proposal]
    assert result["agendas"] == agendas


def test_apply_agenda_actions_approve_moves_pending_to_agendas():
    node = _create_node()
    approved = {"title": "승인 대상", "proposed_by": "PM", "status": "pending"}
    pending_proposals = [approved]
    agendas = [{"title": "기존 안건", "status": "in_progress"}]
    actions = [{"action": "approve", "index": 0, "data": approved}]

    result = _apply_actions(node, actions, pending_proposals, agendas)

    assert result["pending_proposals"] == []
    assert result["agendas"] == [*agendas, approved]


def test_apply_agenda_actions_reject_removes_pending_only():
    node = _create_node()
    pending_proposals = [{"title": "거절 대상", "proposed_by": "PM", "status": "pending"}]
    agendas = [{"title": "기존 안건", "status": "in_progress"}]
    actions = [{"action": "reject", "index": 0, "reason": "범위 외"}]

    result = _apply_actions(node, actions, pending_proposals, agendas)

    assert result["pending_proposals"] == []
    assert result["agendas"] == agendas


def test_apply_agenda_actions_mixed_batch_updates_state_correctly():
    node = _create_node()
    proposal_0 = {"title": "제안 0", "proposed_by": "PM", "status": "pending"}
    proposal_1 = {"title": "제안 1", "proposed_by": "TechLead", "status": "pending"}
    new_proposal = {"title": "제안 2", "proposed_by": "Dev", "status": "pending"}
    pending_proposals = [proposal_0, proposal_1]
    agendas = [{"title": "기존 안건", "status": "in_progress"}]
    actions = [
        {"action": "propose", "data": new_proposal},
        {"action": "approve", "index": 0, "data": proposal_0},
        {"action": "reject", "index": 1, "reason": "중복"},
    ]

    result = _apply_actions(node, actions, pending_proposals, agendas)

    assert result["pending_proposals"] == [new_proposal]
    assert result["agendas"] == [*agendas, proposal_0]


def test_apply_agenda_actions_approve_with_index_drift_removes_both():
    node = _create_node()
    proposal_0 = {"title": "제안 0", "proposed_by": "PM", "status": "pending"}
    proposal_1 = {"title": "제안 1", "proposed_by": "TechLead", "status": "pending"}
    proposal_2 = {"title": "제안 2", "proposed_by": "Designer", "status": "pending"}
    pending_proposals = [proposal_0, proposal_1, proposal_2]
    agendas = [{"title": "기존 안건", "status": "in_progress"}]
    actions = [
        {"action": "approve", "index": 0, "data": proposal_0},
        {"action": "approve", "index": 2, "data": proposal_2},
    ]

    result = _apply_actions(node, actions, pending_proposals, agendas)

    assert result["pending_proposals"] == [proposal_1]
    assert result["agendas"] == [*agendas, proposal_0, proposal_2]


def test_apply_agenda_actions_approve_invalid_index_is_ignored():
    node = _create_node()
    pending_proposals = [{"title": "제안 0", "proposed_by": "PM", "status": "pending"}]
    agendas = [{"title": "기존 안건", "status": "in_progress"}]
    actions = [{"action": "approve", "index": 5, "data": {"title": "무시"}}]

    result = _apply_actions(node, actions, pending_proposals, agendas)

    assert result["pending_proposals"] == pending_proposals
    assert result["agendas"] == agendas


def test_apply_agenda_actions_empty_actions_returns_unchanged_copies():
    node = _create_node()
    pending_proposals = [{"title": "제안 0", "proposed_by": "PM", "status": "pending"}]
    agendas = [{"title": "기존 안건", "status": "in_progress"}]

    result = _apply_actions(node, [], pending_proposals, agendas)

    assert result["pending_proposals"] == pending_proposals
    assert result["agendas"] == agendas
    assert result["pending_proposals"] is not pending_proposals
    assert result["agendas"] is not agendas
