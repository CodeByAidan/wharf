import asyncio
import json
import logging
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional, Union, List
from urllib.parse import quote as urlquote

import aiohttp

from . import __version__
from .dispatcher import Dispatcher
from .errors import BucketMigrated, HTTPException
from .file import File
from .gateway import Gateway
from .impl import Embed, InteractionCommand
from .impl.ratelimit import Ratelimiter

_log = logging.getLogger(__name__)

__all__ = ("Route",)


BASE_API_URL = "https://discord.com/api/v10"


@dataclass
class PreparedData:
    json: Optional[dict] = None
    multipart_content: Optional[aiohttp.FormData] = None


def _filter_dict(d: dict[Any, Any]):
    return dict(filter(lambda item: item[1] is not None, d.items()))


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
            f"{self.method}:{self.url.format_map(top_level_params | other_params)}"
        )


class HTTPClient:
    def __init__(self, *, dispatcher: Dispatcher, token: str, intents: int):
        self._intents = intents
        self._token = token
        self.__session: aiohttp.ClientSession = None  # type: ignore
        self._gateway = Gateway(dispatcher, self)
        self.base_headers = {"Authorization": f"Bot {self._token}"}
        self.user_agent = "DiscordBot (https://github.com/sawshadev/wharf, {0}) Python/{1.major}.{1.minor}.{1.micro}".format(
            __version__, sys.version_info
        )
        self.loop = asyncio.get_event_loop()
        self.ratelimiter = Ratelimiter()
        self.req_id = 0

        self.default_headers: dict[str, str] = {"Authorization": f"Bot {self._token}"}

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

        return json.loads(text) if resp.content_type == "application/json" else text

    @staticmethod
    def _prepare_data(data: Optional[dict[str, Any]], files: Optional[File]):
        pd = PreparedData()

        if data is not None and files is None:
            pd.json = _filter_dict(data)

        if data is not None and files is not None:
            form_dat = aiohttp.FormData()

            form_dat.add_field(
                "payload_json", f"{json.dumps(data)}", content_type="application/json"
            )

            form_dat.add_field('files[1]', files.fp, filename=files.filename)

            pd.multipart_content = form_dat

        return pd

    async def request(
        self,
        route: Route,
        *,
        query_params: Optional[dict[str, Any]] = None,
        json_params: dict = None,
        files: Optional[List[File]] = None,
        reason: Optional[str] = None,
        **kwargs
    ):
        self.req_id += 1

        query_params = query_params or {}
        max_tries = 5

        kwargs = kwargs or {}

        headers: dict[str, str] = self.default_headers

        if reason:
            headers["X-Audit-Log-Reason"] = urlquote(reason, safe="/ ")

        data = self._prepare_data(json_params, files)

        if data.json is not None:
            kwargs["json"] = data.json

        if data.multipart_content is not None:
            kwargs["data"] = data.multipart_content

        bucket = self.ratelimiter.get_bucket(route.bucket)

        for tries in range(max_tries):
            async with self.ratelimiter.global_bucket:
                async with bucket:
                    response = await self._session.request(
                        route.method,
                        f"{BASE_API_URL}{route.url}",
                        params=query_params,
                        headers=headers,
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
                        _log.info("Retry after %s", response.headers["Retry-After"])
                        if "Via" not in response.headers:
                            # cloudflare fucked us. :(

                            raise HTTPException(
                                response, await self._text_or_json(response)
                            )

                        is_global = response.headers["X-RateLimit-Scope"] == "global"

                        if is_global:
                            retry_after = float(response.headers["Retry-After"])
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
        return await self.request(Route("GET", "/gateway/bot"))

    async def register_app_commands(self, command: InteractionCommand):
        me = await self.get_me()

        return await self.request(
            Route("POST", f"/applications/{me['id']}/commands"),
            json_params=command._to_json(),
        )

    async def delete_app_command(self, payload):
        me = await self.get_me()

        return await self.request(Route("DELETE", f"/applications/{me['id']}/commands/{payload['id']}"))

    async def get_app_commands(self):
        me = await  self.get_me()

        return await self.request(Route("GET", f"/applications/{me['id']}/commands"))

    def interaction_respond(self, content: str, embed: Embed, *, id: int, token: str):
        return self.request(
            Route("POST", f"/interactions/{id}/{token}/callback"),
            json_params={"type": 4, "data": {"content": content, "embeds": [embed]}},
        )

    def send_message(self, channel: int, *, content: str, embed: Embed, files: List[File] = None):
        return self.request(
            Route("POST", f"/channels/{channel}/messages"),
            json_params={"content": content, "embeds": [embed.to_dict()]},
            files=files,
        )

    def get_guild(self, guild_id: int):
        return self.request(Route("GET", f"/guilds/{guild_id}"))

    def get_channel(self, channel_id: int):
        return self.request(Route("GET", f"/channels/{channel_id}"))

    def get_me(self):
        return self.request(Route("GET", "/users/@me"))

    def get_member(self, user_id: int, guild_id: int):
        return self.request(Route("GET", f"/guilds/{guild_id}/members/{user_id}"))

    def ban(self, guild_id: int, user_id: int, reason: str):
        route = Route("PUT", f"/guilds/{guild_id}/bans/{user_id}")


        return self.request(route, reason=reason)

    async def start(self):
        await self._gateway.connect()

    def run(self):
        asyncio.run(self.start())
