class WebsocketClosed(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.msg = message

        super().__init__(f"Gateway was closed with code {code}: {message}")