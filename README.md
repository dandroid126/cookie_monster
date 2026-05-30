# cookie_monster
Post Crumbl cookie flavors to discord server as soon as they are posted on the Crumbl web site

## Configuration

Configuration is provided through environment variables (e.g. via a `.env` file in the repo root):

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `DISCORD_TOKEN` | Yes | | The Discord bot token. |
| `DAY_OF_WEEK` | No | `6` (Sunday) | The day of the week the cookies reset on (0 = Monday ... 6 = Sunday). |
| `TIME` | No | `17:00` | The time of day (24h `HH:MM`) the cookies reset at. |
| `TIMEZONE` | No | `US/Pacific` | The timezone used to interpret `DAY_OF_WEEK` and `TIME`. |
| `BOT_MANAGER_USER_ID` | No | | Discord user ID of the bot manager. Receives a direct message if an error on the bot's end (e.g. a parsing error) prevents cookies from being posted. If unset, the bot manager is not notified. |

### Late Crumbl updates

Crumbl is supposed to update their menu about 10 minutes before the scheduled post time, but they are sometimes up to 30 minutes late. When the scheduled (cron) job runs, the bot compares the fetched cookies against the previous week's cookies. If they are identical, it waits 5 minutes and tries again, for up to 2 hours. If the cookies still match last week's after 2 hours, the bot gives up for that week and direct messages every guild owner to let them know Crumbl is still showing last week's cookies.
