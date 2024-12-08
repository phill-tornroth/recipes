import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

import assistant

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


class MessageRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None


class MessageResponse(BaseModel):
    response: str
    thread_id: str


@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open(os.path.join("static", "index.html"), "r") as file:
        html_content = file.read()
    return HTMLResponse(content=html_content, status_code=200)


@app.post("/chat", response_model=MessageResponse)
async def chat_with_assistant(request: MessageRequest):
    response, thread_id = assistant.chat(request.message, request.thread_id)
    return MessageResponse(response=response, thread_id=thread_id)
