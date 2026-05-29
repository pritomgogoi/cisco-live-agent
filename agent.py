"""
Security Cloud Control Agent
Connects an LLM to Cisco Security Cloud Control via MCP tools
to automate user onboarding and management tasks.
"""

import asyncio
import json
import os
import re

from dotenv import load_dotenv

load_dotenv()

from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession
from openai import OpenAI, RateLimitError


# MCP Server configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "https://mcp.security.cisco.com/mcp")
SCC_API_KEY = os.environ["SCC_API_KEY"]

# LLM configuration
llm_client = OpenAI(
    base_url=os.environ["LLM_BASE_URL"],
    api_key=os.environ["LLM_API_KEY"],
)
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

SCC_ORG_ID = os.environ.get("SCC_ORG_ID", "")

SYSTEM_PROMPT = f"""You are a Cisco Security Cloud Control assistant that helps with user onboarding and management.

You are operating in the context of organization ID: {SCC_ORG_ID}

You have access to MCP tools for managing organizations, users, groups, and roles in Security Cloud Control.

Guidelines:
- Always use organization ID {SCC_ORG_ID} when making tool calls that require an org ID.
- Always confirm write operations before executing them.
- When onboarding a user, follow this sequence: verify the organization, check if the user exists, invite the user, assign to a group, and assign a role.
- When creating a group, do not include the appliesTo field in the request payload.
- Present results clearly and concisely.
"""


def mcp_tools_to_openai_tools(mcp_tools):
    """
    Takes a list of MCP tool objects returned by the MCP server and converts them into the
    OpenAI function-calling schema format. Each tool's name, description, and input schema
    are mapped to the structure expected by the OpenAI chat completions API so the LLM can
    select and invoke them.
    """
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


async def agent_loop(session, tools, messages, user_prompt):
    """
    Runs a single turn of the agent loop for a given user prompt. Appends the user message
    to the conversation history, then repeatedly calls the LLM until it produces a final
    text response. If the LLM requests tool calls, each tool is executed against the MCP
    session and the results are fed back into the conversation before the next LLM call.
    Prints the agent's final response to the terminal with basic markdown-to-ANSI formatting.
    """
    openai_tools = mcp_tools_to_openai_tools(tools)

    messages.append({"role": "user", "content": user_prompt})

    while True:
        try:
            response = llm_client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=openai_tools,
            )
        except RateLimitError:
            print("\n\033[91mRate limited. Please try again in a few minutes.\033[0m\n")
            messages.pop()
            return

        choice = response.choices[0]

        # If the LLM returns a text response, the task is complete
        if choice.finish_reason == "stop":
            messages.append(choice.message)
            content = choice.message.content
            content = re.sub(r'\*\*(.+?)\*\*', r'\033[1m\1\033[22m', content)
            content = re.sub(r'\*(.+?)\*', r'\1', content)
            content = re.sub(r'^#{1,3}\s+', '', content, flags=re.MULTILINE)
            print(f"\n\033[94mAgent:\033[0m \033[93m{content}\033[0m\n")
            break

        # If the LLM wants to call tools, execute them via MCP
        if choice.finish_reason == "tool_calls":
            messages.append(choice.message)

            for tool_call in choice.message.tool_calls:
                tool_name = tool_call.function.name
                raw_args = json.loads(tool_call.function.arguments)
                tool_args = raw_args.get("arguments", raw_args) if "arguments" in raw_args else raw_args

                print(f"\033[91m  -> Calling: {tool_name}({json.dumps(tool_args, indent=2)})\033[0m")

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
                    print(f"\033[91m  !! Tool returned error: {result.content}\033[0m")
                else:
                    print(f"\033[92m  <- Result: {result.content}\033[0m")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(result.content),
                })


async def main():
    """
    Entry point for the agent. Establishes an authenticated connection to the Cisco Security
    Cloud Control MCP server, fetches the list of available tools, and prints them to the
    terminal. Then starts an interactive REPL where the user can type requests in plain
    language. Each request is handled by agent_loop(), which drives the LLM and any
    tool calls needed to fulfill it. Type 'quit' or 'exit' to stop.
    """
    headers = {
        "Authorization": f"Bearer {SCC_API_KEY}",
    }

    async with streamablehttp_client(MCP_SERVER_URL, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools_result = await session.list_tools()
            tools = tools_result.tools

            print(f"\033[94mConnected to Security Cloud Control MCP server.")
            print(f"Using OpenAI model: {MODEL}\033[0m")
            print(f"\033[92m{len(tools)} tools available.\033[0m\n")

            for tool in tools:
                print(f"\033[93m  - {tool.name}: {tool.description}\033[0m")

            print("\nType your request (or 'quit' to exit):\n")

            messages = [{"role": "system", "content": SYSTEM_PROMPT}]

            while True:
                user_input = input("\033[94mYou:\033[0m ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ("quit", "exit"):
                    print("Goodbye!")
                    break
                await agent_loop(session, tools, messages, user_input)


if __name__ == "__main__":
    asyncio.run(main())
