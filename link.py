#!/usr/bin/env python3
"""link.py — the WebSocket 'phone line' between the PC brain and the robot.

What it does:
  - Keeps one always-open line (a WebSocket server) on port 8765.
  - Broadcasts every trigger event as JSON to all connected clients:
        {"type": "trigger", "label": "person", "confidence": 0.87, "time": "23:41:05"}
  - Answers simple text commands: {"cmd": "ping"} -> {"type": "pong"}.

Two ways to use it:
  1. Alone (demo):  python link.py
     Starts the server and sends one fake trigger every 3 seconds so you
     can test the line with test_client.py — no brain needed.
  2. With the brain:  python brain.py --link
     brain.py starts this same server in the background and broadcasts
     REAL triggers from the camera instead of fake ones.

The robot side (later, on the ESP32) connects to this same server as a
client and listens for trigger messages.
"""

import asyncio
import json
import threading
import time

from websockets.asyncio.server import serve

import config

CLIENTS = set()  # all currently connected clients


async def _handler(websocket):
    """One connected client: answer its commands, keep the line open."""
    CLIENTS.add(websocket)
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
            except ValueError:
                continue  # ignore messages that are not JSON
            if data.get("cmd") == "ping":
                await websocket.send(json.dumps({"type": "pong"}))
    finally:
        CLIENTS.discard(websocket)


async def broadcast_trigger(label, confidence):
    """Send one trigger event to every connected client."""
    if not CLIENTS:
        return
    payload = json.dumps({
        "type": "trigger",
        "label": label,
        "confidence": round(float(confidence), 2),
        "time": time.strftime("%H:%M:%S"),
    })
    await asyncio.gather(
        *[client.send(payload) for client in list(CLIENTS)],
        return_exceptions=True,
    )


async def _demo_trigger_loop():
    """Demo mode only: one fake trigger every 3 seconds, so test_client.py
    has something to receive when no real brain is connected."""
    labels = ["person", "car", "dog"]
    i = 0
    while True:
        await asyncio.sleep(3)
        await broadcast_trigger(labels[i % len(labels)], 0.90 - (i % 3) * 0.05)
        i += 1


async def _serve(port, demo=False):
    async with serve(_handler, "0.0.0.0", port):
        print(f"Link server listening on ws://localhost:{port}")
        if demo:
            print("Demo mode: sending one fake trigger every 3 seconds.")
            print("Run this in another terminal to test it:  python test_client.py")
            await _demo_trigger_loop()
        else:
            # Run forever, waiting for clients and triggers.
            await asyncio.get_running_loop().create_future()


class LinkHandle:
    """Handle returned by start_link_server_in_thread().

    Lets normal (non-async) code like brain.py send a trigger with one call:
        link.send_trigger("person", 0.87)
    """

    def __init__(self, loop):
        self._loop = loop

    def send_trigger(self, label, confidence):
        if self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                broadcast_trigger(label, confidence), self._loop)


def start_link_server_in_thread(port):
    """Start the server in a background thread (no demo triggers).

    Used by brain.py --link so the brain can broadcast REAL triggers.
    """
    loop = asyncio.new_event_loop()

    def _run():
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_serve(port, demo=False))

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return LinkHandle(loop)


if __name__ == "__main__":
    # Standalone demo: server + one fake trigger every 3 seconds.
    asyncio.run(_serve(config.LINK_PORT, demo=True))
