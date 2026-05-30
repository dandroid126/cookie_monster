"""
Manual end-to-end simulation harness for the notification / late-Crumbl-update features.

This connects to Discord as the real bot (using DISCORD_TOKEN from your .env) and drives the
*real* JobExecutor code paths with controlled inputs, so you can confirm that the DMs actually
get delivered and that the stale-cookie retry/give-up logic behaves, without waiting on the real
cron job or for Crumbl to actually be late / break.

It does NOT touch the database and does NOT post cookies to any channel: the "stale" and "error"
scenarios fail/give up before any posting happens, and they use in-memory fake DAOs.

Usage (run from the repo root, same as the bot):
    PYTHONPATH=. python scripts/simulate.py <scenario>

Scenarios:
    manager   DM the bot manager (BOT_MANAGER_USER_ID) with a fake error. Quick delivery check.
    owners    DM every guild owner with the "Crumbl is still showing last week's cookies" message.
    error     Run the full POST_COOKIES path with a simulated parsing error -> should DM the
              bot manager and report ABORTED.
    stale     Run the full POST_COOKIES path with Crumbl "stuck" on last week's cookies and short
              timers -> should retry a few times, give up, DM every guild owner, and report
              COMPLETED.

The bot disconnects automatically once the scenario finishes.
"""
import sys
import threading
import asyncio

import discord
from unittest.mock import patch

from src import utils
from src import job_executor as je_module
from src.constants import LOGGER
from src.db.cookie.cookie_record import CookieRecord
from src.env_util import env_util
from src.job_executor import JobExecutor

TAG = "Simulate"

SCENARIOS = ("manager", "owners", "error", "stale")

# Short timers so the "stale" scenario gives up in a few seconds instead of 2 hours.
SIM_RETRY_DELAY = 2  # seconds between attempts
SIM_MAX_DURATION = 5  # seconds before giving up

SIM_WEEK = "SIM-CURRENT"
SIM_PREVIOUS_WEEK = "SIM-PREVIOUS"


class FakeCookieDao:
    """In-memory CookieDao stand-in so we don't touch the real database."""

    def __init__(self, cookies_by_week):
        self.cookies_by_week = cookies_by_week

    def get_cookies_by_week(self, week):
        return self.cookies_by_week.get(week, [])


class FakeGuildChannelAssociationDao:
    """The stale/error scenarios never post, so this is only here to satisfy the signature."""

    def get_all_guild_channel_associations(self):
        return []


def _sim_cookies(week):
    return [CookieRecord(f"sim-cookie-{i}", f"Sim Cookie {i}", f"A simulated cookie {i}", f"https://example.com/{i}.png", week) for i in range(1, 7)]


def _make_executor(client):
    # Bypass __init__ so we don't start the real loop/thread; we drive the methods directly.
    executor = JobExecutor.__new__(JobExecutor)
    executor.is_running = True
    executor.healthy = True
    executor.client = client
    return executor


def _run_scenario(client, loop, scenario):
    executor = _make_executor(client)
    try:
        if scenario == "manager":
            LOGGER.i(TAG, f"Sending bot-manager DM to BOT_MANAGER_USER_ID={env_util.BOT_MANAGER_USER_ID}")
            executor._notify_bot_manager(loop, RuntimeError("Simulated error: Crumbl changed their JSON schema"))

        elif scenario == "owners":
            LOGGER.i(TAG, f"Sending owner DM to all {len(client.guilds)} guild owner(s)")
            executor._notify_guild_owners(loop, je_module.STALE_COOKIE_MESSAGE)

        elif scenario == "error":
            cookie_dao = FakeCookieDao({SIM_WEEK: []})
            with patch.object(utils, "get_week", return_value=SIM_WEEK), \
                    patch.object(utils, "fetch_cookies", side_effect=RuntimeError("Simulated parsing error: Crumbl changed their JSON schema")):
                state = executor._post_cookies(loop, None, cookie_dao, FakeGuildChannelAssociationDao())
            LOGGER.i(TAG, f"_post_cookies returned {state} (expected ABORTED); bot manager should have been DMed")

        elif scenario == "stale":
            previous = _sim_cookies(SIM_PREVIOUS_WEEK)
            # Crumbl is "stuck": the fetched lineup has the same cookieIds as last week.
            stuck = _sim_cookies(SIM_WEEK)
            cookie_dao = FakeCookieDao({SIM_WEEK: [], SIM_PREVIOUS_WEEK: previous})
            je_module.STALE_COOKIE_RETRY_DELAY = SIM_RETRY_DELAY
            je_module.STALE_COOKIE_MAX_RETRY_DURATION = SIM_MAX_DURATION
            LOGGER.i(TAG, f"Simulating stale cookies: retrying every {SIM_RETRY_DELAY}s, giving up after {SIM_MAX_DURATION}s")
            with patch.object(utils, "get_week", return_value=SIM_WEEK), \
                    patch.object(utils, "get_previous_week", return_value=SIM_PREVIOUS_WEEK), \
                    patch.object(utils, "fetch_cookies", return_value=("https://example.com/sim", stuck)):
                state = executor._post_cookies(loop, None, cookie_dao, FakeGuildChannelAssociationDao())
            LOGGER.i(TAG, f"_post_cookies returned {state} (expected COMPLETED); guild owners should have been DMed")

    except Exception as e:
        LOGGER.e(TAG, f"Scenario '{scenario}' raised: {e}")
    finally:
        LOGGER.i(TAG, "Scenario finished; disconnecting")
        asyncio.run_coroutine_threadsafe(client.close(), loop)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in SCENARIOS:
        print(f"Usage: PYTHONPATH=. python scripts/simulate.py <{'|'.join(SCENARIOS)}>")
        sys.exit(1)
    scenario = sys.argv[1]

    intents = discord.Intents.default()
    intents.members = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        LOGGER.i(TAG, f"Logged in as {client.user}. Running scenario: {scenario}")
        if scenario in ("owners", "stale") and len(client.guilds) == 0:
            LOGGER.w(TAG, "The bot is not in any guilds, so there are no owners to DM.")
        loop = asyncio.get_running_loop()
        # Run the blocking simulation off the event loop, exactly like the real JobExecutor thread.
        threading.Thread(target=_run_scenario, args=(client, loop, scenario), daemon=True).start()

    client.run(env_util.TOKEN)


if __name__ == "__main__":
    main()
