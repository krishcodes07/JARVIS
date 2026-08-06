import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from jarvis.providers.base import GenerationConfig, Message
from jarvis.providers.protocols.openai import OpenAIProvider


async def main():
    api_key = os.getenv("GROQ_API_KEY", "")
    provider = OpenAIProvider(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
    )

    messages = [Message(role="user", content="yo jarvis I am back")]

    # Test with max_tokens = 16000 vs 4096
    for max_tok in [16000, 8192, 4096]:
        print(f"Testing Groq with max_tokens={max_tok}...")
        config = GenerationConfig(
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=max_tok,
        )
        try:
            res = await provider.generate(messages, config)
            print(f"  [OK] Success! Response: {res.content[:50]}...")
        except Exception as e:
            print(f"  [FAIL] {e}")

    await provider.close()

if __name__ == "__main__":
    asyncio.run(main())
