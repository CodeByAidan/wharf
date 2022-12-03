from __future__ import annotations
import discord_typings as dt

from typing import Optional

from ...asset import Asset

class Member:
    def __init__(self, payload: dt.GuildMemberData):
        self._from_data(payload)

    def _from_data(self, payload: dt.GuildMemberData):
        self.guild_avatar = payload.get("avatar")
        self.joined_at = payload['joined_at']
        self.roles = payload.get("roles")
        self.id = payload['user']['id']
        self.name = payload['user']['username']
        self._avatar = payload['user'].get("avatar")

    @property
    def avatar(self) -> Optional[Asset]:
        if self._avatar is not None:
            return Asset._from_avatar(self.id, self._avatar)
        return None



