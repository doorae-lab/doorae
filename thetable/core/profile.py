"""Agent profile system"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import yaml


class AgentLLMConfig(BaseModel):
    """에이전트별 LLM 설정"""

    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class AgentProfile(BaseModel):
    """Agent의 역할, 책임, 전문성 정의 (계층적 구조 지원)"""
    name: str
    role: str
    responsibilities: List[str]
    expertise: List[str]
    phase_triggers: Dict[str, str] = Field(default_factory=dict)
    agents: Optional[List["AgentProfile"]] = None  # 재귀적 하위 에이전트
    is_human: bool = False  # 사용자 참여자 여부
    mcp_tools: List[str] = Field(default_factory=list)  # 사용할 MCP 서버 목록 (예: ["github", "jira"])
    metadata: Dict[str, Any] = Field(default_factory=dict)  # Agent별 메타데이터 (예: repository 정보)
    llm: Optional[AgentLLMConfig] = None

    def matches_phase(self, phase: str) -> bool:
        """특정 phase에서 자동 발언해야 하는지 확인"""
        return phase in self.phase_triggers

    def is_supervisor(self) -> bool:
        """하위 에이전트가 있으면 supervisor"""
        return self.agents is not None and len(self.agents) > 0

    def get_child_names(self) -> List[str]:
        """하위 에이전트 이름 목록"""
        if self.agents:
            return [a.name for a in self.agents]
        return []


# Pydantic v2 재귀 모델 지원
AgentProfile.model_rebuild()


def load_agent_profiles(yaml_path: str) -> Dict[str, AgentProfile]:
    """YAML 파일에서 Agent Profile 로드"""
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    profiles = {}
    for agent_data in data.get('agents', []):
        profile = AgentProfile(**agent_data)
        profiles[profile.name] = profile

    return profiles
