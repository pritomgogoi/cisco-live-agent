# Cisco Live Agent

Quick test agent to verify LLM access via an OpenAI-compatible endpoint.

## Setup

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Set environment variables:

   ```bash
   export LLM_BASE_URL="https://your-llm-endpoint/v1"
   export LLM_API_KEY="your-api-key"
   ```

3. Run the test:

   ```bash
   python quick_test_agent.py
   ```

This sends a simple prompt to the configured LLM and prints the response, confirming connectivity and authentication.
