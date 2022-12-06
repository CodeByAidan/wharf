from __future__ import annotations

import discord_typings as dt


class Channel:
    def __init__(self, payload: dt.ChannelData):
        self._from_data(payload)

    def _from_data(self, payload: dt.ChannelData):
        self.id = payload.get("id")
        self.guild_id = payload.get("guild")
