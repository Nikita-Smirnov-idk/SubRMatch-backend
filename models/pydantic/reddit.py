from pydantic import BaseModel, Field
from typing import Text


class RedditPostModel(BaseModel):
    title: str = Field(max_length = 1000)
    body: Text = Field(max_length = 10000)
