import base64
import json
import logging
import re
from typing import List
import uuid

import requests
from bs4 import BeautifulSoup
from io import BytesIO
from PIL import Image
import math

from openai import OpenAI
from pinecone.grpc import PineconeGRPC as Pinecone
from sqlalchemy.orm import Session
import yaml
from fastapi import UploadFile
from typing import Optional, Tuple

from config import config
from prompts import get_prompt

from utils.tokens import get_tokens
from storage.conversations import (
    ConversationUpsert,
    upsert_conversation,
    get_conversation,
    get_conversation_contents,
    update_conversation_contents,
)

logging.basicConfig(level=getattr(logging, config.LOG_LEVEL.upper()))


USER_ID = "1d7bec80-9ea3-4359-8707-2fffd74a925a"  # Not worrying about tenants for now

pc = Pinecone(api_key=config.PINECONE_API_KEY)
index = pc.Index("recipes1")

openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
model = "gpt-4o"
MAX_TOKENS = 128000

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_recipe",
            "description": "Adds a recipe to our recipe library",
            "strict": False,
            "parameters": {
                "type": "object",
                "properties": {
                    "recipe_yaml": {
                        "type": "string",
                        "description": "The yaml string of the recipe to add",
                    }
                },
                "required": ["recipe_yaml"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_recipe",
            "description": "Updates an existing recipe to our recipe library",
            "strict": False,
            "parameters": {
                "type": "object",
                "properties": {
                    "recipe_id": {
                        "type": "string",
                        "description": "Unique identifier for this recipe",
                    },
                    "recipe_yaml": {
                        "type": "string",
                        "description": "The yaml string of the recipe to add",
                    },
                },
                "required": ["recipe_id", "recipe_yaml"],
            },
        },
    },
]

EMBEDDINGS_MODEL = "text-embedding-3-small"


async def chat(
    db: Session,
    user_message: str,
    thread_id: Optional[str] = None,
    attachment: Optional[UploadFile] = None,
) -> Tuple[str, str]:
    # Initialize the thread if it's the first message
    if thread_id is None:
        thread = upsert_conversation(
            db, ConversationUpsert(user_id=USER_ID, contents="")
        )
        thread_id = str(thread.id)
    else:
        thread = get_conversation(db, thread_id)

    user_message = process_text_with_urls(user_message)
    user_message_content = user_message

    if attachment:
        image_bytes = await attachment.read()
        encoded_string = normalize_image_to_base64_jpeg(image_bytes)
        user_message_content = [
            {"type": "text", "text": user_message},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{encoded_string}"},
            },
        ]

    prompt = get_prompt(
        get_conversation_contents(thread),
        find_relevant_recipes(user_message),
        max_tokens=MAX_TOKENS - len(get_tokens(json.dumps(user_message_content))),
    )
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_message_content},
    ]

    completion = openai_client.chat.completions.create(
        model=model,
        messages=messages,
        tools=TOOLS,
    )

    tool_calls = completion.choices[0].message.tool_calls
    if tool_calls:
        for tool_call in tool_calls:
            attributes = json.loads(tool_call.function.arguments)
            if tool_call.function.name == "add_recipe":
                recipe_id = add_recipe(attributes["recipe_yaml"])
                messages.append(
                    {
                        "role": "function",
                        "name": "add_recipe",
                        "content": json.dumps({"recipe_id": recipe_id}),
                    }
                )
            elif tool_call.function.name == "update_recipe":
                update_recipe(attributes["recipe_id"], attributes["recipe_yaml"])
                messages.append(
                    {
                        "role": "function",
                        "name": "add_recipe",
                        "content": json.dumps({"status": "success"}),
                    }
                )

        completion = openai_client.chat.completions.create(
            model=model,
            messages=messages,
        )

    response = completion.choices[0].message.content

    # Update the conversation with relevant messages

    user_message = messages[1]
    assistant_message = completion.choices[0].message.to_dict()

    conversation_update_messages = [
        {"role": m["role"], "content": m["content"]}
        for m in [user_message, assistant_message]
    ]
    update_conversation_contents(thread, conversation_update_messages)

    return response, thread_id


