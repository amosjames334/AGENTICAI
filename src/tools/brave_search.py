"""Brave Search integration via the Model Context Protocol (MCP).

The agent connects to the official Brave Search MCP server, which is spawned
locally over stdio with `npx -y @modelcontextprotocol/server-brave-search`.
This requires Node.js to be installed and a `BRAVE_API_KEY` to be configured.

If either is missing, `get_brave_tools()` degrades gracefully by returning an
empty list so the reasoning agent can still operate on the local vector store.
"""
import logging
import shutil
from typing import List

logger = logging.getLogger(__name__)

BRAVE_MCP_PACKAGE = "@modelcontextprotocol/server-brave-search"


def _resolve_npx_command() -> str | None:
    """Find an executable npx command (npx / npx.cmd on Windows)."""
    for candidate in ("npx", "npx.cmd"):
        path = shutil.which(candidate)
        if path:
            return path
    return None


def build_brave_server_config() -> dict | None:
    """Build the MultiServerMCPClient config entry for the Brave MCP server.

    Returns None when Node.js (npx) or the BRAVE_API_KEY is unavailable.
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from utils.config import Config

    if not Config.BRAVE_API_KEY:
        logger.warning("Brave Search disabled: BRAVE_API_KEY is not set.")
        return None

    npx = _resolve_npx_command()
    if not npx:
        logger.warning(
            "Brave Search disabled: 'npx' not found. Install Node.js to enable "
            "the Brave Search MCP server."
        )
        return None

    return {
        "brave": {
            "command": npx,
            "args": ["-y", BRAVE_MCP_PACKAGE],
            "env": {"BRAVE_API_KEY": Config.BRAVE_API_KEY},
            "transport": "stdio",
        }
    }


async def get_brave_tools() -> List:
    """Load Brave Search tools from the MCP server.

    Returns a list of LangChain-compatible tools, or an empty list if the
    Brave MCP server cannot be started (missing key, missing Node, or error).
    """
    server_config = build_brave_server_config()
    if not server_config:
        return []

    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient

        client = MultiServerMCPClient(server_config)
        tools = await client.get_tools()
        logger.info(f"Loaded {len(tools)} Brave Search MCP tool(s): "
                    f"{[t.name for t in tools]}")
        return tools
    except Exception as e:
        logger.error(f"Failed to load Brave Search MCP tools: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return []
