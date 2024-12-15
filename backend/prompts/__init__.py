from typing import List
import os

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
    conversation_history: List[dict], relevant_recipes: List[str], user_message: str
) -> str:
    template = _get_prompt_template()
    return template.format(
        conversation_history=format_conversation_history(conversation_history),
        relevant_recipes=format_relevant_recipes(relevant_recipes),
        user_message=user_message,
    )


def format_conversation_history(conversation_history: List[dict]) -> str:
    return "\n\n".join(
        f"{message['role']}: {message['content']}" for message in conversation_history
    )


def format_relevant_recipes(relevant_recipes: List[str]) -> str:
    return "\n\n".join(relevant_recipes)
