from typing import TYPE_CHECKING

import discord_typings as dt

from .member import Member

if TYPE_CHECKING:
    from ...client import Client


class Guild:
    def __init__(self, data: dt.GuildData, bot: "Client"):
        self._from_data(data)
        self.__bot = bot

    def _from_data(self, guild: dt.GuildData):
        self.name = guild.get("name")
        self.id = guild.get("id")
        self.icon_hash = guild.get("icon")

    async def fetch_member(self, user: int):
        return Member(await self.__bot.http.get_member(user, self.id))

    async def ban(
        self,
        user_id: int,
        *,
        reason: str,
    ):
        await self.__bot.http.ban(self.id, user_id, reason)
