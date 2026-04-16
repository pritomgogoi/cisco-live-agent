1"""Quick test to verify LLM access."""

import os
from openai import OpenAI

client = OpenAI(
    base_url=os.environ["LLM_BASE_URL"],
    api_key=os.environ["LLM_API_KEY"],
)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "user", "content": "What is the weather in San Francisco now?"}
    ],
    max_tokens=100,
)

print(response.choices[0].message.content)
