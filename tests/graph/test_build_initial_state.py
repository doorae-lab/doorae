"""build_initial_state 테스트."""

from unittest.mock import MagicMock

from langchain_core.messages import HumanMessage

from doorae.graph.workflow import build_initial_state


def test_returns_required_keys():
    settings = MagicMock()
    settings.max_turns = 100

    result = build_initial_state(
        settings=settings,
        initial_message="시작",
        human_names=["User"],
        agendas=[{"title": "안건1", "status": "pending", "required_speakers": ["Host"]}],
    )

    assert "messages" in result
    assert "agendas" in result
    assert "current_agenda_idx" in result
    assert "pending_speakers" in result
    assert "speaker_counts" in result
    assert "max_turns" in result
    assert "start_time" in result


def test_first_agenda_in_progress():
    settings = MagicMock()
    settings.max_turns = 100

    agendas = [
        {"title": "안건1", "status": "pending", "required_speakers": []},
        {"title": "안건2", "status": "pending", "required_speakers": []},
    ]

    result = build_initial_state(
        settings=settings,
        initial_message="시작",
        human_names=[],
        agendas=agendas,
    )

    assert result["agendas"][0]["status"] == "in_progress"
    assert result["agendas"][1]["status"] == "pending"


def test_initial_message_as_human_message():
    settings = MagicMock()
    settings.max_turns = 100

    result = build_initial_state(
        settings=settings,
        initial_message="회의를 시작합니다",
        human_names=[],
        agendas=[],
    )

    assert isinstance(result["messages"][0], HumanMessage)
    assert result["messages"][0].content == "회의를 시작합니다"
