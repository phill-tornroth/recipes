import json
import logging
import os
import uuid
import time

from openai import OpenAI
import psycopg2
import yaml

DB_HOST = os.getenv("DB_HOST", "database")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "recipes")
DB_USER = os.getenv("DB_USER", "recipe_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "bananabread")

conn = psycopg2.connect(
    host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
)

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
    system_context_message = build_system_context_message_if_approprate(
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
                    except:
                        # we just tell openAi we couldn't :)
                        logging.exception("Tool call failed")
                        tool_outputs.append(
                            {
                                "tool_call_id": tool.id,
                                "output": f"Error in function call add_recipe with arguments {tool.function.arguments}",
                            }
                        )
                        print(tool_outputs[-1])
                elif tool.function.name == "update_recipe":
                    try:
                        attributes = json.loads(tool.function.arguments)
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
                        logging.exception("Tool call failed")
                        tool_outputs.append(
                            {
                                "tool_call_id": tool.id,
                                "output": f"Error in function call add_recipe with arguments {tool.function.arguments}",
                            }
                        )
                        print(tool_outputs[-1])
                else:
                    tool_outputs.append(
                        {
                            "tool_call_id": tool.id,
                            "output": json.dumps("{status: 'unsupported'}"),
                        }
                    )
                    print(f"unexpected function call: {tool.function.name}... ignoring")

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
            return response, thread.id
        else:
            return (
                "Apologies, the assistant has encountered an error "
                + f"(got an unknown run status: {last_run.status}).",
                None,
            )


def build_system_context_message_if_approprate(user_query, first_message=False):
    # For now we'll just always do it
    query_embedding = get_embeddings(user_query)
    recipes = find_relevant_recipes(query_embedding, top_k=5)
    recipe_context = "\n\n".join(
        [f"Recipe ID: {rec[0]}\nContents: {rec[2]}" for rec in recipes]
    )
    print(f"Found {len(recipes)} relevant recipes: \n{recipe_context}")

    return f"""
    You are a helpful assistant specializing in recipes.

    Here are some recipes that are relevant to the user's query:

    {recipe_context}

    Based on the above recipes, answer the following question:
    """


def get_embeddings(contents):
    response = openai_client.embeddings.create(input=contents, model=EMBEDDINGS_MODEL)
    embedding = response.data[0].embedding
    print(f"Got embedding for '{contents}': \n{embedding}")
    return embedding


def find_relevant_recipes(query_embedding, top_k=5):
    with conn.cursor() as cur:
        print(f"Querying with embeddings: {query_embedding}")
        cur.execute(
            """
            SET ivfflat.iterative_scan = relaxed_order;
            SELECT
                id,
                user_id,
                contents,
                embedding <=> %s::vector AS distance
            FROM
                recipes
            ORDER BY
                distance ASC
            LIMIT %s;
        """,
            (query_embedding, top_k),
        )
        results = cur.fetchall()
    return results


def add_recipe(recipe_yaml):

    recipe_data = yaml.safe_load(recipe_yaml)
    yaml_string = yaml.dump(recipe_data)
    embeddings = get_embeddings(yaml_string)

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO recipes (user_id, contents, embedding)
            VALUES (%s, %s, %s)
            RETURNING id;
        """,
            (1, yaml_string, embeddings),
        )
        recipe_id = cur.fetchone()[0]
    conn.commit()
    return recipe_id


def update_recipe(recipe_id, recipe_yaml):
    recipe_data = yaml.safe_load(recipe_yaml)
    recipe_data["recipe_id"] = recipe_id
    yaml_string = yaml.dump(recipe_data)
    embeddings = get_embeddings(yaml_string)

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE recipes
            SET contents = %s, embedding = %s
            WHERE id = %s;  
        """,
            (yaml_string, embeddings, recipe_id),
        )
    conn.commit()
    return recipe_id
