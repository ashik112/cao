from fastapi import APIRouter, WebSocket
import redis.asyncio as aioredis
from app.config import REDIS_URL

router = APIRouter()
r = aioredis.from_url(REDIS_URL, decode_responses=True)

@router.websocket("/ws/{job_id}")
async def ws(job_id: str, websocket: WebSocket):
    await websocket.accept()
    pubsub = r.pubsub()
    await pubsub.subscribe(f"ws:{job_id}")
    await websocket.send_json({"type": "WS_CONNECTED", "job_id": job_id})

    try:
        async for msg in pubsub.listen():
            if msg and msg.get("type") == "message":
                await websocket.send_text(msg["data"])
    finally:
        await pubsub.unsubscribe(f"ws:{job_id}")
        await pubsub.close()
        await websocket.close()
