from .flag import Flag, flag
from typing import TYPE_CHECKING
from typing_extensions import Self

class Intents(Flag):
    if TYPE_CHECKING:

        def __init__(
            self,
            *,
            guilds: bool = ...,
            guild_members: bool = ...,
            guild_bans: bool = ...,
            guild_emojis_and_stickers: bool = ...,
            guild_integrations: bool = ...,
            guild_webhooks: bool = ...,
            guild_invites: bool = ...,
            guild_voice_states: bool = ...,
            guild_presences: bool = ...,
            guild_messages: bool = ...,
            guild_message_reactions: bool = ...,
            guild_message_typing: bool = ...,
            direct_messages: bool = ...,
            direct_message_reactions: bool = ...,
            direct_message_typing: bool = ...,
            message_content: bool = ...,
            guild_scheduled_events: bool = ...,
            auto_moderation_configuration: bool = ...,
            automod_execution: bool = ...,
        ) -> None:
            ...

    @flag
    def GUILDS():
        return 1 << 0

    @flag
    def GUILD_MEMBERS():
        return 1 << 1

    @flag
    def GUILD_BANS():
        return 1 << 2

    @flag
    def GUILD_EMOJIS_AND_STICKERS():
        return 1 << 3

    @flag
    def GUILD_INTEGRATIONS():
        return 1 << 4

    @flag
    def GUILD_WEBHOOKS():
        return 1 << 5

    @flag
    def GUILD_INVITES():
        return 1 << 6

    @flag
    def GUILD_VOICE_STATES():
        return 1 << 7

    @flag
    def GUILD_PRESENCES():
        return 1 << 8

    @flag
    def GUILD_MESSAGES():
        return 1 << 9

    @flag
    def GUILD_MESSAGE_REACTIONS():
        return 1 << 10

    @flag
    def GUILD_MESSAGE_TYPING():
        return 1 << 11

    @flag
    def DIRECT_MESSAGES():
        return 1 << 12

    @flag
    def DIRECT_MESSAGE_REACTIONS():
        return 1 << 13

    @flag
    def DIRECT_MESSAGE_TYPING():
        return 1 << 14

    @flag
    def MESSAGE_CONTENT():
        return 1 << 15

    @flag
    def GUILD_SCHEDULED_EVENTS():
        return 1 << 16

    @flag
    def AUTO_MODERATION_CONFIGURATION():
        return 1 << 20

    @flag
    def AUTO_MODERATION_EXECUTION():
        return 1 << 21

    @classmethod
    def default(cls: type[Self]) -> Self:
        self = cls.all()
        self.GUILD_MEMBERS = False
        self.GUILD_PRESENCES = False
        self.MESSAGE_CONTENT = False
        return self
