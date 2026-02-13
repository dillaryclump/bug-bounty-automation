"""
Interactsh integration - OOB (Out-of-Band) interaction detection.
Critical for detecting blind vulnerabilities like SSRF, RCE, XXE, etc.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from src.utils.logging import get_logger

logger = get_logger(__name__)


class InteractshClient:
    """
    Interactsh client for OOB detection.
    
    Interactsh allows detecting vulnerabilities that don't directly
    respond but trigger external interactions (DNS, HTTP, SMTP, etc.).
    
    Example: Blind SSRF where the server makes a request to your
    Interactsh URL but doesn't return the result directly.
    """

    def __init__(
        self,
        server_url: str = "https://interact.sh",
        token: Optional[str] = None,
    ) -> None:
        """
        Initialize Interactsh client.
        
        Args:
            server_url: Interactsh server URL
            token: Optional auth token for private server
        """
        self.server_url = server_url.rstrip("/")
        self.token = token
        self.session_id = str(uuid.uuid4())
        self.correlation_id = str(uuid.uuid4())[:16]
        self.domain: Optional[str] = None
        self.client = httpx.AsyncClient(timeout=30.0)

    async def register(self) -> str:
        """
        Register with Interactsh server and get unique domain.
        
        Returns:
            Unique interaction domain (e.g., abc123def.interact.sh)
        """
        logger.info("Registering with Interactsh server...")

        try:
            response = await self.client.post(
                f"{self.server_url}/register",
                json={
                    "correlation-id": self.correlation_id,
                    "secret-key": self.session_id,
                },
                headers={"Authorization": self.token} if self.token else {},
            )
            response.raise_for_status()

            data = response.json()
            self.domain = data.get("correlation-id") + "." + data.get("server", "interact.sh")
            
            logger.info(f"✅ Registered Interactsh domain: {self.domain}")
            return self.domain

        except Exception as e:
            logger.error(f"Failed to register with Interactsh: {e}")
            raise

    async def poll_interactions(self, timeout: int = 60) -> List[Dict[str, Any]]:
        """
        Poll for interactions (DNS queries, HTTP requests, etc.).
        
        Args:
            timeout: How long to wait for interactions (seconds)
            
        Returns:
            List of interaction events
        """
        if not self.domain:
            raise ValueError("Must register() before polling")

        logger.info(f"Polling for interactions (timeout: {timeout}s)...")
        
        interactions = []
        end_time = asyncio.get_event_loop().time() + timeout

        while asyncio.get_event_loop().time() < end_time:
            try:
                response = await self.client.get(
                    f"{self.server_url}/poll",
                    params={
                        "correlation-id": self.correlation_id,
                        "secret": self.session_id,
                    },
                    headers={"Authorization": self.token} if self.token else {},
                )
                
                if response.status_code == 200:
                    data = response.json()
                    new_interactions = data.get("data", [])
                    
                    if new_interactions:
                        logger.info(f"🎯 Received {len(new_interactions)} interactions!")
                        interactions.extend(new_interactions)
                
                # Wait before next poll
                await asyncio.sleep(5)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    # No interactions yet
                    await asyncio.sleep(5)
                    continue
                else:
                    logger.error(f"Polling error: {e}")
                    break
            except Exception as e:
                logger.error(f"Polling failed: {e}")
                break

        logger.info(f"✅ Polling complete. Total interactions: {len(interactions)}")
        return interactions

    async def deregister(self) -> None:
        """Deregister from Interactsh server."""
        if not self.domain:
            return

        try:
            await self.client.post(
                f"{self.server_url}/deregister",
                json={
                    "correlation-id": self.correlation_id,
                    "secret-key": self.session_id,
                },
                headers={"Authorization": self.token} if self.token else {},
            )
            logger.info("Deregistered from Interactsh")
        except Exception as e:
            logger.debug(f"Deregister failed (non-critical): {e}")

    async def close(self) -> None:
        """Clean up resources."""
        await self.deregister()
        await self.client.aclose()

    def generate_payload(self, payload_type: str = "http") -> str:
        """
        Generate an Interactsh payload URL.
        
        Args:
            payload_type: Type of payload (http, dns, etc.)
            
        Returns:
            Formatted payload URL
        """
        if not self.domain:
            raise ValueError("Must register() first")

        if payload_type == "http":
            return f"http://{self.domain}"
        elif payload_type == "https":
            return f"https://{self.domain}"
        elif payload_type == "dns":
            return self.domain
        else:
            return self.domain

    @staticmethod
    def parse_interactions(
        interactions: List[Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parse and group interactions by type.
        
        Returns:
            Dict with keys: dns, http, smtp, etc.
        """
        grouped: Dict[str, List[Dict[str, Any]]] = {
            "dns": [],
            "http": [],
            "smtp": [],
            "ldap": [],
            "other": [],
        }

        for interaction in interactions:
            protocol = interaction.get("protocol", "other").lower()
            
            parsed = {
                "protocol": protocol,
                "unique_id": interaction.get("unique-id", ""),
                "full_id": interaction.get("full-id", ""),
                "timestamp": interaction.get("timestamp", ""),
                "raw_request": interaction.get("raw-request", ""),
                "raw_response": interaction.get("raw-response", ""),
                "remote_address": interaction.get("remote-address", ""),
            }

            # Add protocol-specific fields
            if protocol == "http":
                parsed.update({
                    "method": interaction.get("http-request", {}).get("method", ""),
                    "path": interaction.get("http-request", {}).get("path", ""),
                    "headers": interaction.get("http-request", {}).get("headers", {}),
                })
            elif protocol == "dns":
                parsed.update({
                    "dns_type": interaction.get("dns-request", {}).get("type", ""),
                    "question": interaction.get("dns-request", {}).get("question", ""),
                })

            if protocol in grouped:
                grouped[protocol].append(parsed)
            else:
                grouped["other"].append(parsed)

        return grouped


async def test_interactsh() -> None:
    """Test Interactsh connectivity."""
    client = InteractshClient()
    
    try:
        # Register
        domain = await client.register()
        print(f"✅ Registered: {domain}")
        
        # Generate test payloads
        print(f"HTTP Payload: {client.generate_payload('http')}")
        print(f"DNS Payload: {client.generate_payload('dns')}")
        
        # Poll for interactions (wait 10 seconds)
        print("\nWaiting 10 seconds for interactions...")
        print(f"Try: curl {client.generate_payload('http')}")
        
        interactions = await client.poll_interactions(timeout=10)
        
        if interactions:
            print(f"\n🎯 Received {len(interactions)} interactions!")
            parsed = InteractshClient.parse_interactions(interactions)
            for proto, items in parsed.items():
                if items:
                    print(f"{proto.upper()}: {len(items)} interactions")
        else:
            print("No interactions received (this is normal for a test)")
        
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_interactsh())
