import asyncio

from .http import HTTPClient
from .gateway import Gateway
from .intents import Intents
from .impl import Guild, Embed, Channel
from .file import File
from .enums import Statuses
from .dispatcher import Dispatcher


class Client:
    def __init__(self, *, token: str, intents: Intents):
        self.intents = intents

        self.dispatcher = Dispatcher(self)
        self.http = HTTPClient(dispatcher=self.dispatcher, token=token, intents=intents.value)
        self.ws = self.http._gateway

    def listen(self, name: str):
        def inner(func):
            if name not in self.http._gateway.dispatcher.events:
                self.http._gateway.dispatcher.add_event(name)

            self.http._gateway.dispatcher.add_callback(name, func)

        return inner

    async def change_presence(self, status: Statuses):
        await self. ws._change_precense(status = status.value)

    async def fetch_channel(self, channel_id: int):
        return Channel(await self.http.get_channel(channel_id))

    async def fetch_guild(self, guild_id: int):
        
        return Guild(await self.http.get_guild(guild_id), self)

    async def send(self, channel_id: int, content: str, *, embed: Embed = None, files: list[File] = None):
        await self.http.send_message(channel_id, content=content, files=files)


    async def start(self):
        await self.http.start()

    def run(self):
        asyncio.run(self.start())
