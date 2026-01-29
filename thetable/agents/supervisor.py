"""Supervisor agent for orchestration"""
import json
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from thetable.agents.base_agent import BaseAgent


class SupervisorAgent(BaseAgent):
    """회의 진행을 조율하는 Supervisor Agent"""

    def _format_agent_profiles(self, profiles: Dict[str, Any]) -> str:
        """Agent profile 정보를 포맷팅"""
        lines = []
        for name, profile in profiles.items():
            lines.append(f"\n{name} ({profile.role}):")
            lines.append(f"  Responsibilities: {', '.join(profile.responsibilities)}")
            lines.append(f"  Expertise: {', '.join(profile.expertise)}")
        return "\n".join(lines)

    async def select_next_speaker(self, context: Dict[str, Any]) -> Dict[str, str]:
        """다음 발언자 선택 및 task 부여"""
        phase = context.get("current_phase", "")
        agent_profiles = context.get("agent_profiles", {})
        candidates = context.get("candidates", [])
        recent_messages = context.get("recent_messages", [])

        prompt_text = f"""You are the meeting host/supervisor.

Current phase: {phase}

Available participants:
{self._format_agent_profiles(agent_profiles)}

Candidates: {', '.join(candidates)}

Recent conversation:
{self._format_recent_messages(recent_messages)}

Based on the current phase, decide:
1. Who should speak next? (select from candidates, or 'FINISH' to complete phase)
2. What specific task/question should you give them?
3. Why did you select them?

Respond in JSON format:
{{{{
    "next_speaker": "name or FINISH",
    "task": "@name specific task here",
    "reason": "explanation"
}}}}
"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", self._build_system_prompt()),
            ("human", prompt_text)
        ])

        chain = prompt | self._llm | StrOutputParser()
        response = await chain.ainvoke({})

        # Parse JSON response
        try:
            decision = json.loads(response)
        except json.JSONDecodeError:
            # Fallback to first candidate
            decision = {
                "next_speaker": candidates[0] if candidates else "FINISH",
                "task": f"@{candidates[0]} Please share your thoughts",
                "reason": "JSON parsing failed, fallback to first candidate"
            }

        return decision

    def _format_recent_messages(self, messages) -> str:
        """최근 메시지 포맷팅"""
        if not messages:
            return "(No messages yet)"

        lines = []
        for msg in messages[-5:]:
            name = getattr(msg, 'name', 'Unknown')
            content = getattr(msg, 'content', '')
            lines.append(f"{name}: {content}")
        return "\n".join(lines)
