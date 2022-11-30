import asyncio

from .http import HTTPClient
from .gateway import Gateway
from .intents import Intents
from .impl import Guild, Embed
from .file import File
from .enums import Statuses


class Client:
    def __init__(self, *, token: str, intents: Intents):
        self.intents = intents

        self._http = HTTPClient(token=token, intents=intents.value)
        self._ws = self._http._gateway

    def listen(self, name: str):
        def inner(func):
            if name not in self._http._gateway.dispatcher.events:
                self._http._gateway.dispatcher.add_event(name)

            self._http._gateway.dispatcher.add_callback(name, func)

        return inner

    async def change_presence(self, status: Statuses):
        await self._ws._change_precense(status = status.value)

    async def fetch_guild(self, guild_id: int):
        
        return Guild(await self._http.get_guild(guild_id))

    async def send(self, channel_id: int, content: str, *, embed: Embed = None, files: list[File] = None):
        await self._http.send_message(channel_id, content=content, files=files)


    async def start(self):
        await self._http.start()

    def run(self):
        asyncio.run(self.start())
