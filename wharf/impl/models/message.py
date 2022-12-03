import discord_typings as dt
from .user import User

class Message:
    def __init__(self, data: dt.MessageCreateData):
        self._from_data(data)


    def _from_data(self, message: dt.MessageData):
        self.content = message.get("content")
        self.author = User(message['author'])
        self.channel_id = message['channel_id']