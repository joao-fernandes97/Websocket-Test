import asyncio
import websockets

async def echo(websocket):
    async for message in websocket:
        print("MSG from Unity:", message)
        await websocket.send("Python received: " + message)

async def main():
    async with websockets.serve(echo, "localhost", 3000):
        print("Python Websocket server running on ws://localhost:3000")
        await asyncio.Future()

asyncio.run(main())