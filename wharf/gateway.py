from __future__ import annotations
import asyncio
import random
from aiohttp import ClientSession, ClientWebSocketResponse,  WSMsgType
from typing import TYPE_CHECKING, Optional, Union, Any  
import logging
from sys import platform as _os
import json
import zlib
from .errors import WebsocketClosed
from .dispatcher import Dispatcher
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
        ws: ClientWebSocketResponse
        heartbeat_interval: int

    def __init__(self, http: HTTPClient, *, token: str, intents: int):
        self.http = http
        self.session: Optional[ClientSession] = None
        self.token = token
        self.intents = intents
        self.api_version = 10
        self.gw_url: str = f"wss://gateway.discord.gg/?v={self.api_version}&encoding=json&compress=zlib-stream"
        self._last_sequence: Optional[int] = None
        self._first_heartbeat = True
        self.dispatcher = Dispatcher()
        self._decompresser = zlib.decompressobj()

    def _decompress_msg(self, msg: Union[str, bytes]):
        ZLIB_SUFFIX = b"\x00\x00\xff\xff"

        out_str: str = ""

        # Message should be compressed
        if len(msg) < 4 or msg[-4:] != ZLIB_SUFFIX:
            return out_str

        buff = self._decompresser.decompress(msg)
        out_str = buff.decode("utf-8")
        return out_str

    def listen(self, name: str):
        def inner(func):
            if name not in self.dispatcher.events:
                self.dispatcher.add_event(name)

            self.dispatcher.add_callback(name, func)
                
        
        return inner

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
                "token": self.token,
                "seq": self._last_sequence,
                "session_id": self.session_id,
            },
        }

    @property
    def ping_payload(self):
        payload = {"op": OPCodes.heartbeat, "d": self._last_sequence}

        return payload

    async def keep_heartbeat(self):
        jitters = self.heartbeat_interval
        if self._first_heartbeat:
            jitters = self.heartbeat_interval * float(random.randint(0, 1))
            self._first_heartbeat = False

        await asyncio.sleep(jitters / 1000)
        asyncio.create_task(self.keep_heartbeat())

    async def connect(self, *, reconnect: bool = False):
        try:
            if not self.session:
                self.session = ClientSession()

            self.ws = await self.session.ws_connect(self.gw_url)
            _log.info("Connected to gateway")

            while True:
                async for msg in self.ws:
                    if msg.type in (WSMsgType.BINARY, WSMsgType.TEXT):
                        data: Union[Any, str] = None
                        if msg.type == WSMsgType.BINARY: 
                            data = self._decompress_msg(msg.data)
                        elif msg.type == WSMsgType.TEXT:  
                            data = msg.data  

                        data = json.loads(data)

                    self._last_sequence = data["s"]

                    if data["op"] == OPCodes.hello:
                        self.heartbeat_interval = data["d"]["heartbeat_interval"]

                        if reconnect:
                            await self.ws.send_json(self.resume_payload)
                        else:
                            await self.ws.send_json(self.identify_payload)

                        await self.ws.send_json(self.ping_payload)

                        self.heartbeat_task = asyncio.create_task(self.keep_heartbeat())


                    elif data["op"] == OPCodes.heartbeat: # From what ive seen, this is rare but better handle it for whenever it does come.
                        await self.ws.send_json(self.ping_payload)

                    elif data["op"] == OPCodes.dispatch:
                        event_data = data["d"]
                        _log.info(data["t"])

                        if data["t"] == "READY":
                            self.session_id = data['d']['session_id']
                            self.resume_gateway_url = data['d']['resume_gateway_url']
                        
                        if data['t'].lower() not in self.dispatcher.events:
                            continue
                        
                        self.dispatcher.dispatch(data["t"].lower(), event_data)
    
                    elif data["op"] == OPCodes.heartbeat_ack:
                        _log.info("Heartbeat Awknoledged!")

                    elif data['op'] == OPCodes.reconnect:
                        _log.info(data)
                        await self.ws.close(code=4001)
                        await self.connect(reconnect=True)
                    
                    elif data["op"] == OPCodes.invalid_session:
                        _log.info(data)
                        await self.ws.close(code=4001)
                        break

                    elif msg.type == WSMsgType.CLOSE:
                        _log.info(f"{msg.data} {msg.extra}")
        except Exception as e:
            print(e)
           
    @property
    def is_closed(self):
        if not self.ws:
            return False

        return self.ws.closed
