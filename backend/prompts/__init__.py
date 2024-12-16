from typing import List
import os

from utils.tokens import get_tokens

prompt_template = None


def _get_prompt_template() -> str:
    global prompt_template
    if not prompt_template:
        current_dir = os.path.dirname(__file__)
        prompt_file_path = os.path.join(current_dir, "prompt.txt")
        with open(prompt_file_path, "r") as file:
            prompt_template = file.read()

    return prompt_template


def get_prompt(
    conversation_history: List[dict],
    relevant_recipes: List[str],
    max_tokens: int = 100000,
) -> str:
    template = _get_prompt_template()
    recipes_formatted = format_relevant_recipes(relevant_recipes)
    prompt_tokens = len(get_tokens(template) + get_tokens(recipes_formatted))
    conversation_max_tokens = max_tokens - prompt_tokens
    conversation_formatted = format_conversation_history(
        conversation_history, max_tokens=conversation_max_tokens
    )
    return template.format(
        conversation_history=conversation_formatted,
        relevant_recipes=recipes_formatted,
    )


def format_conversation_history(
    conversation_history: List[dict], max_tokens: int = 50000
) -> str:
    result = "\n\n".join(
        f"{message['role']}: {message['content']}" for message in conversation_history
    )
    if result:
        result = result[:max_tokens]
        result = result[result.index("\n\n") + 2 :]

    return result


def format_relevant_recipes(relevant_recipes: List[str]) -> str:
    return "\n\n".join(relevant_recipes)
