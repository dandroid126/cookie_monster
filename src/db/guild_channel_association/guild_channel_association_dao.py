from typing import Optional

from src.constants import LOGGER
from src.db.db_manager import DbManager, db_manager
from src.db.guild_channel_association.guild_channel_association_record import GuildChannelAssociationRecord

# Keeping these here for reference, but don't use them because formatted strings in queries are bad.
# TABLE_NAME = 'guild_channel_association'
# COLUMN_GUILD_ID = 'guild_id'
# COLUMN_CHANNEL_ID = 'channel_id'

TAG = "GuildChannelAssociationDao"


class GuildChannelAssociationDao:
    def __init__(self, db_manager: DbManager):
        self.db_manager = db_manager

    def get_channel_id_by_guild_id(self, guild_id: int) -> Optional[GuildChannelAssociationRecord]:
        query = "SELECT * FROM guild_channel_association WHERE guild_id=?"
        params = (guild_id,)
        LOGGER.i(TAG, f"get_channel_id_by_guild_id(): executing {query} with params {params}")
        val = self.db_manager.cursor.execute(query, params).fetchone()
        if val is not None:
            return GuildChannelAssociationRecord(int(val[0]), int(val[1]))
        return None

    def insert_or_update_guild_channel_association(self, guild_id: int, channel_id: int) -> Optional[GuildChannelAssociationRecord]:
        query = "INSERT OR REPLACE INTO guild_channel_association(guild_id, channel_id) VALUES(?, ?) RETURNING *"
        params = (guild_id, channel_id)
        LOGGER.i(TAG, f"insert_or_update_guild_channel_association(): executing {query} with params {params}")
        val = self.db_manager.cursor.execute(query, params).fetchone()
        self.db_manager.connection.commit()
        if val is not None:
            return GuildChannelAssociationRecord(int(val[0]), int(val[1]))
        return None

    def get_all_guild_channel_associations(self) -> list[GuildChannelAssociationRecord]:
        query = "SELECT * FROM guild_channel_association"
        LOGGER.i(TAG, f"get_all_guild_channel_associations(): executing {query}")
        val = self.db_manager.cursor.execute(query).fetchall()
        return [GuildChannelAssociationRecord(int(val[0]), int(val[1])) for val in val]

guild_channel_association_dao = GuildChannelAssociationDao(db_manager)
