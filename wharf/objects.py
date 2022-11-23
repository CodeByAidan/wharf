from typing import Optional


class Message:
    def __init__(self, data: dict):
        self.content: Optional[str] = data['content']