import aiohttp
import json
import logging
from typing import List, Dict, Any
from core.config import settings
import base64

class Reddit:
    def __init__(self, client_id: str, client_secret: str, user_agent: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self.base_url = "https://oauth.reddit.com"
        self.auth_url = "https://www.reddit.com/api/v1/access_token"
        self.access_token = None
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers={"User-Agent": self.user_agent})
        await self._authenticate()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.session.close()

    async def _authenticate(self):
        # Basic Auth: base64(client_id:client_secret)
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_header = base64.b64encode(auth_string.encode()).decode()
        headers = {
            "User-Agent": self.user_agent,
            "Authorization": f"Basic {auth_header}"
        }
        data = {
            "grant_type": "client_credentials"
        }
        async with self.session.post(self.auth_url, headers=headers, data=data) as response:
            if response.status == 200:
                token_data = await response.json()
                self.access_token = token_data["access_token"]
                self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})
            else:
                raise Exception(f"Authentication failed: {response.status}")

    async def subreddit(self, subreddit_name: str):
        return Subreddit(self, subreddit_name)

class Subreddit:
    def __init__(self, reddit: Reddit, name: str):
        self.reddit = reddit
        self.name = name
        self.subscribers = None

    async def load(self):
        async with self.reddit.session.get(f"{self.reddit.base_url}/r/{self.name}/about") as response:
            if response.status == 200:
                data = await response.json()
                self.subscribers = data["data"]["subscribers"]
            else:
                raise Exception(f"Failed to load subreddit {self.name}: {response.status}")

    @property
    async def rules(self):
        async with self.reddit.session.get(f"{self.reddit.base_url}/r/{self.name}/about/rules") as response:
            if response.status == 200:
                data = await response.json()
                for rule in data["rules"]:
                    yield Rule(rule["short_name"], rule["description"])
            else:
                raise Exception(f"Failed to fetch rules for {self.name}: {response.status}")

class Rule:
    def __init__(self, short_name: str, description: str):
        self.short_name = short_name
        self.description = description