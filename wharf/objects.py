import discord_typings as dt

class Embed:
    def __init__(self, *, title: str, description: str):
        self.title = title
        self.description = description
        self.fields: list[dict] = []

    def to_dict(self):
        return {
            "title": self.title,
            "description": self.description,
            "fields": self.fields,
        }

    def add_field(self, *, name: str, value: str, inline: bool = False):
        self.fields.append({"name": name, "value": value, "inline": inline})

class Guild:
    def __init__(self, data: dt.GuildData):
        self._from_data(data)

    def _from_data(self, guild: dt.GuildData):
        self.name = guild.get("name")
        self.id = guild.get("id")
        self.icon_hash = guild.get("icon")
        