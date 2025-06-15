import os
import json

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from config import config
from assistant import chat
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

# Serve static files (CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")


class MessagePayload(BaseModel):
    message: str
    thread_id: Optional[str] = None


class MessageResponse(BaseModel):
    response: str
    thread_id: str


@app.get("/", response_class=HTMLResponse)
async def read_index() -> HTMLResponse:
    with open(os.path.join("static", "index.html"), "r") as file:
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
) -> MessageResponse:
    try:
        message_data = json.loads(message)
        payload = MessagePayload(**message_data)
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    user_message = payload.message
    thread_id = payload.thread_id

    # Call the chat function with the message and attachment
    response, new_thread_id = await chat(db, user_message, thread_id, attachment)
    db.commit()
    return MessageResponse(response=response, thread_id=new_thread_id)
