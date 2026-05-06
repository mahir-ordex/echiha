import os
from dotenv import load_dotenv

load_dotenv()  # Load .env FIRST before any other imports

import json
import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from google import genai
from pydantic import BaseModel

from temp.prompt import PROMPT_TEMPLATE, SYSTEM_PROMPT
from utils.tavily import generate_response
from utils.database import engine, Base
from model.model import User, Conversation, Message

app = FastAPI()

@app.on_event("startup")
def on_startup():
    print("🚀 Creating tables if not exist...")
    Base.metadata.create_all(bind=engine)
    print(Base.metadata.tables.keys())


client = genai.Client(api_key=os.getenv("GEMINI_API"))


class AskRequest(BaseModel):
    question: str


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


@app.post("/ask")
async def ask_question(req: AskRequest):
    search_result, prompt_text = await _build_prompt(req.question)

    try:
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

        return {"search_result": search_result, "llm_response": "".join(parts)}
    except Exception as exc:
        return {"search_result": search_result, "llm_error": str(exc)}


@app.post("/ask/stream")
async def ask_question_stream(req: AskRequest):
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


if __name__ == "__main__":
    uvicorn.run("main:app", port=5000, log_level="info")
