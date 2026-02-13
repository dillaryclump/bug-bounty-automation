"""
WebSocket manager for real-time updates

Broadcasts events to connected clients:
- New vulnerabilities discovered
- Scan progress updates
- Scope changes detected
- Alerts sent
"""

from typing import Dict, Set
from fastapi import WebSocket
import json
import asyncio
from datetime import datetime

from src.utils.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and broadcasting."""
    
    def __init__(self):
        # Active connections by connection ID
        self.active_connections: Dict[str, WebSocket] = {}
        # Subscriptions: topic -> set of connection IDs
        self.subscriptions: Dict[str, Set[str]] = {}
        
    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket client connected: {client_id}")
        
    def disconnect(self, client_id: str):
        """Remove a WebSocket connection."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            
            # Remove from all subscriptions
            for topic in self.subscriptions:
                self.subscriptions[topic].discard(client_id)
                
            logger.info(f"WebSocket client disconnected: {client_id}")
    
    def subscribe(self, client_id: str, topic: str):
        """Subscribe a client to a topic."""
        if topic not in self.subscriptions:
            self.subscriptions[topic] = set()
        self.subscriptions[topic].add(client_id)
        logger.debug(f"Client {client_id} subscribed to {topic}")
    
    def unsubscribe(self, client_id: str, topic: str):
        """Unsubscribe a client from a topic."""
        if topic in self.subscriptions:
            self.subscriptions[topic].discard(client_id)
            logger.debug(f"Client {client_id} unsubscribed from {topic}")
    
    async def send_personal_message(self, message: dict, client_id: str):
        """Send a message to a specific client."""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)
    
    async def broadcast(self, message: dict, topic: str = None):
        """
        Broadcast a message to all connected clients or topic subscribers.
        
        Args:
            message: Message dict to send
            topic: Optional topic to filter subscribers
        """
        message["timestamp"] = datetime.utcnow().isoformat()
        
        # Determine recipients
        if topic and topic in self.subscriptions:
            recipients = self.subscriptions[topic]
        else:
            recipients = set(self.active_connections.keys())
        
        # Send to all recipients
        disconnected = []
        for client_id in recipients:
            if client_id in self.active_connections:
                try:
                    await self.active_connections[client_id].send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to {client_id}: {e}")
                    disconnected.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)
    
    async def broadcast_vulnerability(self, vuln_data: dict):
        """Broadcast new vulnerability event."""
        await self.broadcast({
            "event": "new_vulnerability",
            "data": vuln_data
        }, topic="vulnerabilities")
    
    async def broadcast_scan_progress(self, scan_id: int, progress: int, status: str):
        """Broadcast scan progress update."""
        await self.broadcast({
            "event": "scan_progress",
            "data": {
                "scan_id": scan_id,
                "progress": progress,
                "status": status
            }
        }, topic="scans")
    
    async def broadcast_scope_change(self, program_id: int, change_data: dict):
        """Broadcast scope change event."""
        await self.broadcast({
            "event": "scope_change",
            "data": {
                "program_id": program_id,
                **change_data
            }
        }, topic="scope")
    
    async def broadcast_alert(self, alert_data: dict):
        """Broadcast alert sent event."""
        await self.broadcast({
            "event": "alert_sent",
            "data": alert_data
        }, topic="alerts")


# Global connection manager instance
manager = ConnectionManager()
