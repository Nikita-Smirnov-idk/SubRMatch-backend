from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
BASE_EXAMPLES_DIR = Path(BASE_DIR, "prompts_examples")

with open(Path(BASE_EXAMPLES_DIR, "suggest_subreddit_example.txt")) as file:
    suggest_subreddit_example = file.read()

with open(Path(BASE_EXAMPLES_DIR, "format_post_for_subreddit_example.txt")) as file:
    format_post_for_subreddit_example = file.read()


def create_subreddit_suggestion_prompt(post: str):
    prompt = (
        f"You are a Reddit expert. Analyze the following Reddit post and suggest 3-5 relevant subreddits where it could be posted.\n"
        f"Focus on the topic, tone, and content.\n" + 
        ("-"*40)+
        f"\n The post: \n"
        "{" + f"{post}" + "} \n" +
        ("-"*40) +
        "\n Return reponse in such format, do not add anything else:\n{"
        f"{suggest_subreddit_example}" + "}\n"
    )
    return prompt


def create_format_post_for_subreddit_prompt(post: str, subreddit_name: str, subreddit_rules: str):
    prompt = (
        f"You are a Reddit expert. Analyze the following Reddit post and format it according subreddit rules.\n"
        f"Focus on the topic, tone, and content.\n" + 
        ("-"*40)+
        f"\n The post: \n"
        "{" + f"{post}" + "} \n" +
        ("-"*40) +
        f"\n Subreddit name: '{subreddit_name}' \n"
        f"\n Subreddit rules: \n"
        "{" + f"{subreddit_rules}" + "} \n" +
        "\n Return reponse in such format, do not add anything else:\n{"
        f"{format_post_for_subreddit_example}" + "}\n"
    )
    return prompt