from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...gateway import Gateway
    from ..models import Embed

class Interaction:
    def __init__(self, bot: "Gateway", payload: dict):
        self.bot = bot
        self.payload = payload
        self.id = payload.get("id")
        self.token = payload.get("token")

    async def reply(self, content: str, embed: 'Embed'):
        await self.bot.http.interaction_respond(content, id = self.id, token=self.token)