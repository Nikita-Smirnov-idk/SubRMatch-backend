from openai import AsyncOpenAI
from core.config import settings
from fastapi import HTTPException
import json
from pathlib import Path
import asyncio

BASE_DIR = Path(__file__).resolve().parent

# Load JSON file as string during startup
with open(Path(BASE_DIR, "suggest_subreddit_example.json")) as file:
    example_data_str = file.read()
    suggest_subreddit_example = json.loads(example_data_str)

deepseek_client = AsyncOpenAI(
    api_key=settings.AI_API_KEY,
    base_url=settings.AI_API_URL
)

print(settings.AI_API_KEY, settings.AI_API_URL)

async def get_suggested_subreddits(title: str, body: str):
    prompt = (
        f"You are a Reddit expert. Analyze the following Reddit post and suggest 3-5 relevant subreddits where it could be posted.\n"
        f"Focus on the topic, tone, and content.\n"
        f"Return reponse in such way:\n"
        f"{suggest_subreddit_example}\n"
        f"The post: \n"
        f"Title: {title or "No title provided"}\nBody: {body or 'No body provided'}"
    )
    try:
        print('here')
        response = await deepseek_client.chat.completions.create(
            model="deepseek-reasoner",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            stream=False,
        )
        print(response.choices[0].message.content)
        # Парсим ответ, предполагая, что AI возвращает список названий сабреддитов
        subreddits = response.choices[0].message.content.strip().split("\n")
        return [s.strip() for s in subreddits if s.strip()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI API error")