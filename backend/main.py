"""
main.py — ArchAI FastAPI application entry point.

Features:
  - Async lifespan with DB init
  - CORS for frontend dev + production
  - WebSocket connection manager (real-time agent progress)
  - Mounted route groups
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from routes import agents, chat, generate, images, models, projects, users, api_keys, environment


# ─────────────────────────────────────────────────────────────────────────────
# WebSocket connection manager
# ─────────────────────────────────────────────────────────────────────────────

class ConnectionManager:
    """Tracks one WebSocket per project_id for real-time agent progress."""

    def __init__(self) -> None:
        self.active: dict[str, WebSocket] = {}

    async def connect(self, project_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self.active[project_id] = ws

    async def send_update(self, project_id: str, data: dict) -> None:
        ws = self.active.get(project_id)
        if ws is None:
            return
        try:
            await ws.send_json(data)
        except Exception:
            self.disconnect(project_id)

    def disconnect(self, project_id: str) -> None:
        self.active.pop(project_id, None)

    async def broadcast(self, data: dict) -> None:
        dead: list[str] = []
        for pid, ws in self.active.items():
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(pid)
        for pid in dead:
            self.disconnect(pid)


manager = ConnectionManager()


# ─────────────────────────────────────────────────────────────────────────────
# Lifespan
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    app.state.manager = manager
    yield
    # Clean up connections on shutdown
    for ws in list(manager.active.values()):
        try:
            await ws.close()
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="ArchAI API",
    version="1.0.0",
    description="AI-powered architectural design backend",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "https://archai.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(generate.router, prefix="/api/generate", tags=["generate"])
app.include_router(agents.router,   prefix="/api/agents",   tags=["agents"])
app.include_router(models.router,   prefix="/api/models",   tags=["models"])
app.include_router(users.router,    prefix="/api/users",    tags=["users"])
app.include_router(chat.router,     prefix="/api/chat",     tags=["chat"])
app.include_router(images.router,   prefix="/api/images",   tags=["images"])
app.include_router(api_keys.router, prefix="/api/users", tags=["api_keys"])
app.include_router(environment.router, prefix="/api/environment", tags=["environment"])
# Also expose a root keys router for simpler client calls (legacy support)
app.include_router(api_keys.router)


# ─────────────────────────────────────────────────────────────────────────────
# WebSocket endpoint
# ─────────────────────────────────────────────────────────────────────────────

@app.websocket("/ws/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    await manager.connect(project_id, websocket)
    try:
        while True:
            await websocket.receive_text()   # keep-alive ping loop
    except WebSocketDisconnect:
        manager.disconnect(project_id)
    except Exception:
        manager.disconnect(project_id)


# ─────────────────────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["health"])
async def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "active_ws": len(manager.active),
    }
