from ollama import Client
import asyncio


class OllamaService:
    def __init__(self,
                 address: str = "http://localhost:11434",
                 model: str = "deepseek-r1:1.5b"):
        self._address = address
        self._model = model

    async def get_chat_stream(self, query: str):
        client = Client(host=self._address)
        chat_messages: list[dict[str, str]] = [{'role': 'user', 'content': query}]

        stream = client.chat(
            model=self._model,
            messages=chat_messages,
            stream=True,
            options={
                "temperature": 2,  # Deterministic output for speed
                "num_ctx": 4096,     # Reasonable context length
                "num_predict": 512   # Limit max tokens for faster response
            }
        )

        for chunk in stream:
            token = chunk['message']['content']
            yield token
            await asyncio.sleep(0.05)
            