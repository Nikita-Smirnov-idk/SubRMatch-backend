from pydantic import BaseModel, Field, field_validator
from typing import Text
from .validators.reddit_validators import validate_text, validate_json


class RedditPostModel(BaseModel):
    post: Text = Field(min_length=2, max_length = 10000)

    @field_validator("post")
    def validate_post(cls, value: str) -> str:
        return validate_text(value)




class RedditPostFormatForSubredditModel(BaseModel):
    post: Text = Field(min_length=2, max_length = 10000)
    subreddit_name: str = Field(min_length=2, max_length = 21)
    subreddit_rules: Text = Field(min_length=2, max_length = 10000)

    @field_validator("post")
    def validate_post(cls, value: str) -> str:
        return validate_text(value)
    
    @field_validator("subreddit_name")
    def validate_subreddit_name(cls, value: str) -> str:
        return validate_text(value)
    
    @field_validator("subreddit_rules")
    def validate_subreddit_rules(cls, value: str) -> str:
        return validate_json(value, "subreddit_rules")