from fastapi import FastAPI
from app.routers import jobs, websocket, health

app = FastAPI(title="CAO Gateway")

app.include_router(jobs.router, prefix="/api/v1")
app.include_router(websocket.router)
app.include_router(health.router, prefix="/api/v1")
