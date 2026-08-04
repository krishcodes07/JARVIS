"""Quick smoke test for Gemini embedding via the JARVIS provider stack."""

import asyncio
import os
import sys

# Ensure project root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))


async def main():
    from jarvis.providers.protocols.google import GoogleProvider

    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        print("[FAIL] GOOGLE_API_KEY not set in .env")
        return

    provider = GoogleProvider(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta",
    )

    try:
        models = await provider.list_models()
        print("Available models:")
        embed_models = [m['id'] for m in models if 'embed' in m['id'].lower()]
        for m in embed_models:
            print(" -", m)

        for model in embed_models:
            print(f"\nTesting embedding model: {model}")
            try:
                embeddings = await provider.embed(["Hello world"], model)
                print(f"[OK] {model}: got {len(embeddings[0])}-dim embedding")
            except Exception as e:
                print(f"[FAIL] {model}: {e}")
    finally:
        await provider.close()


if __name__ == "__main__":
    asyncio.run(main())
