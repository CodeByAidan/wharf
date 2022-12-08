from typing import Optional, Union

import discord_typings as dt
from aiohttp import ClientResponse


class BaseException(Exception):
    pass


class WebsocketClosed(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.msg = message

        super().__init__(f"Gateway was closed with code {code}: {message}")


def _shorten_error_dict(
    d: dt.NestedHTTPErrorsData, parent_key: str = ""
) -> dict[str, str]:
    ret_items: dict[str, str] = {}

    _errors = d.get("_errors")
    if _errors is not None and isinstance(_errors, list):
        ret_items[parent_key] = ", ".join([msg["message"] for msg in _errors])
    else:
        for key, value in d.items():
            key_path = f"{parent_key}.{key}" if parent_key else key
            # pyright thinks the type of value could be object which violates the first parameter
            # of this function
            ret_items |= list(_shorten_error_dict(value, key_path).items())  # type: ignore

    return ret_items


class HTTPException(Exception):
    """Represents an error while attempting to connect to the Discord REST API.
    Args:
        response (aiohttp.ClientResponse): The response from the attempted REST API request.
        data (Union[discord_typings.HTTPErrorResponseData, str, None]): The raw data retrieved from the response.
    Attributes:
        text (str): The error text. Might be empty.
        code (int): The Discord specfic error code of the request.
    """

    __slots__ = ("text", "code")

    def __init__(
        self,
        response: ClientResponse,
        data: Optional[Union[dt.HTTPErrorResponseData, str]],
    ) -> None:
        self.code: int
        self.text: str
        if isinstance(data, dict):
            self.code = data.get("code", 0)
            base = data.get("message", "")
            if errors := data.get("errors"):
                errors = _shorten_error_dict(errors)
                helpful_msg = "In {0}: {0}".format(iter(errors.items()))
                self.text = f"{base}\n{helpful_msg}"
            else:
                self.text = base
        else:
            self.text = data or ""
            self.code = 0

        formatted = "{0} {1} (error code: {2}"
        if self.text:
            formatted += ": {3}"

        formatted += ")"

        # more shitty aiohttp typing
        super().__init__(formatted.format(response.status, response.reason, self.code, self.text))  # type: ignore


class BucketMigrated(BaseException):
    """Represents an internal exception for when a bucket migrates."""

    def __init__(self, discord_hash: str):
        super().__init__(
            f"The current bucket was migrated to another bucket at {discord_hash}"
        )
