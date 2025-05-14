from openai import AsyncOpenAI
from core.config import settings
import json
from pathlib import Path
from typing import AsyncGenerator
import httpx
import re

BASE_DIR = Path(__file__).resolve().parent

# Load JSON file as string during startup
with open(Path(BASE_DIR, "suggest_subreddit_example.txt")) as file:
    example_data_str = file.read()
    suggest_subreddit_example = example_data_str

deepseek_client = AsyncOpenAI(
    api_key=settings.AI_API_KEY,
    base_url=settings.AI_API_URL
)

def create_subreddit_suggestion_prompt(title: str, body: str):
    prompt = (
        f"You are a Reddit expert. Analyze the following Reddit post and suggest 3-5 relevant subreddits where it could be posted.\n"
        f"Focus on the topic, tone, and content.\n" + 
        ("-"*40)+
        f"\n The post: \n"
        "Title: {" + f"{title or "No title provided"}" + "}" "\nBody: {" + f"{body or 'No body provided'}" + "} \n" +
        ("-"*40) +
        "\n Return reponse in such format, do not add anything else:\n{"
        f"{suggest_subreddit_example}" + "}\n"
    )
    return prompt


async def stream_openrouter_response(prompt: str) -> AsyncGenerator[str, None]:
    """
    Asynchronously stream response from OpenRouter API for a given prompt.
    Yields chunks of the response as they arrive.
    """
    headers = {
        "Authorization": f"Bearer {settings.AI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek/deepseek-chat:free",
        "messages": [{"role": "user", "content": prompt}],
        "stream": True  # Enable streaming
    }

    subreddit_pattern = r'- r\/([\w-]+) -'

    async with httpx.AsyncClient() as client:
        try:
            async with client.stream("POST", settings.AI_API_URL, json=data, headers=headers, timeout=30) as response:
                if response.status_code != 200:
                    yield f"Error: Failed to fetch data from API. Status Code: {response.status_code}"
                    return
                
                text = ""
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        chunk = line[6:].strip()
                        if chunk == "[DONE]":
                            subreddit_names = re.findall(subreddit_pattern, text, re.MULTILINE)
                            yield f"data: {{\"subreddits\": {json.dumps(subreddit_names)}}}"
                            break
                        try:
                            json_chunk = json.loads(chunk)
                            content = json_chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if content:
                                text += content
                                yield content
                        except json.JSONDecodeError:
                            continue
        except httpx.RequestError as e:
            yield f"Error: Request failed - {str(e)}"
    