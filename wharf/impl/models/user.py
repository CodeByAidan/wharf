import discord_typings as dt


class User:
    def __init__(self, data: dt.UserData):
        self._from_data(data)

    def _from_data(self, data):
        self.name = data.get("username")
        self.id = data.get("id")
