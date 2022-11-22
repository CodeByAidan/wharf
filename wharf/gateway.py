from __future__ import annotations
import asyncio
import random
from aiohttp import ClientSession, ClientWebSocketResponse,  WSMsgType
from typing import TYPE_CHECKING, Optional
import logging
from sys import platform as _os
import json
import zlib
import traceback
from .errors import WebsocketClosed


logging.basicConfig(level=logging.INFO)
_log = logging.getLogger(__name__)


class OPCodes:
    dispatch = 0
    heartbeat = 1
    identify = 2
    presence_update = 3
    voice_state_update = 4
    resume = 6
    reconnect = 7
    request_guild_members = 8
    invalid_session = 9
    hello = 10
    heartbeat_ack = 11


class Gateway:
    if TYPE_CHECKING:
        ws: ClientWebSocketResponse
        heartbeat_interval: int
        resume_gw_url: str

    def __init__(self, *, token: str, intents: int):
        self.session: Optional[ClientSession] = None
        self.token = token
        self.intents = intents
        self.api_version = 10
        self.gw_url: str = f"wss://gateway.discord.gg/?v={self.api_version}&encoding=json&compress=zlib-stream"
        self._last_sequence: Optional[int] = None
        self._first_heartbeat = True

        self._decompresser = zlib.decompressobj()

    def _decompress_msg(self, msg: bytes):
        ZLIB_SUFFIX = b"\x00\x00\xff\xff"

        out_str: str = ""

        # Message should be compressed
        if len(msg) < 4 or msg[-4:] != ZLIB_SUFFIX:
            return out_str

        buff = self._decompresser.decompress(msg)
        out_str = buff.decode("utf-8")
        return out_str

    @property
    def identify_payload(self):
        payload = {
            "op": OPCodes.identify,
            "d": {
                "token": self.token,
                "intents": self.intents,
                "properties": {"os": _os, "browser": "rtest", "device": "rtest"},
                "compress": True,
            },
        }

        return payload

    @property
    def resume_payload(self):
        return {
            "op": OPCodes.resume,
            "d": {
                "token": self._token,
                "seq": self._last_sequence,
                "session_id": self._session_id,
            },
        }

    @property
    def ping_payload(self):
        payload = {"op": OPCodes.heartbeat, "d": self._last_sequence}

        return payload

    async def connect(self, *, reconnect: bool = False):
        if not self.session:
            self.session = ClientSession()

        self.ws = await self.session.ws_connect(self.gw_url)
        _log.info("Connected to gateway")

        while True:
            async for msg in self.ws:
                data = json.loads(self._decompress_msg(msg.data))
                self._last_sequence = data["s"]

                if data["op"] == OPCodes.hello:
                    self.heartbeat_interval = data["d"]["heartbeat_interval"]

                    await self.ws.send_json(self.identify_payload)

                    await self.ws.send_json(self.ping_payload)
                    jitters = self.heartbeat_interval
                    if self._first_heartbeat:
                        jitters = self.heartbeat_interval * float(random.randint(0, 1))
                        self._first_heartbeat = False

                    await asyncio.sleep(jitters / 1000)

                elif data["op"] == OPCodes.heartbeat:
                    await self.ws.send_json(self.ping_payload)

                elif data["op"] == OPCodes.dispatch:
                    if data["t"] == "READY":
                        self.session_id = data['d']['session_id']
                        self.resume_gateway_url = data['d']['resume_gateway_url']

                elif data["op"] == OPCodes.heartbeat_ack:
                    _log.info("Heartbeat Awknoledged!")

                elif data['op'] == OPCodes.reconnect:
                    await self.ws.close(code=4001)
                    await self.connect(reconnect=True)
                elif data["op"] == OPCodes.invalid_session:
                    await self.ws.close(code=4001)
                    break
            
                elif msg.type == WSMsgType.CLOSE:
                    raise WebsocketClosed(msg.data, msg.extras)

    @property
    def is_closed(self):
        if not self.ws:
            return False

        return self.ws.closed
