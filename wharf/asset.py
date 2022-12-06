from __future__ import annotations


class Asset:
    BASE_URL = "https://cdn.discordapp.com"

    def __init__(self, *, url: str, key: str, animated: bool = False):
        self._url: str = url
        self._animated: bool = animated
        self._key: str = key

    @property
    def url(self) -> str:
        """:class:`str`: Returns the underlying URL of the asset."""
        return self._url

    @property
    def key(self) -> str:
        """:class:`str`: Returns the identifying key of the asset."""
        return self._key

    def is_animated(self) -> bool:
        """:class:`bool`: Returns whether the asset is animated."""
        return self._animated

    @classmethod
    def _from_avatar(cls, user_id: int, avatar: str):
        animated = avatar.startswith("a_")
        format = "gif" if animated else "png"
        return cls(
            url=f"{cls.BASE_URL}/avatars/{user_id}/{avatar}.{format}?size=1024",
            key=avatar,
            animated=animated,
        )
