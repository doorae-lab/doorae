"""Base agent with LLM integration"""
import logging
from typing import Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI

from thetable.config import get_settings
from thetable.core.profile import AgentProfile

logger = logging.getLogger(__name__)


class BaseAgent:
    """기본 Agent 클래스 (MCP Tool 지원)"""

    def __init__(
        self,
        name: str,
        profile: AgentProfile,
        llm: Optional[ChatOpenAI] = None,
    ):
        self.name = name
        self.profile = profile
        self._llm = llm or self._init_default_llm()
        self._mcp_tools: list = []
        self._system_prompt = self._build_system_prompt()

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

    def bind_mcp_tools(self, tools: list) -> None:
        """MCP 도구를 에이전트에 바인딩하고 시스템 프롬프트를 업데이트."""
        self._mcp_tools = tools
        
        if tools:
            tool_names = [t.name for t in tools]
            logger.info(f"[{self.name}] 🔧 MCP 도구 바인딩 완료: {len(tools)}개")
            logger.debug(f"[{self.name}]    도구 목록: {', '.join(sorted(tool_names))}")
            
            # 실제 도구 정보로 시스템 프롬프트 재구성
            tools_list = ", ".join(sorted(tool_names))
            tools_instruction = f"""

**AVAILABLE TOOLS:**
You have access to MCP tools: {tools_list}

When relevant to the discussion, use these tools to:
- Check actual repository status, open PRs, recent issues
- Fetch real data before making statements about code or project status
- Verify facts rather than making assumptions

Always base your contributions on real data when tools are available.
"""
            self._system_prompt = self._build_system_prompt() + tools_instruction
        else:
            logger.warning(f"[{self.name}] ⚠️ 빈 MCP 도구 목록으로 바인딩 시도")

    async def generate_response(self, context: Dict[str, Any]) -> str:
        """응답 생성 (MCP Tool-Calling 지원)"""
        # MCP 도구가 없으면 기존 로직
        if not self._mcp_tools:
            logger.debug(f"[{self.name}] MCP 도구 없음 - 일반 LLM 모드로 실행")
            prompt = ChatPromptTemplate.from_messages([
                ("system", self._system_prompt),
                ("human", self._build_user_prompt(context))
            ])
            chain = prompt | self._llm | StrOutputParser()
            return await chain.ainvoke({})
        
        # MCP 도구가 있으면 tool-calling 루프
        logger.info(f"[{self.name}] 🔧 MCP tool-calling 모드 활성화 ({len(self._mcp_tools)}개 도구)")
        user_prompt = self._build_user_prompt(context)
        messages = [
            SystemMessage(content=self._system_prompt),
            HumanMessage(content=user_prompt),
        ]
        
        iteration = 0
        max_iterations = 5  # 무한 루프 방지
        
        while iteration < max_iterations:
            iteration += 1
            logger.debug(f"[{self.name}] 🔄 Tool-calling 루프 #{iteration} 시작")
            
            response = await self._llm.bind_tools(self._mcp_tools).ainvoke(messages)
            messages.append(response)
            
            if not response.tool_calls:
                logger.info(f"[{self.name}] ✅ 최종 응답 생성 완료 (총 {iteration}번 반복)")
                return response.content
            
            logger.info(f"[{self.name}] 🛠️ LLM이 {len(response.tool_calls)}개 도구 호출 요청")
            
            # 도구 실행
            for tc in response.tool_calls:
                tool_name = tc["name"]
                tool_args = tc.get("args", {})
                logger.info(f"[{self.name}]   → 도구: {tool_name}")
                logger.debug(f"[{self.name}]      인자: {tool_args}")
                
                tool_fn = {t.name: t for t in self._mcp_tools}.get(tool_name)
                if tool_fn:
                    try:
                        result = await tool_fn.ainvoke(tool_args)
                        logger.debug(f"[{self.name}]   ✅ 도구 실행 성공: {tool_name}")
                        logger.debug(f"[{self.name}]      결과 (처음 200자): {str(result)[:200]}")
                        messages.append(ToolMessage(
                            content=str(result),
                            tool_call_id=tc["id"],
                        ))
                    except Exception as e:
                        logger.error(f"[{self.name}]   ❌ 도구 실행 실패: {tool_name}, 오류: {e}")
                        messages.append(ToolMessage(
                            content=f"Error executing {tool_name}: {e}",
                            tool_call_id=tc["id"],
                        ))
                else:
                    logger.warning(f"[{self.name}]   ⚠️ 알 수 없는 도구: {tool_name}")
        
        logger.warning(f"[{self.name}] ⚠️ 최대 반복 횟수 도달 ({max_iterations})")
        return messages[-1].content if messages else "(응답 생성 실패)"
