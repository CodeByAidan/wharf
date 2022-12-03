from __future__ import annotations

import asyncio
import datetime
import json
import logging
import random
import traceback
import zlib
from sys import platform as _os
from typing import TYPE_CHECKING, Any, Optional, Union

from aiohttp import ClientSession, ClientWebSocketResponse, WSMsgType

from .dispatcher import Dispatcher
from .errors import WebsocketClosed

if TYPE_CHECKING:
    from .http import HTTPClient


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
        heartbeat_interval: int

    def __init__(self, dispatcher: Dispatcher, http: HTTPClient):
        self.http = http
        self.token = self.http._token
        self.intents = self.http._intents
        self.api_version = 10
        self.gw_url: str = f"wss://gateway.discord.gg/?v={self.api_version}&encoding=json&compress=zlib-stream"
        self._last_sequence: Optional[int] = None
        self._first_heartbeat = True
        self.dispatcher = dispatcher
        self._decompresser = zlib.decompressobj()
        self.loop = asyncio.get_event_loop()
        self.session: Optional[ClientSession] = None
        self.ws: Optional[ClientWebSocketResponse] = None

    def _decompress_msg(self, msg: Union[str, bytes]):
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
                "properties": {"os": _os, "browser": "wharf", "device": "wharf"},
                "compress": True,
            },
        }

        return payload

    @property
    def resume_payload(self):
        payload = {
            "op": OPCodes.resume,
            "d": {
                "token": self.token,
                "seq": self._last_sequence,
                "session_id": self.session_id,
            },
        }
        return payload

    @property
    def ping_payload(self):
        payload = {"op": OPCodes.heartbeat, "d": self._last_sequence}

        return payload

    async def keep_heartbeat(self):
        jitters = self.heartbeat_interval
        if self._first_heartbeat:
            jitters *= random.uniform(1.0, 0.0)
            self._first_heartbeat = False
            
        await self.ws.send_json(self.ping_payload)
        await asyncio.sleep(jitters)
        asyncio.create_task(self.keep_heartbeat())

    async def send(self, data: dict):
        await self.ws.send_json(data)
        _log.info("Sent json to the gateway successfully")
        

    async def _change_precense(self, *, status: str):
        activities = [] # Placeholder whilst i do more testing with presences uwu

        payload = {
            "op": OPCodes.presence_update,
            "d": {
                "status": status,
                "afk": False,
                "since": 0.0,
                "activities": activities
            }
        }

        await self.ws.send_json(payload)


    async def connect(self, *, reconnect: bool = False):
        if not self.session:
            self.session = ClientSession()

        self.ws = await self.session.ws_connect(self.gw_url)

        while True:

            msg = await self.ws.receive()

            if msg.type in (WSMsgType.BINARY, WSMsgType.TEXT):
                data: Union[Any, str] = None
                if msg.type == WSMsgType.BINARY:
                    data = self._decompress_msg(msg.data)
                elif msg.type == WSMsgType.TEXT:
                    data = msg.data

                data = json.loads(data)

            self._last_sequence = data["s"]

            if data["op"] == OPCodes.hello:
                self.heartbeat_interval = data["d"]["heartbeat_interval"] / 1000

                if reconnect:
                    await self.send(self.resume_payload)
                else:
                    await self.send(self.identify_payload)

                asyncio.create_task(self.keep_heartbeat())

            if data["op"] == OPCodes.heartbeat:
                await self.send(self.ping_payload)

            if data["op"] == OPCodes.dispatch:
                
                if data["t"] == "READY":
                    self.session_id = data["d"]["session_id"]
                
                event_data = data["d"]

                if data["t"].lower() not in self.dispatcher.events.keys():
                    continue

                if data['t'].lower() == 'ready':
                    self.dispatcher.dispatch(data["t"].lower())
                else:

                    self.dispatcher.dispatch(data["t"].lower(), event_data)

            if data["op"] == OPCodes.heartbeat_ack:
                self._last_heartbeat_ack = datetime.datetime.now()

            if data["op"] == OPCodes.reconnect:
                _log.info(data)
                await self.ws.close(code=4001)
                await self.connect(reconnect=True)

            if data["op"] == OPCodes.invalid_session:
                await self.ws.close(code=4001)
                _log.info("invalid?")
                break

            elif msg.type == WSMsgType.CLOSE:
                raise WebsocketClosed(msg.data, msg.extra)

    @property
    def is_closed(self):
        if not self.ws:
            return False

        return self.ws.closed
