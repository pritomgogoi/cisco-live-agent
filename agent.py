"""
Security Cloud Control Agent
Connects an LLM to Cisco Security Cloud Control via MCP tools
to automate user onboarding and management tasks.
"""

import asyncio
import json
import os

from mcp.client.sse import sse_client
from mcp import ClientSession
from openai import OpenAI


# MCP Server configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "https://mcp.security.cisco.com/mcp")
SCC_API_KEY = os.environ["SCC_API_KEY"]

# LLM configuration
llm_client = OpenAI(
    base_url=os.environ["LLM_BASE_URL"],
    api_key=os.environ["LLM_API_KEY"],
)
MODEL = "gpt-4o"

SYSTEM_PROMPT = """You are a Cisco Security Cloud Control assistant that helps with user onboarding and management.

You have access to MCP tools for managing organizations, users, groups, and roles in Security Cloud Control.

Guidelines:
- Always confirm write operations before executing them.
- When onboarding a user, follow this sequence: verify the organization, check if the user exists, invite the user, assign to a group, and assign a role.
- Present results clearly and concisely.
"""


def mcp_tools_to_openai_tools(mcp_tools):
    """Convert MCP tool definitions to OpenAI function-calling format."""
    tools = []
    for tool in mcp_tools:
        tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema,
            },
        })
    return tools


async def agent_loop(session, tools, user_prompt):
    """Run the agent loop: prompt -> LLM -> tool calls -> repeat."""
    openai_tools = mcp_tools_to_openai_tools(tools)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    while True:
        response = llm_client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=openai_tools,
        )

        choice = response.choices[0]

        # If the LLM returns a text response, the task is complete
        if choice.finish_reason == "stop":
            print(f"\nAgent: {choice.message.content}\n")
            break

        # If the LLM wants to call tools, execute them via MCP
        if choice.finish_reason == "tool_calls":
            messages.append(choice.message)

            for tool_call in choice.message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                print(f"  -> Calling: {tool_name}({json.dumps(tool_args, indent=2)})")

                try:
                    result = await session.call_tool(tool_name, tool_args)
                except Exception as e:
                    print(f"  !! Tool call failed: {e}")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": f"Error calling tool: {e}",
                    })
                    continue

                if result.isError:
                    print(f"  !! Tool returned error: {result.content}")
                else:
                    print(f"  <- Result: {result.content}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(result.content),
                })


async def main():
    """Connect to the MCP server and start the interactive agent."""
    headers = {
        "Authorization": f"Bearer {SCC_API_KEY}",
    }

    async with sse_client(MCP_SERVER_URL, headers=headers) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools_result = await session.list_tools()
            tools = tools_result.tools

            print(f"Connected to Security Cloud Control MCP server.")
            print(f"{len(tools)} tools available.\n")

            for tool in tools:
                print(f"  - {tool.name}: {tool.description}")

            print("\nType your request (or 'quit' to exit):\n")

            while True:
                user_input = input("You: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ("quit", "exit"):
                    print("Goodbye!")
                    break
                await agent_loop(session, tools, user_input)


if __name__ == "__main__":
    asyncio.run(main())
