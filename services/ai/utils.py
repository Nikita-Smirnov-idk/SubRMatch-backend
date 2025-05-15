from openai import AsyncOpenAI
from core.config import settings
import json
from typing import AsyncGenerator
import httpx
import re
from services.reddit.utils import get_subreddit_rules


deepseek_client = AsyncOpenAI(
    api_key=settings.AI_API_KEY,
    base_url=settings.AI_API_URL
)


def create_data_for_model(prompt: str):
    return {
        "model": "deepseek/deepseek-chat:free",
        "messages": [{"role": "user", "content": prompt}],
        "stream": True
    }


async def stream_openrouter_response(prompt: str) -> AsyncGenerator[str, None]:
    """
    Asynchronously stream response from OpenRouter API for a given prompt.
    Yields chunks of the response as they arrive.
    """
    headers = {
        "Authorization": f"Bearer {settings.AI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = create_data_for_model(prompt)

    async with httpx.AsyncClient() as client:
        try:
            async with client.stream("POST", settings.AI_API_URL, json=data, headers=headers, timeout=30) as response:
                if response.status_code != 200:
                    yield f"Error: Failed to fetch data from API. Status Code: {response.status_code}"
                    return
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        chunk = line[6:].strip()
                        if chunk == "[DONE]":
                            yield chunk
                            break
                        try:
                            json_chunk = json.loads(chunk)
                            content = json_chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
        except httpx.RequestError as e:
            yield f"Error: Request failed - {str(e)}"
    

async def stream_subreddits_suggestion_and_rules(prompt: str) -> AsyncGenerator[str, None]:
    subreddit_pattern = r'- r\/([\w-]+) -'
    text = ""
    subreddit_names = []
    async for chunk in stream_openrouter_response(prompt):
        if chunk.startswith("Error:"):
            yield chunk
            return
        if chunk == "[DONE]":
            subreddit_names = re.findall(subreddit_pattern, text, re.MULTILINE)
            yield f"data: {{\"subreddits\": {json.dumps(subreddit_names)}}}"
            break
        text += chunk
        yield chunk


async def stream_subreddits_suggestion_and_rules_formatted(prompt: str) -> AsyncGenerator[str, None]:
    subreddits = []
    async for chunk in stream_subreddits_suggestion_and_rules(prompt):
        if chunk.startswith("data: {\"subreddits\":"):
            # Извлекаем список сабреддитов из финального чанка
            subreddits = json.loads(chunk[6:])["subreddits"]
        else:
            yield chunk
    yield "\ndata: [DONEAI]\n\n"
    for subreddit in subreddits:
        result = await get_subreddit_rules(subreddit)
        yield result
    yield "\ndata: [DONE]\n\n"