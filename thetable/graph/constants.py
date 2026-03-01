"""공유 상수 정의"""

# 안건 상태 이모지
STATUS_EMOJI = {
    "pending": "⏳",
    "in_progress": "🔄",
    "completed": "✅",
    "deferred": "⏸️"
}

# 안건 상태 텍스트
STATUS_TEXT = {
    "pending": "예정",
    "in_progress": "현재 논의 중",
    "completed": "완료",
    "deferred": "보류"
}

# Host 역할 이름
HOST_ROLE_NAME = "Host"

# 에이전트 색상 (동적 할당용)
AGENT_COLORS = ["green", "blue", "yellow", "cyan", "magenta", "bright_white"]