def normalize_image_to_base64_jpeg(file_contents):
    # Open the PNG image from the file handle
    with Image.open(BytesIO(file_contents)) as img:
        # Ensure the image is in RGB mode (JPEG does not support transparency)
        img = img.convert("RGB")

        # Get current dimensions
        width, height = img.size

        # Resize to fit within 768px on the shorter side, preserving aspect ratio
        if min(width, height) > 768:
            scale_factor = 768 / min(width, height)
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Ensure both dimensions are divisible by 512 for tiling
        width, height = img.size
        new_width = math.ceil(width / 512) * 512
        new_height = math.ceil(height / 512) * 512
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Save the image as JPEG to a BytesIO stream
        buffer = BytesIO()
        img.save(buffer, format="JPEG", optimize=True, quality=85)
        buffer.seek(0)

        # Convert the JPEG bytes to a base64 string
        base64_string = base64.b64encode(buffer.read()).decode("utf-8")

        return base64_string


def get_embeddings(contents) -> list:
    response = openai_client.embeddings.create(input=contents, model=EMBEDDINGS_MODEL)
    embeddings = [record.embedding for record in response.data]
    return embeddings


def find_relevant_recipes(user_query, top_k=5) -> List[str]:
    query_embedding = get_embeddings(user_query)
    query_results = index.query(
        namespace=f"user_{USER_ID}",
        vector=query_embedding[0],
        top_k=top_k,
        include_values=False,
        include_metadata=True,
    )

    results = [result.metadata["contents"] for result in query_results.matches]

    return results


def extract_url(url: str) -> str:
    """
    Fetches the content from a recipe website URL and extracts the main text content.

    Args:
        url (str): The URL of the recipe page.

    Returns:
        str: The extracted recipe text, or an error message if extraction fails.
    """
    try:
        # Spoofing User-Agent to mimic a real browser
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
            )
        }

        # Fetch the webpage
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an error for unsuccessful requests

        # Parse the HTML
        soup = BeautifulSoup(response.content, "html.parser")

        # Try to find the recipe content based on common HTML structures
        # 1. Look for schema.org metadata
        recipe_schema = soup.find("script", type="application/ld+json")
        if recipe_schema:
            print(f"Schema: {recipe_schema.string}")
            import json

            schema_data = json.loads(recipe_schema.string)
            if isinstance(schema_data, dict) and schema_data.get("@type") == "Recipe":
                return schema_data.get(
                    "recipeInstructions", "Recipe instructions not found."
                )

        # 2. Fallback to common HTML elements for recipes
        main_content = soup.find(class_="recipe-content") or soup.find(id="recipe")
        if main_content:
            main_contents = main_content.get_text(strip=True)
            if main_contents:
                print(f"Main Contents: {main_contents}")
                return main_contents

        # 3. If no specific structure is found, return the page's visible text
        return soup.get_text(strip=True)

    except Exception as e:
        return f"An error occurred while processing the URL: {str(e)}"


def process_text_with_urls(text: str) -> str:
    """
    Detects URLs in the text, extracts their content, and appends it next to the URL.

    Args:
        text (str): The input text containing URLs.

    Returns:
        str: The text with extracted content appended next to URLs.
    """
    print(f"Extracting!: {text}")
    # Regular expression to detect URLs
    url_pattern = re.compile(r"(https?://[^\s]+)")

    # Find all URLs in the text
    urls = re.findall(url_pattern, text)

    for url in urls:
        print(f"URL: {url}")
        # Extract content for each URL
        extracted_content = extract_url(url)

        # Append the extracted content next to the URL in the text
        text = text.replace(url, f"{url} (Extracted Content: {extracted_content})")
        print(f"PROCESSED: {text}")

    return text


def add_recipe(recipe_yaml: str) -> str:
    recipe_id = str(uuid.uuid4())
    update_recipe(recipe_id, recipe_yaml)
    return recipe_id


def update_recipe(recipe_id: str, recipe_yaml: str) -> str:
    recipe_data = yaml.safe_load(recipe_yaml)
    recipe_data["recipe_id"] = recipe_id
    yaml_string = yaml.dump(recipe_data)
    embeddings = get_embeddings(yaml_string)

    index.upsert(
        vectors=[
            {
                "id": recipe_id,
                "values": embeddings[
                    0
                ],  # TODO: Understand why we're only using the first one
                "metadata": {
                    "contents": yaml_string,
                },
            },
        ],
        namespace=f"user_{USER_ID}",
    )

    return recipe_id
