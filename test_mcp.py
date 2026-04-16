"""Quick script to test MCP tool calls directly."""

import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "https://mcp.security.cisco.com/mcp")
SCC_API_KEY = os.environ["SCC_API_KEY"]


async def test():
    tool_name = sys.argv[1] if len(sys.argv) > 1 else "platform-management_list_organizations"
    headers = {"Authorization": f"Bearer {SCC_API_KEY}"}

    async with streamablehttp_client(MCP_SERVER_URL, headers=headers) as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()

            if tool_name == "--list":
                tools = await s.list_tools()
                for t in tools.tools:
                    print(f"  {t.name}: {t.description}")
                return

            result = await s.call_tool(tool_name, {})
            print(result)


asyncio.run(test())
