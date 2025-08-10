import os
from typing import Optional

import discord
from discord import app_commands
from dotenv import load_dotenv

from src import utils
from src.constants import LOGGER
from src.db.guild_channel_association.guild_channel_association_dao import guild_channel_association_dao
from src.errors import LoggedRuntimeError
from src.job_executor import JobExecutor

TAG = "client"

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

if TOKEN is None:
    raise LoggedRuntimeError(TAG, "TOKEN not found. Check that .env file exists in src dir and that its contents are correct")

intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

job_executor: Optional[JobExecutor] = None

@tree.command(
    name="set_channel",
    description="Set the channel to send cookie notifications to",
)
@app_commands.default_permissions(administrator=True)
async def set_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_channel_association_record = guild_channel_association_dao.insert_or_update_guild_channel_association(interaction.guild_id, channel.id)
    if guild_channel_association_record is None:
        await interaction.response.send_message("Failed to set channel", ephemeral=True)
        return
    channel = client.get_channel(guild_channel_association_record.channel_id)
    if channel is None:
        await interaction.response.send_message("Failed to set channel", ephemeral=True)
        return
    await interaction.response.send_message(f"Cookie notifications will be sent to {channel.mention}" , ephemeral=True)

@tree.command(
    name="get_cookies",
    description="Get this week's cookies"
)
async def get_cookies(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    channel_id = interaction.channel_id
    cookies = utils.get_cookies()
    for cookie in cookies:
        message = f'{cookie["name"].strip()} - {cookie["description"].strip()}\n{cookie["newAerialImage"].strip()}\n\n'
        await client.get_channel(channel_id).send(message)
    await interaction.followup.send("Done", ephemeral=True)

@client.event
async def on_ready():
    LOGGER.d(TAG, "on_ready:")
    global job_executor
    await tree.sync()
    for guild in client.guilds:
        LOGGER.d(TAG, f"Connected to {guild.name}")
    if job_executor is None or not job_executor.is_running:
        # Start processing jobs
        job_executor = JobExecutor(client)
        LOGGER.d(TAG, f"on_ready: job_executor.is_started: {job_executor.is_running}")
    else:
        # If the job executor is already set, skip setting it again
        # This happens in the case of a reconnect
        LOGGER.d(TAG, "on_ready: job_executor is already started")

@client.event
async def on_guild_join(guild: discord.Guild):
    await tree.sync()
    LOGGER.d(TAG, f"on_guild_join: {guild}")
    owner = client.get_user(guild.owner_id)
    await owner.send(f"Thanks for adding me to {guild.name}! To setup automatic cookie notifications, run `/set_channel <#channel_id>` in any channel in the guild.")

if __name__ == "__main__":
    client.run(TOKEN)
