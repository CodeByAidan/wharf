from enum import Enum

class Intents(Enum):
    NONE = 0 
    GUILDS = 1 << 0
    GUILD_MEMBERS =  1 << 1
    GUILD_BANS = 1 << 2
    GUILD_EMOJIS = 1 << 3
    GUILD_INTEGRATIONS = 1 << 4
    GUILD_WEBHOOKS = 1 << 5
    GUILD_INVITES  = 1 << 6 
    GUILD_VOICE_STATES = 1 << 7
    GUILD_PRESENCES = 1 << 8
    GUILD_MESSAGES  = 1 << 9
    GUILD_MESSAGE_REACTIONS = 1 << 10
    GUILD_MESSAGE_TYPING = 1 << 11
    DIRECT_MESSAGES = 1 << 12
    DIRECT_MESSAGE_REACTIONS = 1 << 13
    DIRECT_MESSAGE_TYPING = 1 << 14
    MESSAGE_CONTENT = 1 << 15
    GUILD_SCHEDULED_EVENTS = 1 << 16

    ALL_GUILDS_UNPRIVILEGED = (
        GUILDS
        | GUILD_BANS
        | GUILD_EMOJIS
        | GUILD_INTEGRATIONS
        | GUILD_WEBHOOKS
        | GUILD_INVITES
        | GUILD_VOICE_STATES
        | GUILD_MESSAGES
        | GUILD_MESSAGE_REACTIONS
        | GUILD_MESSAGE_TYPING
        | GUILD_SCHEDULED_EVENTS
    )

    ALL_GUILDS_PRIVILEGED = GUILD_MEMBERS | GUILD_PRESENCES
    """All privileged guild intents.
    !!! warning
        This set of intent is privileged, and requires enabling/whitelisting to
        use.
    """

    ALL_GUILDS = ALL_GUILDS_UNPRIVILEGED | ALL_GUILDS_PRIVILEGED
    """All unprivileged guild intents and all privileged guild intents.
    This combines `Intents.ALL_GUILDS_UNPRIVILEGED` and
    `Intents.ALL_GUILDS_PRIVILEGED`.
    !!! warning
        This set of intent is privileged, and requires enabling/whitelisting to
        use.
    """

    ALL_DMS = DIRECT_MESSAGES | DIRECT_MESSAGE_TYPING| DIRECT_MESSAGE_REACTIONS
    """All private message channel (non-guild bound) intents."""

    ALL_MESSAGES = DIRECT_MESSAGES | GUILD_MESSAGES


    ALL_MESSAGE_REACTIONS = DIRECT_MESSAGE_REACTIONS | GUILD_MESSAGE_REACTIONS

    ALL_MESSAGE_TYPING = DIRECT_MESSAGE_TYPING | GUILD_MESSAGE_TYPING


    ALL_UNPRIVILEGED = ALL_GUILDS_UNPRIVILEGED | ALL_DMS


    ALL_PRIVILEGED = ALL_GUILDS_PRIVILEGED | MESSAGE_CONTENT


    ALL = ALL_UNPRIVILEGED | ALL_PRIVILEGED


    @property
    def is_privileged(self) -> bool:
        return bool(self & self.ALL_PRIVILEGED)



