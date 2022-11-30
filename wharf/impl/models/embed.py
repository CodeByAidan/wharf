from typing import List, Dict

class Embed:
    def __init__(self, *, title: str, description: str):
        self.title = title
        self.description = description
        self.fields: List[Dict] = []

    def to_dict(self):
        return {
            "title": self.title,
            "description": self.description,
            "fields": self.fields,
        }

    def add_field(self, *, name: str, value: str, inline: bool = False):
        self.fields.append({"name": name, "value": value, "inline": inline})