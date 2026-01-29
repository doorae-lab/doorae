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
