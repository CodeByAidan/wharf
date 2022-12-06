from __future__ import annotations
from typing import TYPE_CHECKING, Optional, List
from enum import Enum

import discord_typings as dt

if TYPE_CHECKING:
    from ...client import Client
    from ..models import Embed

class InteractionOptionType(Enum):
    string = 3
    number = 4
    user = 6
    channel = 7
    role = 8
    attachment = 10

class Interaction:
    def __init__(self, bot: Client, payload: dict):
        self.bot = bot
        self.payload = payload
        self.id = payload.get("id")
        self.token = payload.get("token")
        self.channel_id = payload.get("channel_id")
        self.command = InteractionCommand._from_json(payload)


    async def reply(self, content: str, embed: Embed = None):
        await self.bot.http.interaction_respond(content, id = self.id, token=self.token)


class InteractionCommand:
    def __init__(self, *, name: str, description: Optional[str] = None):
        self.name = name
        self.description = description
        self.options = []

    def add_options(self, *, name: str, type: InteractionOptionType,  description: str, choices: Optional[List] = None, required: bool = True):
        data = {
            "name": name,
            "description": description,
            "type": type.value,
            "required": required,
        }

        if choices:
            data["choices"] = choices


        self.options.append(data)


    def _to_json(self):
        payload = {
            "name": self.name,
            "description": self.description,
            "type": 1,
        }

        if self.options:
            payload["options"] = self.options

        return payload

    @classmethod
    def _from_json(cls, payload: dt.InteractionCreateData):
        name = payload['data']['name']
        description = payload['data'].get("description", "")

        return cls(name=name, description=description)