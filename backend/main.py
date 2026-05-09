import os
import uuid
from winsound import MessageBeep
from middleware.auth import Verify_User
import json
from uuid import uuid4
import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from google import genai
from pydantic import BaseModel

from temp.prompt import PROMPT_TEMPLATE, SYSTEM_PROMPT
from utils.tavily import generate_response
from utils.database import engine, Base, SessionLocal
from model.model import User,Message,Conversation
from dotenv import load_dotenv

load_dotenv()


app = FastAPI()

# Configure CORS for local development. Set VITE_DEV_ORIGIN in env to restrict in production.
_dev_origins = [o for o in (
    os.getenv("VITE_DEV_ORIGIN"),
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
) if o]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_dev_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    print("🚀 Creating tables if not exist...")
    Base.metadata.create_all(bind=engine)
    print(Base.metadata.tables.keys())


client = genai.Client(api_key=os.getenv("GEMINI_API"))


class AskRequest(BaseModel):
    question: str


class FollowUpRequest(BaseModel):
    conversation_id: str
    question: str


def _slugify(text: str) -> str:
    slug = "-".join(text.lower().strip().split())
    return slug[:80] or f"conversation-{uuid4().hex[:8]}"


def _serialize_conversation(conversation: Conversation) -> dict:
    return {
        "id": conversation.id,
        "title": conversation.title,
        "slug": conversation.slug,
    }



def _serialize_message(message: Message) -> dict:
    return {
        "id": message.id,
        "content": message.content,
        "role": message.role,
        "created_at": message.created_at,
        "conversation_id": message.conversation_id,
    }


def _save_message(db, conversation_id: str, role: str, content: str) -> Message:
    message = Message(
        id=str(uuid4()),
        conversation_id=conversation_id,
        role=role,
        content=content,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


async def _generate_answer(question: str, history: str | None = None) -> tuple[dict, str]:
    search_result, prompt_text = await _build_prompt(question)

    if history:
        prompt_text = f"Conversation history:\n{history}\n\n{prompt_text}"

    llm_stream = client.models.generate_content_stream(
        model=os.getenv("AI_MODEL"),
        config=genai.types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
        contents=[prompt_text],
    )

    parts = []
    if hasattr(llm_stream, "__aiter__"):
        async for chunk in llm_stream:
            parts.append(_chunk_to_text(chunk))
    else:
        for chunk in llm_stream:
            parts.append(_chunk_to_text(chunk))

    return search_result, "".join(parts)


def _chunk_to_text(chunk) -> str:
    if chunk is None:
        return ""
    if isinstance(chunk, bytes):
        return chunk.decode("utf-8", errors="ignore")
    if isinstance(chunk, str):
        return chunk

    for attribute in ("text", "content", "message"):
        value = getattr(chunk, attribute, None)
        if value:
            return value if isinstance(value, str) else str(value)

    return str(chunk)


def _sse(data: str) -> bytes:
    return f"data: {data}\n\n".encode("utf-8")


async def _build_prompt(question: str) -> tuple[dict, str]:
    search_result = await generate_response(question)
    prompt_text = PROMPT_TEMPLATE.replace("{{WEB_SEARCH_RESULTS}}", str(search_result)).replace(
        "{{USER_QUERY}}", question
    )
    return search_result, prompt_text


@app.post("/ask/stream")
async def ask_question_stream(req: AskRequest, user: User = Depends(Verify_User)):

    search_result, prompt_text = await _build_prompt(req.question)

    try:
        llm_stream = client.models.generate_content_stream(
            model=os.getenv("AI_MODEL"),
            config=genai.types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
            contents=[prompt_text],
        )
    except Exception as exc:
        async def error_stream():
            yield _sse(json.dumps({"type": "error", "error": str(exc)}))

        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    async def event_stream():
        yield _sse(json.dumps({"type": "search_result", "data": search_result}, default=str))

        if hasattr(llm_stream, "__aiter__"):
            async for chunk in llm_stream:
                text = _chunk_to_text(chunk)
                if text:
                    yield _sse(json.dumps({"type": "chunk", "data": text}))
        else:
            for chunk in llm_stream:
                text = _chunk_to_text(chunk)
                if text:
                    yield _sse(json.dumps({"type": "chunk", "data": text}))

        yield _sse(json.dumps({"type": "done"}))

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/conversations")
def get_conversations(current_user: User = Depends(Verify_User)) -> dict:
    db = SessionLocal()
    try:
        conversations = (
            db.query(Conversation)
            .filter(Conversation.user_id == current_user.id)
            .all()
        )
        return {
            "conversations": [_serialize_conversation(conversation) for conversation in conversations],
        }
    finally:
        db.close()


@app.post("/conversation/{conversation_id}")
def get_conversation(conversation_id: str, current_user: User = Depends(Verify_User)) -> dict:
    db = SessionLocal()
    try:
        convo = (
            db.query(Conversation)
            .options(joinedload(Conversation.messages))
            .filter(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user.id,
            )
            .first()
        )

        if not convo:
            raise HTTPException(status_code=404, detail="Conversation Not Found!")

        # convo.messages is populated due to joinedload
        messages = convo.messages or []

        return {
            "conversation": {
                "id": convo.id,
                "title": convo.title,
                "slug": convo.slug,
            },
            "messages": [
                {
                    "id": m.id,
                    "content": m.content,
                    "role": m.role,
                    "created_at": m.created_at,
                    "conversation_id": m.conversation_id,
                }
                for m in messages
            ],
        }
    finally:
        db.close()

@app.post("/purplexity_ask/follow_up")
async def purplexity_follow_up(req: FollowUpRequest, current_user: User = Depends(Verify_User)) -> dict:
    db = SessionLocal()
    try:
        convo = (
            db.query(Conversation)
            .options(joinedload(Conversation.messages))
            .filter(
                Conversation.id == req.conversation_id,
                Conversation.user_id == current_user.id,
            )
            .first()
        )

        if not convo:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Keep last N messages to limit prompt length
        N = 12
        history_messages = convo.messages or []
        trimmed = history_messages[-N:] if len(history_messages) > 0 else []
        history = "\n".join(f"{m.role}: {m.content}" for m in trimmed)

        # Save user's follow-up message
        user_msg = Message(
            id=str(uuid4()),
            conversation_id=req.conversation_id,
            role="user",
            content=req.question,
        )
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)

        # Generate answer with history
        search_result, response_text = await _generate_answer(req.question, history=history)

        # Save assistant message
        assistant_msg = Message(
            id=str(uuid4()),
            conversation_id=req.conversation_id,
            role="assistant",
            content=response_text,
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)

        return {
            "conversation": {
                "id": convo.id,
                "title": convo.title,
                "slug": convo.slug,
            },
            "userMessage": {
                "id": user_msg.id,
                "content": user_msg.content,
                "role": user_msg.role,
                "created_at": user_msg.created_at,
            },
            "assistantMessage": {
                "id": assistant_msg.id,
                "content": assistant_msg.content,
                "role": assistant_msg.role,
                "created_at": assistant_msg.created_at,
            },
            "search_result": search_result,
            "answer": response_text,
        }
    finally:
        db.close()
        
if __name__ == "__main__":
    uvicorn.run("main:app", port=5000, log_level="info")
