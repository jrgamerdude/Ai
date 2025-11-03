import asyncio
import json
import random
import uuid
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, Optional

import websockets

WIDTH = 1000
HEIGHT = 1000


@dataclass
class Command:
    """Represents a command that can be executed by the server."""

    handler: Callable[[websockets.WebSocketServerProtocol, dict], Awaitable[None]]
    description: str


class CommandRegistry:
    """Registry used to keep track of commands that the server supports."""

    def __init__(self) -> None:
        self._commands: Dict[str, Command] = {}

    def register(
        self,
        name: str,
        handler: Callable[[websockets.WebSocketServerProtocol, dict], Awaitable[None]],
        *,
        description: str,
    ) -> None:
        self._commands[name] = Command(handler=handler, description=description)

    def get(self, name: str) -> Optional[Command]:
        return self._commands.get(name)

    def help_text(self) -> Dict[str, str]:
        return {name: command.description for name, command in sorted(self._commands.items())}


class MultiPurposeServer:
    """WebSocket server that supports an extensible command system."""

    def __init__(self, width: int = WIDTH, height: int = HEIGHT) -> None:
        self.width = width
        self.height = height
        self.players: Dict[websockets.WebSocketServerProtocol, dict] = {}
        self.commands = CommandRegistry()
        self._register_default_commands()

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------
    async def handler(self, websocket: websockets.WebSocketServerProtocol) -> None:
        player_id = uuid.uuid4().hex
        player_state = {
            "id": player_id,
            "x": random.randint(0, self.width),
            "y": random.randint(0, self.height),
        }
        self.players[websocket] = player_state
        await self._send(
            websocket,
            {
                "type": "welcome",
                "playerId": player_id,
                "commands": self.commands.help_text(),
            },
        )
        await self._broadcast_state()

        try:
            async for message in websocket:
                await self._handle_message(websocket, message)
        finally:
            self.players.pop(websocket, None)
            await self._broadcast_state()

    async def _handle_message(self, websocket: websockets.WebSocketServerProtocol, message: str) -> None:
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            await self._send_error(websocket, "Received invalid JSON data.")
            return

        if not isinstance(data, dict):
            await self._send_error(websocket, "Messages must be JSON objects.")
            return

        command_name = data.get("type") or data.get("command")
        if not command_name and "move" in data:
            command_name = "move"

        if not command_name:
            await self._send_error(websocket, "Missing command type in message.")
            return

        if command_name == "help":
            await self._send(
                websocket,
                {"type": "help", "commands": self.commands.help_text()},
            )
            return

        command = self.commands.get(command_name)
        if not command:
            await self._send_error(websocket, f"Unknown command '{command_name}'.")
            return

        await command.handler(websocket, data)

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------
    def _register_default_commands(self) -> None:
        self.commands.register(
            "move",
            self._command_move,
            description="Move the player. Use the 'direction' or 'move' field with up/down/left/right.",
        )
        self.commands.register(
            "ping",
            self._command_ping,
            description="Check connectivity. Optionally include an 'echo' field to be returned.",
        )
        self.commands.register(
            "state",
            self._command_state,
            description="Receive the latest player positions without broadcasting to others.",
        )

    async def _command_move(self, websocket: websockets.WebSocketServerProtocol, data: dict) -> None:
        player = self.players.get(websocket)
        if not player:
            return

        direction = data.get("direction") or data.get("move")
        if not direction:
            await self._send_error(websocket, "Missing 'direction' for move command.")
            return

        dx, dy = 0, 0
        if direction == "up":
            dy = -5
        elif direction == "down":
            dy = 5
        elif direction == "left":
            dx = -5
        elif direction == "right":
            dx = 5
        else:
            await self._send_error(websocket, f"Unknown move direction '{direction}'.")
            return

        player["x"] = max(0, min(self.width, player["x"] + dx))
        player["y"] = max(0, min(self.height, player["y"] + dy))
        await self._broadcast_state()

    async def _command_ping(self, websocket: websockets.WebSocketServerProtocol, data: dict) -> None:
        payload = {"type": "pong"}
        if "echo" in data:
            payload["echo"] = data["echo"]
        await self._send(websocket, payload)

    async def _command_state(self, websocket: websockets.WebSocketServerProtocol, data: dict) -> None:
        await self._send(websocket, self._build_state_message())

    # ------------------------------------------------------------------
    # Messaging helpers
    # ------------------------------------------------------------------
    async def _send(self, websocket: websockets.WebSocketServerProtocol, payload: dict) -> None:
        try:
            await websocket.send(json.dumps(payload))
        except websockets.ConnectionClosed:
            pass

    async def _broadcast_state(self) -> None:
        if not self.players:
            return
        message = json.dumps(self._build_state_message())
        await asyncio.gather(
            *(
                self._safe_send(websocket, message)
                for websocket in list(self.players.keys())
            ),
            return_exceptions=True,
        )

    async def _safe_send(self, websocket: websockets.WebSocketServerProtocol, message: str) -> None:
        try:
            await websocket.send(message)
        except websockets.ConnectionClosed:
            self.players.pop(websocket, None)

    async def _send_error(self, websocket: websockets.WebSocketServerProtocol, message: str) -> None:
        await self._send(websocket, {"type": "error", "message": message})

    def _build_state_message(self) -> dict:
        return {
            "type": "state",
            "players": {
                player_state["id"]: {"x": player_state["x"], "y": player_state["y"]}
                for player_state in self.players.values()
            },
        }


async def main() -> None:
    server = MultiPurposeServer()
    async with websockets.serve(server.handler, "0.0.0.0", 8765):
        print("Server started on port 8765")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
