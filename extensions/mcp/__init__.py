from __future__ import annotations

import logging

logger = logging.getLogger("ownex.mcp")

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    _MCP_AVAILABLE = True
except ImportError:
    _MCP_AVAILABLE = False
    logger.warning("mcp SDK not installed — plugin disabled")
