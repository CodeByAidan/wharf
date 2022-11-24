from .http import HTTPClient
from .objects import Embed
from .intents import Intents
import asyncio

class Client:
    def __init__(self, *, token: str, intents: Intents):
        self.intents = intents

        self.http = HTTPClient(token=token, intents=intents.value)

    def listen(self, name: str):
        def inner(func):
            if name not in self.http._gateway.dispatcher.events:
                self.http._gateway.dispatcher.add_event(name)

            self.http._gateway.dispatcher.add_callback(name, func)

        return inner

    async def send(self, channel_id: int, content: str, *, embed: Embed = None):
        await self.http.send_message(channel_id, content, embed)
    
    async def start(self):
        await self.http.start()

    def run(self):
        asyncio.run(self.start())