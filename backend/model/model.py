from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from utils.database import Base
from datetime import datetime


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True)
    provider = Column(String)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversations = relationship("Conversation", back_populates="user")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, index=True)
    title = Column(String)
    slug = Column(String)

    user_id = Column(String, ForeignKey("users.id"))

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at.desc()")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, index=True)
    content = Column(String)
    role = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation_id = Column(String, ForeignKey("conversations.id"))

    conversation = relationship("Conversation", back_populates="messages")