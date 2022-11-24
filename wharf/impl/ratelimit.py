import asyncio
from typing import Optional, Union
from datetime import datetime, timezone
from aiohttp import ClientResponse
from ..errors import BucketMigrated


class RatelimiterBase:
    "An base for any ratelimiter subclassed from this. only provides needed stuff, everything else is up to the subclassed ratelimiters!"

    def __init__(self):
        self.lock: asyncio.Event = asyncio.Event()

        self.lock.set()

    async def acquire(self):
        await self.lock.wait()

    def is_locked(self) -> bool:
        return not self.lock.is_set()

    async def __aenter__(self):
        await self.acquire()
        return None

    async def __aexit__(self, *args):
        pass


class ManualRatelimiter(RatelimiterBase):
    """A simple ratelimiter that simply locks at the command of anything."""

    async def _unlock(self, delay: float):
        await asyncio.sleep(delay)
        self.lock.set()

    def lock_for(self, delay: float):
        """Locks the bucket for a given amount of time.
        Args:
            delay (float): How long the bucket should be locked for.
        """
        if self.is_locked():
            return

        self.lock.clear()
        asyncio.create_task(self._unlock(delay))


class BurstRatelimiter(ManualRatelimiter):
    def __init__(self):
        RatelimiterBase.__init__(self)
        self.limit: Optional[int] = None
        self.remaining: Optional[int] = None
        self.reset_after: Optional[int] = None

    async def acquire(self):
        if self.reset_after and self.remaining == 0 and not self.is_locked():
            self.lock_for(self.reset_after)

        return await super().acquire()


class Bucket(BurstRatelimiter):
    def __init__(self):
        super().__init__()
        self.reset: Optional[datetime] = None
        self.bucket: Optional[str] = None
        self._first_update: bool = True
        self._migrated: bool = False

    def update_info(self, resp: ClientResponse):
        self.limit = int(resp.headers.get("X-RateLimit-Limit", 1))
        raw_remaining = resp.headers.get("X-RateLimit-Remaining")

        if resp.status == 429:
            self.remaining = 0
        elif raw_remaining is None:
            self.remaining = 1
        else:
            raw_remaining = int(raw_remaining)

            if self._first_update:
                self.remaining = raw_remaining
            elif self.remaining is not None:
                self.remaining = (
                    raw_remaining if raw_remaining < self.remaining else self.remaining
                )

        reset = resp.headers.get("X-RateLimit-Reset")

        if reset is not None:
            self.reset = datetime.fromtimestamp(float(reset), timezone.utc)

        reset_after = resp.headers.get("X-RateLimit-Reset-After")

        if reset_after is not None:
            reset_after = float(reset_after)

            if self.reset_after is None:
                self.reset_after = reset_after

            else:
                self.reset_after = (
                    reset_after if self.reset_after < reset_after else self.reset_after
                )

        if self._first_update:
            self._first_update = False

        if (
            self.reset_after is not None
            and self.remaining == 0
            and not self.is_locked()
        ):
            self.lock_for(self.reset_after)

    def migrate(self, hash: str):
        self._migrated = True

        raise BucketMigrated(hash)

    @property
    def migrated(self):
        return self._migrated


class Ratelimiter:
    def __init__(self):
        self.discord_buckets: dict[str, Bucket] = {}
        self.url_buckets: dict[str, Bucket] = {}
        self.url_to_discord_hash: dict[str, str] = {}
        self.global_bucket = ManualRatelimiter()

    def get_bucket(self, url: str):
        if url not in self.url_to_discord_hash:
            bucket = Bucket()
            self.url_buckets[url] = bucket
            return bucket

        hash = self.url_to_discord_hash[url]
        return self.discord_buckets[hash]

    def migrate(self, url: str, hash: str):
        self.url_to_discord_hash[url] = hash

        bucket = self.url_buckets[url]
        self.discord_buckets[hash] = bucket
        self.url_buckets.pop(url)

        bucket.migrate(hash)
