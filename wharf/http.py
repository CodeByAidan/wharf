import aiohttp
from typing import TYPE_CHECKING, Any, Optional

from .gateway import Gateway

from urllib.parse import quote as urlquote
import json
from . import __version__
import sys


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
        self._gateway = Gateway(self, token=token, intents=intents)
        self.base_headers = {"Authorization": f"Bot {self._token}"}
        self.user_agent = "DiscordBot (https://github.com/sawshadev/wharf, {0}) Python/{1.major}.{1.minor}.{1.micro}".format(
            __version__, sys.version_info
        )

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

        return await self._text_or_json(response)

    async def start(self):
        await self._gateway.connect()