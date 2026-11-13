#!/usr/bin/env python3
"""test_client.py — proves the 'phone line' works.

Steps:
  1. In one terminal, start the server:   python link.py
  2. In another terminal, run this test:  python test_client.py

What it does: connects, waits for one trigger, sends a ping,
prints everything it got, and says OK if the ping/pong round-trip worked.
"""

import asyncio
import json
import sys

from websockets.asyncio.client import connect

import config

URI = f"ws://localhost:{config.LINK_PORT}"


async def main():
    print(f"Connecting to {URI} ...")
    try:
        async with connect(URI) as ws:
            print("Connected. Waiting for one trigger ...")
            while True:
                raw = await asyncio.wait_for(ws.recv(), timeout=15)
                msg = json.loads(raw)
                if msg.get("type") == "trigger":
                    print(f"Got trigger: {msg}")
                    break
                print(f"(ignored other message: {msg})")

            print('Sending {"cmd": "ping"} ...')
            await ws.send(json.dumps({"cmd": "ping"}))
            raw = await asyncio.wait_for(ws.recv(), timeout=5)
            msg = json.loads(raw)
            print(f"Got reply: {msg}")
            assert msg.get("type") == "pong", f"expected pong, got {msg!r}"
            print("OK — phone line works: trigger received + ping/pong round-trip.")
    except (ConnectionRefusedError, OSError):
        print("ERROR: could not connect. Is link.py running?")
        print("  Terminal 1:  python link.py")
        print("  Terminal 2:  python test_client.py")
        sys.exit(1)
    except asyncio.TimeoutError:
        print("ERROR: timed out waiting for a message. Is link.py in demo mode?")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
