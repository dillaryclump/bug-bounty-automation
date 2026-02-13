"""
WebSocket routes for real-time updates
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Optional
import uuid

from src.api.websocket import manager
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])


@router.websocket("/feed")
async def websocket_feed(
    websocket: WebSocket,
    topics: Optional[str] = Query(None, description="Comma-separated list of topics to subscribe to")
):
    """
    WebSocket endpoint for real-time event feed.
    
    Topics:
    - vulnerabilities: New vulnerability discoveries
    - scans: Scan progress updates
    - scope: Scope change detections
    - alerts: Alert notifications
    - all: Subscribe to all events (default)
    
    Example:
        ws://localhost:8000/api/ws/feed?topics=vulnerabilities,scans
    """
    client_id = str(uuid.uuid4())
    
    try:
        # Connect the client
        await manager.connect(websocket, client_id)
        
        # Parse and subscribe to topics
        if topics:
            topic_list = [t.strip() for t in topics.split(",")]
            for topic in topic_list:
                manager.subscribe(client_id, topic)
            
            await websocket.send_json({
                "event": "connected",
                "message": f"Subscribed to topics: {', '.join(topic_list)}",
                "client_id": client_id
            })
        else:
            # Subscribe to all topics by default
            for topic in ["vulnerabilities", "scans", "scope", "alerts"]:
                manager.subscribe(client_id, topic)
            
            await websocket.send_json({
                "event": "connected",
                "message": "Subscribed to all topics",
                "client_id": client_id
            })
        
        # Keep connection alive and handle client messages
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            # Handle subscribe/unsubscribe commands
            if "action" in data:
                if data["action"] == "subscribe" and "topic" in data:
                    manager.subscribe(client_id, data["topic"])
                    await websocket.send_json({
                        "event": "subscribed",
                        "topic": data["topic"]
                    })
                elif data["action"] == "unsubscribe" and "topic" in data:
                    manager.unsubscribe(client_id, data["topic"])
                    await websocket.send_json({
                        "event": "unsubscribed",
                        "topic": data["topic"]
                    })
                elif data["action"] == "ping":
                    await websocket.send_json({"event": "pong"})
            
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        logger.info(f"Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        manager.disconnect(client_id)


@router.websocket("/scans/{scan_id}")
async def websocket_scan_progress(
    websocket: WebSocket,
    scan_id: int
):
    """
    WebSocket endpoint for tracking a specific scan's progress.
    
    Receives real-time updates for a single scan including:
    - Progress percentage
    - Status changes  
    - Discoveries
    - Completion
    
    Example:
        ws://localhost:8000/api/ws/scans/123
    """
    client_id = f"scan_{scan_id}_{uuid.uuid4()}"
    
    try:
        await manager.connect(websocket, client_id)
        manager.subscribe(client_id, f"scan_{scan_id}")
        
        await websocket.send_json({
            "event": "connected",
            "message": f"Tracking scan {scan_id}",
            "scan_id": scan_id
        })
        
        # Keep connection alive
        while True:
            data = await websocket.receive_json()
            
            # Handle ping/pong for keepalive
            if data.get("action") == "ping":
                await websocket.send_json({"event": "pong"})
    
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        logger.info(f"Scan tracker {client_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for scan tracker {client_id}: {e}")
        manager.disconnect(client_id)
