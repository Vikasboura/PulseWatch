"""
PulseWatch WebSocket Hub
-------------------------
Handles real-time streaming of incoming logs and alert incident events
to connected dashboard clients.

SINGLE-INSTANCE ARCHITECTURE NOTICE:
This connection manager holds active WebSocket connections in memory within
this server process.
- Single-instance (Render/Railway, single Cloud Run instance with 1+ min instances):
  Works out of the box with zero external dependencies.
- Multi-instance scaling:
  When running across multiple containers, an external broker (Redis Pub/Sub)
  must be used: when a log arrives at Container A, it publishes to Redis channel
  `pulsewatch:events:<project_id>`, and all containers subscribed broadcast to
  their locally connected clients.
"""

import asyncio
import json
import logging
from collections import defaultdict
from typing import Set, Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, status
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import SessionLocal, get_db
from app.models.user import User
from app.models.project import Project

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSockets"])


class WebSocketConnectionManager:
    def __init__(self):
        # Maps project_id -> set of active WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = defaultdict(set)

    async def connect(self, project_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[project_id].add(websocket)
        logger.info(f"WebSocket client connected to project {project_id}. Total: {len(self.active_connections[project_id])}")

    def disconnect(self, project_id: str, websocket: WebSocket):
        if project_id in self.active_connections:
            self.active_connections[project_id].discard(websocket)
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]
        logger.info(f"WebSocket client disconnected from project {project_id}")

    async def broadcast_to_project(self, project_id: str, message: dict):
        if project_id not in self.active_connections:
            return

        dead_sockets = set()
        for websocket in list(self.active_connections[project_id]):
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.warning(f"Failed to send to client on project {project_id}: {e}")
                dead_sockets.add(websocket)

        for dead in dead_sockets:
            self.disconnect(project_id, dead)

    def broadcast_log_sync(self, project_id: str, log_data: dict):
        """Helper to broadcast from synchronous ingestion worker."""
        if project_id not in self.active_connections:
            return
        msg = {"type": "log", "data": log_data}
        self._schedule_broadcast(project_id, msg)

    def broadcast_alert_sync(self, project_id: str, alert_data: dict):
        """Helper to broadcast alert events from background evaluator."""
        if project_id not in self.active_connections:
            return
        msg = {"type": "alert", "data": alert_data}
        self._schedule_broadcast(project_id, msg)

    def _schedule_broadcast(self, project_id: str, message: dict):
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast_to_project(project_id, message))
        except RuntimeError:
            pass


ws_manager = WebSocketConnectionManager()


@router.websocket("/ws/live/{project_id}")
async def websocket_live_stream(
    websocket: WebSocket,
    project_id: str,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Real-time WebSocket stream for logs and alert notifications.
    Authenticates with JWT and verifies project ownership.
    """
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing authentication token")
        return

    user_id = decode_access_token(token)
    if not user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or expired token")
        return

    # Verify user exists and owns project
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User not found or inactive")
        return

    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Project not found or permission denied")
        return

    # Authentication & Authorization successful
    await ws_manager.connect(project_id, websocket)

    # Send welcome acknowledgment
    await websocket.send_text(json.dumps({
        "type": "connected",
        "project_id": project_id,
        "message": "Connected to PulseWatch live stream"
    }))

    try:
        while True:
            # Keep connection open and receive optional client messages (e.g. ping)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        ws_manager.disconnect(project_id, websocket)
    except Exception as e:
        logger.warning(f"WebSocket error on project {project_id}: {e}")
        ws_manager.disconnect(project_id, websocket)
