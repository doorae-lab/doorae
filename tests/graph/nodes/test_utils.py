"""유틸리티 함수 테스트

이동된 함수들의 테스트:
- extract_mentions_llm → ProcessResponseNode._extract_mentions (통합 테스트로 커버)
- detect_agenda_completion → ProcessResponseNode._detect_agenda_completion (통합 테스트로 커버)
- detect_meeting_end_keyword → ProcessResponseNode._detect_meeting_end_keyword (통합 테스트로 커버)
- detect_meeting_end_llm → ProcessResponseNode._detect_meeting_end_llm (통합 테스트로 커버)
- get_remaining_speakers → RefillSpeakersNode._get_remaining_speakers (통합 테스트로 커버)
"""

import pytest
from doorae.graph.nodes.utils import initialize_mcp_tools


class TestInitializeMCPTools:
    """initialize_mcp_tools 함수 테스트"""

    @pytest.mark.asyncio
    async def test_config_file_not_found(self, tmp_path):
        """설정 파일 없음"""
        # 존재하지 않는 경로 지정
        nonexistent_path = tmp_path / "nonexistent.json"

        result = await initialize_mcp_tools(str(nonexistent_path))

        # FileNotFoundError 또는 ImportError 발생 시 빈 딕셔너리 반환
        assert result == {}
