import asyncio
import json
import random
import websockets

WIDTH = 1000
HEIGHT = 1000
AI_ID = "ai_boss"

players = {}
connections = {}
ai_state = {"x": WIDTH // 2, "y": HEIGHT // 2, "size": 40}
ai_target = {"x": WIDTH // 2, "y": HEIGHT // 2}


def clamp_position(value, min_value, max_value):
    return max(min_value, min(max_value, value))


async def notify_state():
    if not connections:
        return
    state = {player_id: {"x": pos[0], "y": pos[1]} for player_id, pos in players.items()}
    msg_base = {"players": state, "ais": {AI_ID: ai_state}}
    tasks = []
    for websocket, player_id in connections.items():
        payload = dict(msg_base)
        payload["self_id"] = player_id
        tasks.append(websocket.send(json.dumps(payload)))
    if tasks:
        await asyncio.gather(*tasks)


async def handler(websocket):
    player_id = str(id(websocket))
    x = random.randint(0, WIDTH)
    y = random.randint(0, HEIGHT)
    players[player_id] = [x, y]
    connections[websocket] = player_id
    await notify_state()
    try:
        async for message in websocket:
            data = json.loads(message)
            dx, dy = 0, 0
            if data.get("move") == "up":
                dy = -5
            elif data.get("move") == "down":
                dy = 5
            elif data.get("move") == "left":
                dx = -5
            elif data.get("move") == "right":
                dx = 5
            pos = players[player_id]
            pos[0] = clamp_position(pos[0] + dx, 0, WIDTH)
            pos[1] = clamp_position(pos[1] + dy, 0, HEIGHT)
            await notify_state()
    finally:
        players.pop(player_id, None)
        connections.pop(websocket, None)
        await notify_state()


async def ai_loop():
    global ai_target
    while True:
        if abs(ai_state["x"] - ai_target["x"]) < 5 and abs(ai_state["y"] - ai_target["y"]) < 5:
            ai_target = {"x": random.randint(0, WIDTH), "y": random.randint(0, HEIGHT)}
        step = 3
        if ai_state["x"] < ai_target["x"]:
            ai_state["x"] = clamp_position(ai_state["x"] + step, 0, WIDTH)
        elif ai_state["x"] > ai_target["x"]:
            ai_state["x"] = clamp_position(ai_state["x"] - step, 0, WIDTH)
        if ai_state["y"] < ai_target["y"]:
            ai_state["y"] = clamp_position(ai_state["y"] + step, 0, HEIGHT)
        elif ai_state["y"] > ai_target["y"]:
            ai_state["y"] = clamp_position(ai_state["y"] - step, 0, HEIGHT)
        await notify_state()
        await asyncio.sleep(0.1)


async def main():
    async with websockets.serve(handler, "0.0.0.0", 8765):
        print("Server started on port 8765")
        asyncio.create_task(ai_loop())
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
