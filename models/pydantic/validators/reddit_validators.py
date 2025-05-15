import json


def validate_text(post: str, number_of_symbols: int = 2) -> str:
    if len(post.strip()) < number_of_symbols:
        raise ValueError(f"Not enough text in post, at least {number_of_symbols} symbols")
    return post


def validate_json(json_string: str, which_json: str) -> str:
    try:
        json.loads(json_string)
    except ValueError:
        raise ValueError(f"Invalid {which_json}, must be JSON string")
    return json_string