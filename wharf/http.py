import asyncio
import json
import logging
import sys
from typing import TYPE_CHECKING, Any, Optional, Union
from urllib.parse import quote as urlquote

import aiohttp

from . import __version__
from .errors import BucketMigrated, HTTPException
from .gateway import Gateway
from .impl.ratelimit import Ratelimiter
from .objects import Embed

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
        return self.url.format_map(
            {k: urlquote(str(v)) for k, v in self.params.items()}
        )

    @property
    def bucket(self) -> str:
        """The pseudo-bucket that represents this route. This is generated via the method, raw url and top level parameters."""
        top_level_params = {
            k: getattr(self, k)
            for k in ("guild_id", "channel_id", "webhook_id", "webhook_token")
            if getattr(self, k) is not None
        }
        other_params = {
            k: None for k in self.params.keys() if k not in top_level_params.keys()
        }

        return (
            f"{self.method}:{self.url.format_map({**top_level_params, **other_params})}"
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
        self.ratelimiter = Ratelimiter()
        self.req_id = 0

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
        self,
        route: Route,
        *,
        query_params: Optional[dict[str, Any]] = None,
        json_params: Union[dict[str, Any], list[Any]] = None,
        **extras,
    ):
        self.req_id += 1

        max_tries = 5

        bucket = self.ratelimiter.get_bucket(route.bucket)
        kwargs: dict[str, Any] = extras or {}

        for tries in range(max_tries):
            async with self.ratelimiter.global_bucket:
                async with bucket:
                    response = await self._session.request(
                        route.method,
                        f"{BASE_API_URL}{route.url}",
                        params=query_params,
                        headers=self.base_headers,
                        json=json_params,
                        **kwargs,
                    )

                    bucket_url = bucket.bucket is None
                    bucket.update_info(response)
                    await bucket.acquire()

                    if bucket_url and bucket.bucket is not None:
                        try:
                            self.ratelimiter.migrate(route.bucket, bucket.bucket)
                        except BucketMigrated:
                            bucket = self.ratelimiter.get_bucket(route.bucket)

                    if 200 <= response.status < 300:
                        return await self._text_or_json(response)

                    if response.status == 429:  # Uh oh! we're ratelimited shit fuck

                        if "Via" not in response.headers:
                            # cloudflare fucked us. :(

                            raise HTTPException(
                                response, await self._text_or_json(response)
                            )

                        retry_after = float(response.headers["Retry-After"])
                        is_global = response.headers["X-RateLimit-Scope"] == "global"

                        if is_global:
                            _log.info(
                                "REQUEST:%d All requests have hit a global ratelimit! Retrying in %f.",
                                self.req_id,
                                retry_after,
                            )
                            self.ratelimiter.global_bucket.lock_for(retry_after)
                            await self.ratelimiter.global_bucket.acquire()

                        _log.info(
                            "REQUEST:%d Ratelimit is over. Continuing with the request.",
                            self.req_id,
                        )
                        continue

                    if response.status in {500, 502, 504}:
                        wait_time = 1 + tries * 2
                        _log.info(
                            "REQUEST: %d Got a server error! Retrying in %d.",
                            self.req_id,
                            wait_time,
                        )
                        await asyncio.sleep(wait_time)
                        continue

                    if response.status >= 400:
                        raise HTTPException(
                            response, await self._text_or_json(response)
                        )

    async def get_gateway_bot(self):
        return await self.request(Route("GET", f"/gateway/bot"))


    async def send_message(self, channel: int, content: str, embed: Embed = None):
        embeds = []
        if embed:
            embeds.append(embed)

        return await self.request(
            Route("POST", f"/channels/{channel}/messages"),
            json_params={"content": content, "embeds": embeds},
        )  # Only supports content until ratelimiting and more objects are made.

    async def get_guild(self, guild_id: int):
        resp = await self.request(Route("GET", f"/guilds/{guild_id}"))
        return resp


    async def get_me(self):
        return await self.request(Route("GET", "/users/@me"))

    async def start(self):
        await self._gateway.connect()

    def run(self):
        asyncio.run(self.start())
