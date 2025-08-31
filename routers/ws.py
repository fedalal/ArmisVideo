from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
from database import SessionLocal
import models
import json

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active:
            self.active.remove(websocket)

    async def broadcast(self, message: dict):
        text = json.dumps(message, default=str)
        for conn in list(self.active):
            try:
                await conn.send_text(text)
            except Exception:
                self.disconnect(conn)

manager = ConnectionManager()

@router.websocket('/ws/presence')
async def presence_ws(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()  # ping-pong or client requests
            # reply current presence snapshot
            with SessionLocal() as db:
                rows = db.query(models.PresenceState).all()
                payload = [{'workstation_id':r.workstation_id,'is_present':r.is_present,'last_seen':r.last_seen} for r in rows]
            await websocket.send_text(json.dumps(payload, default=str))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
