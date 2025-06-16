import asyncio
import base64
import json
import logging
import math
import re
import uuid
from io import BytesIO
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Union

import requests
import yaml
from auth.models import User
from bs4 import BeautifulSoup
from config import config
from fastapi import HTTPException, UploadFile
from openai import OpenAI
from PIL import Image
from pinecone.grpc import PineconeGRPC as Pinecone
from prompts import get_prompt
from sqlalchemy.orm import Session
from storage.conversations import (
    ConversationUpsert,
    get_conversation,
    get_conversation_contents,
    update_conversation_contents,
    upsert_conversation,
)
from utils.tokens import get_tokens

# Type aliases for better readability
MessageContent = Union[str, List[Dict[str, Any]]]
ConversationMessage = Dict[str, Any]
RecipeData = Dict[str, Any]

logging.basicConfig(level=getattr(logging, config.LOG_LEVEL.upper()))

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
    user: User,
    user_message: str,
    thread_id: Optional[str] = None,
    attachment: Optional[UploadFile] = None,
) -> Tuple[str, str]:
    # Initialize the thread if it's the first message
    if thread_id is None:
        thread = upsert_conversation(
            db, ConversationUpsert(user_id=user.id, contents="")
        )
        thread_id = str(thread.id)
    else:
        thread = get_conversation(db, uuid.UUID(thread_id))
        if thread is None or thread.user_id != user.id:
            raise HTTPException(status_code=404, detail="Conversation not found")

    user_message = process_text_with_urls(user_message)
    user_message_content: MessageContent = user_message

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
        find_relevant_recipes(user_message, user.id),
        max_tokens=MAX_TOKENS - len(get_tokens(json.dumps(user_message_content))),
    )
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_message_content},
    ]

    completion = openai_client.chat.completions.create(  # type: ignore
        model=model,
        messages=messages,  # type: ignore
        tools=TOOLS,  # type: ignore
    )

    tool_calls = completion.choices[0].message.tool_calls
    if tool_calls:
        for tool_call in tool_calls:
            attributes = json.loads(tool_call.function.arguments)
            if tool_call.function.name == "add_recipe":
                recipe_id = add_recipe(attributes["recipe_yaml"], user.id)
                messages.append(
                    {
                        "role": "function",
                        "name": "add_recipe",
                        "content": json.dumps({"recipe_id": recipe_id}),
                    }
                )
            elif tool_call.function.name == "update_recipe":
                update_recipe(
                    attributes["recipe_id"], attributes["recipe_yaml"], user.id
                )
                messages.append(
                    {
                        "role": "function",
                        "name": "add_recipe",
                        "content": json.dumps({"status": "success"}),
                    }
                )

        completion = openai_client.chat.completions.create(  # type: ignore
            model=model,
            messages=messages,  # type: ignore
        )

    response = completion.choices[0].message.content or "No response generated"

    # Update the conversation with relevant messages

    user_message_dict = messages[1]  # type: ignore
    assistant_message_dict = completion.choices[0].message.to_dict()

    conversation_update_messages = [
        {"role": user_message_dict["role"], "content": user_message_dict["content"]},  # type: ignore
        {
            "role": assistant_message_dict["role"],
            "content": assistant_message_dict["content"],
        },
    ]
    update_conversation_contents(thread, conversation_update_messages)

    return response, thread_id


