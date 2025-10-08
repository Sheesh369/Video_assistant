import httpx
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()

async def test_api():
    api_key = os.getenv("OPENROUTER_API_KEY")
    print(f"Testing API key: {api_key[:10] if api_key else 'None'}...")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-3.5-turbo",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 50
            }
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")

asyncio.run(test_api())