"""Agent profile system"""
import os
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator
import yaml
from loguru import logger


def _resolve_env_var(value: str | None) -> str | None:
    """${VAR} 패턴을 환경변수 값으로 치환. 미설정 시 None 반환."""
    if value is None:
        return None
    match = re.fullmatch(r"\$\{(\w+)\}", value)
    if match:
        return os.environ.get(match.group(1))
    return value


class AgentLLMConfig(BaseModel):
    """에이전트별 LLM 설정"""

    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

    @model_validator(mode="after")
    def resolve_env_vars(self) -> "AgentLLMConfig":
        self.model = _resolve_env_var(self.model)
        self.api_key = _resolve_env_var(self.api_key)
        self.base_url = _resolve_env_var(self.base_url)
        return self


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


def validate_no_cycles(profiles: Dict[str, AgentProfile]) -> None:
    """하위 에이전트 순환 참조 검증."""

    def dfs(profile: AgentProfile, path: List[str]) -> None:
        if profile.name in path:
            cycle_path = " -> ".join(path + [profile.name])
            raise ValueError(f"Agent cycle detected: {cycle_path}")

        next_path = path + [profile.name]
        for child in profile.agents or []:
            dfs(child, next_path)

    for profile in profiles.values():
        dfs(profile, [])


def flatten_all_profiles(profiles: Dict[str, AgentProfile]) -> Dict[str, AgentProfile]:
    """모든 레벨의 참여자를 flat dict로 반환."""
    flat: Dict[str, AgentProfile] = {}

    def walk(profile: AgentProfile) -> None:
        if profile.name in flat:
            raise ValueError(f"Duplicate agent name detected: {profile.name}")
        flat[profile.name] = profile
        for child in profile.agents or []:
            walk(child)

    for profile in profiles.values():
        walk(profile)

    return flat


def load_agent_profiles(yaml_path: str) -> Dict[str, AgentProfile]:
    """YAML 파일에서 Agent Profile 로드"""
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    profiles: Dict[str, AgentProfile] = {}
    for agent_data in data.get('agents', []):
        payload = dict(agent_data)
        if payload.get("is_human") and payload.get("agents"):
            logger.warning(
                f"[{payload.get('name', 'unknown')}] is_human=true 이므로 agents 필드는 무시됩니다."
            )
            payload.pop("agents", None)

        profile = AgentProfile(**payload)
        if profile.name in profiles:
            raise ValueError(f"Duplicate top-level agent name detected: {profile.name}")
        profiles[profile.name] = profile

    validate_no_cycles(profiles)
    return profiles
