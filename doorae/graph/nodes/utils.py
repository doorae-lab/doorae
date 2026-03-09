"""Utility functions - meeting workflow helpers"""

from typing import Optional
from loguru import logger


async def initialize_mcp_tools(config_path: Optional[str] = None) -> dict[str, list]:
    """Initialize MCP tools and collect by server

    Args:
        config_path: Path to mcp_servers.json (defaults to config/mcp_servers.json)

    Returns:
        Dict of tools by server {server_name: [tools]}
    """
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
        from doorae import PROJECT_ROOT
        from doorae.mcp import load_mcp_config, collect_tools_by_server

        # Load MCP config
        if config_path is None:
            config_path = PROJECT_ROOT / "config" / "mcp_servers.json"

        config_dict = load_mcp_config(config_path)

        if not config_dict:
            logger.warning("⚠️ No MCP servers available")
            return {}

        # Initialize MCP client
        from doorae.mcp.cache import CachingInterceptor
        mcp_client = MultiServerMCPClient(config_dict, tool_interceptors=[CachingInterceptor()])

        # Collect tools from all servers
        server_names = set(config_dict.keys())
        tools_by_server = await collect_tools_by_server(mcp_client, server_names)

        total = sum(len(t) for t in tools_by_server.values())
        logger.info(f"✅ MCP tools loaded: {total} tools ({len(tools_by_server)} servers)")

        return tools_by_server

    except ImportError:
        logger.warning("⚠️ langchain-mcp-adapters is not installed")
        return {}
    except FileNotFoundError:
        logger.warning(f"⚠️ MCP config file not found: {config_path}")
        return {}
    except Exception:
        logger.exception("❌ Unexpected error during MCP initialization")
        raise
