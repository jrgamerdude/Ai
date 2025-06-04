import asyncio
import json
import random
import websockets

WIDTH = 1000
HEIGHT = 1000

players = {}

async def notify_state():
    state = {str(id(ws)): {'x': pos[0], 'y': pos[1]} for ws, pos in players.items()}
    if players:
        msg = json.dumps({'players': state})
        await asyncio.wait([ws.send(msg) for ws in players])

async def handler(websocket):
    # Assign random position
    x = random.randint(0, WIDTH)
    y = random.randint(0, HEIGHT)
    players[websocket] = [x, y]
    await notify_state()
    try:
        async for message in websocket:
            data = json.loads(message)
            dx, dy = 0, 0
            if data.get('move') == 'up':
                dy = -5
            elif data.get('move') == 'down':
                dy = 5
            elif data.get('move') == 'left':
                dx = -5
            elif data.get('move') == 'right':
                dx = 5
            pos = players[websocket]
            pos[0] = max(0, min(WIDTH, pos[0] + dx))
            pos[1] = max(0, min(HEIGHT, pos[1] + dy))
            await notify_state()
    finally:
        del players[websocket]
        await notify_state()

async def main():
    async with websockets.serve(handler, '0.0.0.0', 8765):
        print('Server started on port 8765')
        await asyncio.Future()  # run forever

if __name__ == '__main__':
    asyncio.run(main())
