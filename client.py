import asyncio
import json
import pygame
import websockets

WIDTH, HEIGHT = 800, 600
WORLD_WIDTH, WORLD_HEIGHT = 1000, 1000

class Client:
    def __init__(self, uri):
        self.uri = uri
        self.players = {}
        self.ais = {}
        self.self_id = None
        self.x = 0
        self.y = 0
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption('Open World Strategy')
        self.clock = pygame.time.Clock()

    async def send_move(self, websocket, move):
        await websocket.send(json.dumps({'move': move}))

    async def run(self):
        async with websockets.connect(self.uri) as websocket:
            # Receive initial state
            async def receiver():
                async for message in websocket:
                    data = json.loads(message)
                    self.players = data.get('players', {})
                    self.ais = data.get('ais', {})
                    self.self_id = data.get('self_id')
                    # Update own position
                    if self.self_id in self.players:
                        self.x = self.players[self.self_id]['x']
                        self.y = self.players[self.self_id]['y']

            recv_task = asyncio.create_task(receiver())
            running = True
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_UP:
                            await self.send_move(websocket, 'up')
                        elif event.key == pygame.K_DOWN:
                            await self.send_move(websocket, 'down')
                        elif event.key == pygame.K_LEFT:
                            await self.send_move(websocket, 'left')
                        elif event.key == pygame.K_RIGHT:
                            await self.send_move(websocket, 'right')
                # Draw world
                self.screen.fill((0, 0, 0))
                # Translate world so player is centered
                offset_x = WIDTH // 2 - self.x
                offset_y = HEIGHT // 2 - self.y
                # Draw players
                for ws_id, pos in self.players.items():
                    color = (255, 0, 0) if ws_id == self.self_id else (0, 255, 0)
                    pygame.draw.circle(
                        self.screen,
                        color,
                        (pos['x'] + offset_x, pos['y'] + offset_y),
                        10
                    )
                for ai_id, pos in self.ais.items():
                    pygame.draw.circle(
                        self.screen,
                        (0, 128, 255),
                        (pos['x'] + offset_x, pos['y'] + offset_y),
                        pos.get('size', 30)
                    )
                pygame.display.flip()
                self.clock.tick(60)
            recv_task.cancel()

if __name__ == '__main__':
    client = Client('ws://localhost:8765')
    asyncio.run(client.run())
