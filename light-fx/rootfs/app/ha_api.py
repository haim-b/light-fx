"""Home Assistant API integration for Light FX addon."""
import logging
import json
from typing import Dict, Any, Optional

import aiohttp

_LOGGER = logging.getLogger(__name__)

class HomeAssistantAPI:
    """Interface to Home Assistant's API."""
    
    def __init__(self, host: str, token: str, port: int = 8123):
        """Initialize the API client."""
        self.host = host
        self.token = token
        self.port = port
        self.base_url = f"http://{host}:{port}/api"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        self.websocket = None
        self.id_counter = 0

    async def get_state(self, entity_id: str) -> Dict[str, Any]:
        """Get the state of an entity."""
        url = f"{self.base_url}/states/{entity_id}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    text = await response.text()
                    raise Exception(f"Failed to get state: {text}")

    async def call_service(self, domain: str, service: str, data: Dict[str, Any]):
        """Call a Home Assistant service."""
        url = f"{self.base_url}/services/{domain}/{service}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.post(url, json=data) as response:
                if response.status != 200:
                    text = await response.text()
                    raise Exception(f"Failed to call service: {text}")

    async def connect_websocket(self):
        """Connect to Home Assistant websocket API."""
        url = f"ws://{self.host}:{self.port}/api/websocket"
        self.websocket = await aiohttp.ClientSession().ws_connect(url)
        
        # Send auth message
        auth_msg = {
            "type": "auth",
            "access_token": self.token
        }
        await self.websocket.send_json(auth_msg)
        
        # Wait for auth_ok message
        msg = await self.websocket.receive_json()
        if msg["type"] != "auth_ok":
            raise Exception("Authentication failed")

    async def subscribe_to_events(self, event_type: str, callback):
        """Subscribe to Home Assistant events."""
        if not self.websocket:
            await self.connect_websocket()
            
        self.id_counter += 1
        sub_msg = {
            "id": self.id_counter,
            "type": "subscribe_events",
            "event_type": event_type
        }
        await self.websocket.send_json(sub_msg)
        
        # Handle the subscription confirmation
        msg = await self.websocket.receive_json()
        if msg["type"] != "result" or not msg.get("success"):
            raise Exception("Failed to subscribe to events")

        # Start listening for events
        while True:
            msg = await self.websocket.receive_json()
            if msg["type"] == "event":
                await callback(msg["event"])

    async def close(self):
        """Close the websocket connection."""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
