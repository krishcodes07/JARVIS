import asyncio
import os
import sys
import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

async def main():
    api_key = os.getenv("NVIDIA_API_KEY", "")
    if not api_key:
        print("❌ NVIDIA_API_KEY not set")
        return

    url = "https://integrate.api.nvidia.com/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    model = "nvidia/nv-embedcode-7b-v1"
    
    # Test 1: Standard OpenAI payload
    payload1 = {
        "input": ["def hello(): print('world')"],
        "model": model,
    }
    
    print("Test 1: Standard OpenAI payload...")
    async with httpx.AsyncClient() as client:
        res1 = await client.post(url, headers=headers, json=payload1)
        print("Status:", res1.status_code)
        print("Response:", res1.text)

    # Test 2: Payload with input_type
    payload2 = {
        "input": ["def hello(): print('world')"],
        "model": model,
        "input_type": "passage",
    }
    
    print("\nTest 2: Payload with input_type='passage'...")
    async with httpx.AsyncClient() as client:
        res2 = await client.post(url, headers=headers, json=payload2)
        print("Status:", res2.status_code)
        print("Response:", res2.text[:200])

if __name__ == "__main__":
    asyncio.run(main())
