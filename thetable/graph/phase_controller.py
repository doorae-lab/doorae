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
        return "closing"


def should_transition_phase(state: Dict[str, Any]) -> bool:
    """Phase 전환 조건 확인"""
    current_phase = state["current_phase"]
    speaker_counts = state.get("speaker_counts", {})
    required_speakers = state.get("phase_required_speakers", {}).get(current_phase, [])

    if not required_speakers:
        return True

    for speaker in required_speakers:
        if speaker_counts.get(speaker, 0) == 0:
            return False

    return True
