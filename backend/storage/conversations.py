import json
import uuid
from typing import List
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from sqlalchemy import Column, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session

Base = declarative_base()


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    start_time = Column(TIMESTAMP, nullable=False)
    contents = Column(Text, nullable=False)


class ConversationUpsert(BaseModel):
    id: Optional[uuid.UUID] = None
    user_id: uuid.UUID
    start_time: datetime = Field(default_factory=datetime.now)
    contents: str


def get_conversation(db: Session, conversation_id: uuid.UUID) -> Optional[Conversation]:
    return db.query(Conversation).filter(Conversation.id == conversation_id).first()


def upsert_conversation(
    db: Session, conversation_data: ConversationUpsert
) -> Conversation:
    if conversation_data.id:
        conversation = get_conversation(db, conversation_data.id)
        if conversation_data.contents:
            conversation.contents = conversation_data.contents
    else:
        conversation = Conversation(
            id=conversation_data.id or uuid.uuid4(),
            user_id=conversation_data.user_id,
            start_time=conversation_data.start_time,
            contents=conversation_data.contents,
        )
        db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def get_conversation_contents(conversation: Conversation) -> List[dict]:
    return json.loads(conversation.contents) if conversation.contents else []


def update_conversation_contents(
    conversation: Conversation, messages: List[dict]
) -> None:
    if conversation.contents:
        messages = json.loads(conversation.contents) + messages

    conversation.contents = json.dumps(messages)
