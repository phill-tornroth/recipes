import json
import logging
import os
from typing import List
import uuid

from openai import OpenAI
from pinecone.grpc import PineconeGRPC as Pinecone
from sqlalchemy.orm import Session
import yaml
from fastapi import UploadFile
from typing import Optional, Tuple

from prompts import get_prompt
from storage.conversations import (
    ConversationUpsert,
    upsert_conversation,
    get_conversation,
    get_conversation_contents,
    update_conversation_contents,
)

logging.basicConfig(level=logging.INFO)


USER_ID = "1d7bec80-9ea3-4359-8707-2fffd74a925a"  # Not worrying about tenants for now

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("recipes1")

assistant_prompt = """You're a helpful assistant who keeps track of recipes 
    for your users and helps them meal plan or cook."""

openai_client = OpenAI()
model = "gpt-4o"

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

    # Upload the attachment if it exists
    # if attachment:
    #     attachment_content = await attachment.read()
    #     args["attachments"] = [llm.Attachment(file=attachment_content)]

    prompt = get_prompt(
        get_conversation_contents(thread),
        find_relevant_recipes(user_message),
        user_message,
    )
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_message},
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
