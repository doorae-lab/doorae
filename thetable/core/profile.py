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
