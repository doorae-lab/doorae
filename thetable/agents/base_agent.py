"""Base agent with LLM integration"""
from typing import Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from thetable.config import get_settings
from thetable.core.profile import AgentProfile


class BaseAgent:
    """기본 Agent 클래스"""

    def __init__(
        self,
        name: str,
        profile: AgentProfile,
        llm: Optional[ChatOpenAI] = None,
    ):
        self.name = name
        self.profile = profile
        self._llm = llm or self._init_default_llm()

    def _init_default_llm(self) -> ChatOpenAI:
        """기본 LLM 초기화"""
        settings = get_settings()
        kwargs = {
            "model": settings.llm_model,
            "temperature": settings.llm_temperature,
        }
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        return ChatOpenAI(**kwargs)

    def _build_system_prompt(self) -> str:
        """시스템 프롬프트 생성"""
        return f"""You are {self.name}, a {self.profile.role}.

Your responsibilities:
{chr(10).join(f'- {r}' for r in self.profile.responsibilities)}

Your expertise:
{chr(10).join(f'- {e}' for e in self.profile.expertise)}

Respond according to your role and the given task.
"""

    def _build_user_prompt(self, context: Dict[str, Any]) -> str:
        """사용자 프롬프트 생성"""
        parts = []

        if "phase" in context:
            parts.append(f"Current phase: {context['phase']}")

        if "task" in context:
            parts.append(f"\nTask: {context['task']}")

        if "recent_messages" in context and context["recent_messages"]:
            parts.append("\nRecent conversation:")
            for msg in context["recent_messages"][-5:]:
                parts.append(f"{msg.name}: {msg.content}")

        return "\n".join(parts)

    async def generate_response(self, context: Dict[str, Any]) -> str:
        """응답 생성"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self._build_system_prompt()),
            ("human", self._build_user_prompt(context))
        ])

        chain = prompt | self._llm | StrOutputParser()
        response = await chain.ainvoke({})

        return response