async def chat_with_feedback(
    db: Session,
    user: User,
    user_message: str,
    thread_id: Optional[str] = None,
    attachment: Optional[UploadFile] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Chat function that yields progress updates for real-time feedback.

    Yields events with the following structure:
    - {'type': 'status', 'message': 'Searching your recipe database...'}
    - {'type': 'recipe_search', 'count': 3, 'message': 'Found 3 relevant recipes'}
    - {'type': 'tool_use', 'tool': 'add_recipe', 'message': 'Adding new recipe...'}
    - {'type': 'response', 'content': 'Here is my response...', 'thread_id': 'abc123'}
    """

    # Initialize the thread if it's the first message
    yield {"type": "status", "message": "Initializing conversation..."}
    await asyncio.sleep(0.1)  # Small delay for UI feedback

    if thread_id is None:
        thread = upsert_conversation(
            db, ConversationUpsert(user_id=user.id, contents="")
        )
        thread_id = str(thread.id)
    else:
        thread = get_conversation(db, uuid.UUID(thread_id))
        if thread is None or thread.user_id != user.id:
            raise HTTPException(status_code=404, detail="Conversation not found")

    # Process URL extraction if needed
    if "http" in user_message:
        yield {"type": "status", "message": "Extracting content from URLs..."}
        await asyncio.sleep(0.1)

    user_message = process_text_with_urls(user_message)
    user_message_content: MessageContent = user_message

    # Process image attachment if present
    if attachment:
        yield {"type": "status", "message": "Processing image attachment..."}
        await asyncio.sleep(0.1)

        image_bytes = await attachment.read()
        encoded_string = normalize_image_to_base64_jpeg(image_bytes)
        user_message_content = [
            {"type": "text", "text": user_message},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{encoded_string}"},
            },
        ]

    # Search for relevant recipes
    yield {"type": "status", "message": "Searching your recipe database..."}
    await asyncio.sleep(0.1)

    relevant_recipes = find_relevant_recipes(user_message, user.id)
    recipe_count = len(relevant_recipes)

    if recipe_count > 0:
        yield {
            "type": "recipe_search",
            "count": recipe_count,
            "message": f"Found {recipe_count} relevant recipe{'s' if recipe_count != 1 else ''}",
        }
    else:
        yield {
            "type": "recipe_search",
            "count": 0,
            "message": "No relevant recipes found in your database",
        }

    await asyncio.sleep(0.1)

    # Generate AI response
    yield {"type": "status", "message": "Generating AI response..."}
    await asyncio.sleep(0.1)

    prompt = get_prompt(
        get_conversation_contents(thread),
        relevant_recipes,
        max_tokens=MAX_TOKENS - len(get_tokens(json.dumps(user_message_content))),
    )
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_message_content},
    ]

    completion = openai_client.chat.completions.create(  # type: ignore
        model=model,
        messages=messages,  # type: ignore
        tools=TOOLS,  # type: ignore
    )

    # Handle tool calls if present
    tool_calls = completion.choices[0].message.tool_calls
    if tool_calls:
        for tool_call in tool_calls:
            tool_name = tool_call.function.name

            if tool_name == "add_recipe":
                yield {
                    "type": "tool_use",
                    "tool": "add_recipe",
                    "message": "Adding new recipe to your database...",
                }
            elif tool_name == "update_recipe":
                yield {
                    "type": "tool_use",
                    "tool": "update_recipe",
                    "message": "Updating existing recipe in your database...",
                }

            await asyncio.sleep(0.1)

            # Execute the tool
            attributes = json.loads(tool_call.function.arguments)
            if tool_call.function.name == "add_recipe":
                recipe_id = add_recipe(attributes["recipe_yaml"], user.id)
                messages.append(
                    {
                        "role": "function",
                        "name": "add_recipe",
                        "content": json.dumps({"recipe_id": recipe_id}),
                    }
                )
                yield {
                    "type": "tool_complete",
                    "tool": "add_recipe",
                    "message": "✅ Recipe added successfully!",
                }
            elif tool_call.function.name == "update_recipe":
                update_recipe(
                    attributes["recipe_id"], attributes["recipe_yaml"], user.id
                )
                messages.append(
                    {
                        "role": "function",
                        "name": "add_recipe",
                        "content": json.dumps({"status": "success"}),
                    }
                )
                yield {
                    "type": "tool_complete",
                    "tool": "update_recipe",
                    "message": "✅ Recipe updated successfully!",
                }

        # Get final response after tool use
        yield {"type": "status", "message": "Finalizing response..."}
        await asyncio.sleep(0.1)

        completion = openai_client.chat.completions.create(  # type: ignore
            model=model,
            messages=messages,  # type: ignore
        )

    response = completion.choices[0].message.content or "No response generated"

    # Update the conversation with relevant messages
    user_message_dict = messages[1]  # type: ignore
    assistant_message_dict = completion.choices[0].message.to_dict()

    conversation_update_messages = [
        {"role": user_message_dict["role"], "content": user_message_dict["content"]},  # type: ignore
        {
            "role": assistant_message_dict["role"],
            "content": assistant_message_dict["content"],
        },
    ]
    update_conversation_contents(thread, conversation_update_messages)

    # Final response
    yield {"type": "response", "content": response, "thread_id": thread_id}


def normalize_image_to_base64_jpeg(file_contents: bytes) -> str:
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


def get_embeddings(contents: str) -> List[List[float]]:
    response = openai_client.embeddings.create(input=contents, model=EMBEDDINGS_MODEL)
    embeddings = [record.embedding for record in response.data]
    return embeddings


def find_relevant_recipes(
    user_query: str, user_id: uuid.UUID, top_k: int = 5
) -> List[str]:
    query_embedding = get_embeddings(user_query)
    query_results = index.query(
        namespace=f"user_{user_id}",
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


def add_recipe(recipe_yaml: str, user_id: uuid.UUID) -> str:
    recipe_id = str(uuid.uuid4())
    update_recipe(recipe_id, recipe_yaml, user_id)
    return recipe_id


def update_recipe(recipe_id: str, recipe_yaml: str, user_id: uuid.UUID) -> str:
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
        namespace=f"user_{user_id}",
    )

    return recipe_id
