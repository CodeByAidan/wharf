import asyncio
from typing import List

from .dispatcher import Dispatcher
from .enums import Statuses
from .file import File
from .http import HTTPClient
from .impl import Channel, Embed, Guild, InteractionCommand
from .intents import Intents


class Client:
    def __init__(self, *, token: str, intents: Intents):
        self.intents = intents

        self.dispatcher = Dispatcher(self)
        self.http = HTTPClient(
            dispatcher=self.dispatcher, token=token, intents=intents.value
        )
        self.ws = self.http._gateway
        self._slash_commands = []

    def listen(self, name: str):
        def inner(func):
            if name not in self.dispatcher.events:
                self.dispatcher.subscribe(name, func)
            else:
                self.dispatcher.add_callback(name, func)

        return inner

    async def change_presence(self, status: Statuses):
        await self.ws._change_precense(status=status.value)

    async def fetch_channel(self, channel_id: int):
        return Channel(await self.http.get_channel(channel_id))

    async def fetch_guild(self, guild_id: int):

        return Guild(await self.http.get_guild(guild_id), self)

    async def register_app_command(self, command: InteractionCommand):
        await self.http.register_app_commands(command)
        self._slash_commands.append(command._to_json())

    async def start(self):
        await self.http.start()

    async def close(self):
        await self.http._session.close()
        await self.ws.ws.close()

        api_commands = await self.http.get_app_commands()

        for command in api_commands:
            for cached_command in self._slash_commands:
                if command["name"] != cached_command["name"]:
                    await self.http.delete_app_command(command)
                continue

    def run(self):
        try:
            asyncio.run(self.start())
        except (KeyboardInterrupt, RuntimeError):
            asyncio.run(self.close())
