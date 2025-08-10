from dataclasses import dataclass


@dataclass
class GuildChannelAssociationRecord:
    guild_id: int
    channel_id: int

    def __str__(self):
        return f"guild_id: {self.guild_id}, channel_id: {self.channel_id}"
