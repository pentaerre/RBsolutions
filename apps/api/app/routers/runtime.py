from pydantic import BaseModel, Field
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.db.session import SessionLocal
from app.runtime.orchestrator import Orchestrator

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    model: str | None = None
    app: str | None = None


@router.post("/runtime/chat")
def runtime_chat(payload: ChatRequest) -> StreamingResponse:
    async def events():
        db = SessionLocal()
        try:
            orchestrator = Orchestrator(db)
            async for chunk in orchestrator.stream_chat(payload.message, model=payload.model):
                yield chunk
        finally:
            db.close()

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
