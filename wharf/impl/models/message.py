import discord_typings as dt

from ...client import Client
from .user import User


class Message:
    def __init__(self, data: dt.MessageCreateData, bot: Client):
        self._from_data(data)
        self.bot = bot

    def _from_data(self, message: dt.MessageData):
        self.content = message.get("content")
        self.author = User(message["author"])
        self.channel_id = message["channel_id"]

    async def send(self, content: str):
        msg = await self.bot.http.send_message(self.channel_id, content=content)
        return Message(msg, self.bot)
