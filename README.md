# security-agent-mcp

Security Cloud Control Agent using MCP tools.

## Requirements

- Python `>=3.13`

## Installation

Install the project dependencies from `pyproject.toml`:

```bash
pip install .
```

This installs:

- `mcp`
- `openai`

## Environment Variables

Set the variables required for your target workflow.

For the quick LLM connectivity test:

```bash
export LLM_BASE_URL="https://your-llm-endpoint/v1"
export LLM_API_KEY="your-api-key"
```

For the Security Cloud Control MCP agent:

```bash
export LLM_BASE_URL="https://your-llm-endpoint/v1"
export LLM_API_KEY="your-api-key"
export SCC_API_KEY="your-scc-api-key"
export MCP_SERVER_URL="https://mcp.security.cisco.com/mcp"
```

`MCP_SERVER_URL` is optional. If not set, the agent defaults to `https://mcp.security.cisco.com/mcp`.

## Usage

Run the quick test:

```bash
python simple_agent_test.py
```

This sends a simple prompt to the configured OpenAI-compatible endpoint and prints the response.

Run the interactive Security Cloud Control agent:

```bash
python agent.py
```

The agent connects to the Security Cloud Control MCP server, lists the available tools, and then accepts interactive requests.
