import json
import os
from typing import List, Optional

import yaml
from assistant import add_recipe, chat, chat_with_feedback
from auth.dependencies import get_current_user
from auth.models import User
from auth.routes import router as auth_router
from config import config
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session
from storage.dependencies import get_db

# Validate required environment variables on startup
config.validate_required_vars()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include authentication routes
app.include_router(auth_router)

# Serve static files (CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")


class MessagePayload(BaseModel):
    message: str
    thread_id: Optional[str] = None


class MessageResponse(BaseModel):
    response: str
    thread_id: str


class BulkUploadResponse(BaseModel):
    success: bool
    message: str
    recipes_added: int
    errors: List[str] = []


@app.get("/", response_class=HTMLResponse)
async def read_index() -> HTMLResponse:
    with open(os.path.join("static", "index.html"), "r") as file:
        html_content = file.read()
    return HTMLResponse(content=html_content, status_code=200)


@app.get("/settings", response_class=HTMLResponse)
async def read_settings() -> HTMLResponse:
    with open(os.path.join("static", "settings.html"), "r") as file:
        html_content = file.read()
    return HTMLResponse(content=html_content, status_code=200)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> FileResponse:
    return FileResponse(os.path.join("static", "favicon.ico"))


@app.post("/chat", response_model=MessageResponse)
async def chat_with_assistant(
    message: str = Form(...),
    attachment: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    try:
        message_data = json.loads(message)
        payload = MessagePayload(**message_data)
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    user_message = payload.message
    thread_id = payload.thread_id

    # Call the chat function with the message and attachment
    response, new_thread_id = await chat(
        db, current_user, user_message, thread_id, attachment
    )
    db.commit()
    return MessageResponse(response=response, thread_id=new_thread_id)


@app.post("/chat/stream")
async def chat_with_assistant_stream(
    message: str = Form(...),
    attachment: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stream chat responses with real-time tool use feedback."""
    try:
        message_data = json.loads(message)
        payload = MessagePayload(**message_data)
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    user_message = payload.message
    thread_id = payload.thread_id

    async def generate_stream():
        """Generate Server-Sent Events stream."""
        try:
            async for event in chat_with_feedback(
                db, current_user, user_message, thread_id, attachment
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

            # Commit the database transaction
            db.commit()

            # Signal end of stream
            yield f"data: {json.dumps({'type': 'end'}, ensure_ascii=False)}\n\n"
        except Exception as e:
            # Rollback on error
            db.rollback()
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        },
    )


@app.post("/recipes/bulk-upload", response_model=BulkUploadResponse)
async def bulk_upload_recipes(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BulkUploadResponse:
    """
    Upload a YAML file containing one or more recipes for bulk import.

    The YAML file can contain either:
    1. A single recipe with the standard recipe structure
    2. Multiple recipes in a list format:
       recipes:
         - recipe: {...}
         - recipe: {...}
    3. Multiple recipe documents separated by ---
    """
    if not file.filename or not file.filename.endswith((".yaml", ".yml")):
        raise HTTPException(
            status_code=400, detail="File must be a YAML file (.yaml or .yml)"
        )

    try:
        # Read file contents
        contents = await file.read()
        yaml_content = contents.decode("utf-8")

        recipes_added = 0
        errors = []

        try:
            # Try to parse as multiple YAML documents first
            documents = list(yaml.safe_load_all(yaml_content))

            if len(documents) == 1:
                # Single document - check if it's a recipes list or single recipe
                doc = documents[0]
                if isinstance(doc, dict):
                    if "recipes" in doc and isinstance(doc["recipes"], list):
                        # Format: recipes: [recipe1, recipe2, ...]
                        recipes_to_process = doc["recipes"]
                    elif "recipe" in doc:
                        # Single recipe format
                        recipes_to_process = [doc]
                    else:
                        errors.append(
                            "Invalid format: YAML must contain 'recipe' or 'recipes' key"
                        )
                        recipes_to_process = []
                else:
                    errors.append("Invalid format: YAML document must be an object")
                    recipes_to_process = []
            else:
                # Multiple documents
                recipes_to_process = documents

            # Process each recipe
            for i, recipe_data in enumerate(recipes_to_process):
                try:
                    if not isinstance(recipe_data, dict):
                        errors.append(f"Recipe {i+1}: Must be an object")
                        continue

                    if "recipe" not in recipe_data:
                        errors.append(f"Recipe {i+1}: Missing 'recipe' key")
                        continue

                    # Convert back to YAML for storage
                    recipe_yaml = yaml.dump(recipe_data, default_flow_style=False)

                    # Add the recipe using existing function
                    recipe_id = add_recipe(recipe_yaml, current_user.id)
                    recipes_added += 1

                except Exception as e:
                    errors.append(f"Recipe {i+1}: {str(e)}")

        except yaml.YAMLError as e:
            errors.append(f"YAML parsing error: {str(e)}")

        # Commit changes
        db.commit()

        if recipes_added > 0:
            message = f"Successfully imported {recipes_added} recipe{'s' if recipes_added != 1 else ''}"
            if errors:
                message += f" with {len(errors)} error{'s' if len(errors) != 1 else ''}"
            return BulkUploadResponse(
                success=True,
                message=message,
                recipes_added=recipes_added,
                errors=errors,
            )
        else:
            return BulkUploadResponse(
                success=False,
                message="No recipes were imported",
                recipes_added=0,
                errors=errors,
            )

    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400, detail="File must be valid UTF-8 encoded text"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
