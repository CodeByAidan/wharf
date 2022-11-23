import asyncio
import json
import sys
from typing import TYPE_CHECKING, Any, Optional, Union
from urllib.parse import quote as urlquote

import aiohttp

from . import __version__
from .errors import HTTPException
from .gateway import Gateway
import logging

_log = logging.getLogger(__name__)

__all__ = ("Route",)


BASE_API_URL = "https://discord.com/api/v10"


class Route:
    def __init__(self, method: str, url: str, **params: Any) -> None:
        self.params: dict[str, Any] = params
        self.method: str = method
        self.url: str = url

        # top-level resource parameters
        self.guild_id: Optional[int] = params.get("guild_id")
        self.channel_id: Optional[int] = params.get("channel_id")
        self.webhook_id: Optional[int] = params.get("webhook_id")
        self.webhook_token: Optional[str] = params.get("webhook_token")

    @property
    def endpoint(self) -> str:
        """The formatted url for this route."""
        return self.url.format_map({k: urlquote(str(v)) for k, v in self.params.items()})

    @property
    def bucket(self) -> str:
        """The pseudo-bucket that represents this route. This is generated via the method, raw url and top level parameters."""
        top_level_params = {
            k: getattr(self, k)
            for k in ("guild_id", "channel_id", "webhook_id", "webhook_token")
            if getattr(self, k) is not None
        }
        other_params = {k: None for k in self.params.keys() if k not in top_level_params.keys()}

        return f"{self.method}:{self.url.format_map({**top_level_params, **other_params})}"


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
        query_params: Optional[dict[str, Any]] = None,
        json_params: Union[dict[str, Any], list[Any]] = None,
        **extras

    ):
        kwargs: dict[str, Any] = extras or {}

        response = await self._session.request(
            route.method,
            f"{BASE_API_URL}{route.url}",
            params=query_params,
            headers=self.base_headers,
            json=json_params,
            **kwargs
        )
    
        if response.status >= 400:
            raise HTTPException(response, await self._text_or_json(response))

        _log.info(response.headers.get("X-RateLimit-Remaining"))

        return await self._text_or_json(response)

    async def get_gateway_bot(self):
        return await self.request(Route("GET", f"/gateway/bot"))

    

    async def send_message(self, channel: int, content: str):
        return await self.request(Route("POST", f"/channels/{channel}/messages"), json_params={"content": content}) # Only supports content until ratelimiting and more objects are made.

    async def get_me(self):
        return await self.request(Route("GET", "/users/@me"))

    async def start(self):
        await self._gateway.connect()

    def run(self):
        asyncio.run(self.start())