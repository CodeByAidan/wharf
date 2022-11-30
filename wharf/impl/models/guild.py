import discord_typings as dt


class Guild:
    def __init__(self, data: dt.GuildData):
        self._from_data(data)

    def _from_data(self, guild: dt.GuildData):
        self.name = guild.get("name")
        self.id = guild.get("id")
        self.icon_hash = guild.get("icon")
