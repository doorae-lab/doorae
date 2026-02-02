"""MCP Tools 연결 테스트 스크립트"""
import asyncio
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_mcp():
    """MCP 초기화 및 tools 확인"""
    from thetable.graph.workflow import initialize_mcp_tools
    from thetable.core.profile import load_agent_profiles

    print("\n" + "="*60)
    print("MCP Tools 연결 테스트")
    print("="*60 + "\n")

    # 1. MCP 초기화
    print("1. MCP 초기화 중...")
    try:
        mcp_tools = await initialize_mcp_tools()

        if not mcp_tools:
            print("❌ MCP 도구를 로드할 수 없습니다")
            print("\n확인 사항:")
            print("  - .env 파일에 GITHUB_PERSONAL_ACCESS_TOKEN 설정")
            print("  - Docker가 실행 중인지 확인")
            print("  - config/mcp_servers.json 파일 존재 확인")
            return

        print(f"✅ MCP 서버: {list(mcp_tools.keys())}")
        for server, tools in mcp_tools.items():
            print(f"   - {server}: {len(tools)}개 도구")
            for tool in tools[:5]:  # 처음 5개만 표시
                print(f"      • {tool.name}")
            if len(tools) > 5:
                print(f"      ... 외 {len(tools)-5}개")

    except Exception as e:
        print(f"❌ MCP 초기화 실패: {e}")
        import traceback
        traceback.print_exc()
        return

    # 2. Profile 확인
    print("\n2. Agent 프로필 확인 중...")
    profiles = load_agent_profiles("config/agent_profiles.yaml")

    for name, profile in profiles.items():
        if profile.mcp_tools:
            print(f"✅ {name}: {profile.mcp_tools}")

            # 해당 agent가 받을 tools 확인
            agent_tools = []
            for server_name in profile.mcp_tools:
                if server_name in mcp_tools:
                    agent_tools.extend(mcp_tools[server_name])

            print(f"   → {len(agent_tools)}개 도구 연결됨")
        else:
            print(f"⚪ {name}: (도구 없음)")

    print("\n" + "="*60)
    print("테스트 완료!")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(test_mcp())
