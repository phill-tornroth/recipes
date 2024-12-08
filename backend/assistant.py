import json
import logging
import os
import time
import uuid

from openai import OpenAI
from pinecone.grpc import PineconeGRPC as Pinecone
import yaml

logging.basicConfig(level=logging.INFO)

USER_ID = "1"  # Not worrying about tenants for now

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("recipes1")

assistant_prompt = """You're a helpful assistant who keeps track of recipes 
    for your users and helps them meal plan or cook."""

openai_client = OpenAI()

assistant = openai_client.beta.assistants.retrieve("asst_howzALx8V6GlEQ23eUqWd7wt")

EMBEDDINGS_MODEL = "text-embedding-3-small"


def create_assistant():
    assistant = openai_client.beta.assistants.create(
        name="Phill's Recipe Assistant",
        instructions=assistant_prompt,
        tools=[],  # TODO:  missing tool use... this probably doesn't work.
        model="gpt-4o",
    )
    assistant = openai_client.beta.assistants.update(
        assistant_id=assistant.id,
    )
    return assistant


def chat(message, thread_id=None):
    if thread_id:
        thread = openai_client.beta.threads.retrieve(thread_id)
    else:
        thread = openai_client.beta.threads.create()

    # TODO: Not supporting attachments / images yet
    system_context_message = build_system_context_message_if_appropriate(
        message, first_message=thread_id is None
    )
    if system_context_message:
        openai_client.beta.threads.messages.create(
            thread_id=thread.id,
            role="assistant",
            content=system_context_message,
        )

    openai_client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=message,
    )

    logging.info(
        f"Updating conversation with messages: {system_context_message}\n {message}"
    )

    last_run = openai_client.beta.threads.runs.create(
        thread_id=thread.id, assistant_id=assistant.id
    )

    while True:
        while last_run.status in ("queued", "in_progress"):
            last_run = openai_client.beta.threads.runs.retrieve(
                thread_id=thread.id, run_id=last_run.id
            )
            time.sleep(0.1)
            continue

        if last_run.status == "requires_action":
            tool_calls = last_run.required_action.submit_tool_outputs.tool_calls
            tool_outputs = []
            for tool in tool_calls:
                if tool.function.name == "add_recipe":
                    try:
                        attributes = json.loads(tool.function.arguments)
                        add_recipe(attributes["recipe_yaml"])
                        tool_outputs.append(
                            {
                                "tool_call_id": tool.id,
                                "output": json.dumps("{status: 'success'}"),
                            }
                        )
                        logging.info(f"add_recipe called with {attributes}")
                    except:
                        # we just tell openAI we couldn't :)
                        logging.exception("Tool call failed")
                        tool_outputs.append(
                            {
                                "tool_call_id": tool.id,
                                "output": f"Error in function call add_recipe with arguments {tool.function.arguments}",
                            }
                        )
                        logging.exception(f"Tool call failed - {tool_outputs[-1]}")
                elif tool.function.name == "update_recipe":
                    try:
                        attributes = json.loads(tool.function.arguments)
                        logging.info(f"update_recipe called with {attributes}")
                        update_recipe(
                            attributes["recipe_id"], attributes["recipe_yaml"]
                        )
                        tool_outputs.append(
                            {
                                "tool_call_id": tool.id,
                                "output": json.dumps("{status: 'success'}"),
                            }
                        )
                    except:
                        # we just tell openAi we couldn't :)
                        tool_outputs.append(
                            {
                                "tool_call_id": tool.id,
                                "output": f"Error in function call update_recipe with arguments {tool.function.arguments}",
                            }
                        )
                        logging.exception(f"Tool call failed - {tool_outputs[-1]}")
                else:
                    tool_outputs.append(
                        {
                            "tool_call_id": tool.id,
                            "output": json.dumps("{status: 'unsupported'}"),
                        }
                    )
                    logging.error(
                        f"unexpected function call: {tool.function.name}... ignoring"
                    )

            last_run = openai_client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread.id, run_id=last_run.id, tool_outputs=tool_outputs
            )
            time.sleep(0.1)
            continue

        elif last_run.status == "completed":
            thread_messages = openai_client.beta.threads.messages.list(
                thread.id, limit=4
            )
            response = thread_messages.data[0].content[0].text.value
            logging.info(f"Assistant response: {response} - thread_id: {thread.id}")
            return response, thread.id
        else:
            return (
                "Apologies, the assistant has encountered an error "
                + f"(got an unknown run status: {last_run.status}).",
                None,
            )


def build_system_context_message_if_appropriate(user_query, first_message=False):
    # For now we'll just always do it
    query_embedding = get_embeddings(user_query)
    recipes = find_relevant_recipes(query_embedding, top_k=5)
    recipe_context = "\n\n".join([recipe for recipe in recipes])
    logging.info(f"Found {len(recipes)} relevant recipes: \n{recipe_context}")

    return f"""
    You are a helpful assistant specializing in recipes.

    Here are some recipes that are relevant to the user's query:

    {recipe_context}

    Based on the above recipes, answer the following question:
    """


def get_embeddings(contents) -> list:
    response = openai_client.embeddings.create(input=contents, model=EMBEDDINGS_MODEL)
    embeddings = [record.embedding for record in response.data]
    return embeddings


def find_relevant_recipes(query_embedding, top_k=5):
    query_results = index.query(
        namespace=f"user_{USER_ID}",
        vector=query_embedding[0],
        top_k=top_k,
        include_values=False,
        include_metadata=True,
    )

    results = [result.metadata["contents"] for result in query_results.matches]

    return results


def add_recipe(recipe_yaml):
    recipe_id = str(uuid.uuid4())
    update_recipe(recipe_id, recipe_yaml)
    return recipe_id


def update_recipe(recipe_id, recipe_yaml):
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
