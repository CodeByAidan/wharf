import asyncio
import json
import sys
from typing import TYPE_CHECKING, Any, Optional
from urllib.parse import quote as urlquote

import aiohttp

from . import __version__
from .errors import HTTPException
from .gateway import Gateway

__all__ = ("Route",)


BASE_API_URL = "https://discord.com/api/v10"


class Route:
    base: str = "https://discord.com/api/v10"

    def __init__(self, method: str, url: str,  **params: Any):
        self.method = method
        self.url = self.base + url
        self.params = params

        if params:
            url = url.format_map({k: urlquote(v) if isinstance(v, str) else v for k, v in params.items()}) # Parses the url
        self.url: str = url

        # top-level resource parameters
        self.guild_id: Optional[int] = params.get("guild_id")
        self.channel_id: Optional[int] = params.get("channel_id")
        self.webhook_id: Optional[int] = params.get("webhook_id")
        self.webhook_token: Optional[str] = params.get("webhook_token")
        
        
    @property
    def key(self) -> str:
        return f'{self.method} {self.url}'

    @property
    def major_parameters(self) -> str:
        """Returns the major parameters formatted a string.
        This needs to be appended to a bucket hash to constitute as a full rate limit key.
        """
        return '+'.join(
            str(k) for k in (self.channel_id, self.guild_id, self.webhook_id, self.webhook_token) if k is not None
        )


class HTTPClient:
    def __init__(self, *, token: str, intents: int):
        self._intents = intents
        self._token = token
        self.__session: aiohttp.ClientSession = None  # type: ignore
        self._gateway = Gateway(self)
        self.base_headers = {"Authorization": f"Bot {self._token}"}
        self.user_agent = "DiscordBot (https://github.com/sawshadev/wharf, {0}) Python/{1.major}.{1.minor}.{1.micro}".format(
            __version__, sys.version_info
        )
        self.loop = asyncio.get_event_loop()

    def listen(self, name: str):
        def inner(func):
            if name not in self._gateway.dispatcher.events:
                self._gateway.dispatcher.add_event(name)

            self._gateway.dispatcher.add_callback(name, func)
                
        
        return inner

    @property
    def _session(self):
        if self.__session is None or self.__session.closed:
            self.__session = aiohttp.ClientSession(
                headers={"User-Agent": self.user_agent}, json_serialize=json.dumps
            )

        return self.__session

    @staticmethod
    async def _text_or_json(resp: aiohttp.ClientResponse):
        text = await resp.text()

        if resp.content_type == "application/json":
            return json.loads(text)

        return text

    async def request(
        self, route: Route, 
        *,
        query_params: Optional[dict[str, Any]] = None

    ):
        response = await self._session.request(
            route.method,
            f"{BASE_API_URL}{route.url}",
            params=query_params,
            headers=self.base_headers
        )

        if response.status >= 400:
            raise HTTPException(response, await self._text_or_json(response))

        return await self._text_or_json(response)

    async def get_gateway_bot(self):
        return await self.request(Route("GET", f"/gateway/bot"))

    async def get_me(self):
        return await self.request(Route("GET", "/users/@me"))

    async def start(self):
        await self._gateway.connect()

    def run(self):
        asyncio.run(self.start())