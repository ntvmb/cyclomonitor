"""CycloMonitor Discord bot"""

import math
from . import server_vars
from . import global_vars
from . import atcf
from . import errors
import datetime
import logging
import time
import asyncio
from . import ibtracs
from types import GeneratorType
from .uptime import *
from .dir_calc import get_dir
from io import StringIO
from sys import exit
from .locales import *

copyright_notice = """
CycloMonitor - ATCF and IBTrACS wrapper for Discord
Copyright (c) 2023 Virtual Nate

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or any later version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
details.

For those hosting a copy of this bot, you should have received a copy of the
GNU Affero General Public License along with this program. If not, see
<https://www.gnu.org/licenses/>.
"""

# Prevent PyLance from complaining about these
INVITE = None
SERVER = None
GITHUB = None

try:
    import discord
    from discord import (
        option,
        default_permissions,
        SlashCommandOptionType,
        guild_only,
        Option,
    )
    from discord.ext import tasks, commands
except ImportError as e:
    raise ModuleNotFoundError(ERROR_PYCORD_MISSING) from e

KT_TO_MPH = 1.15077945
KT_TO_KMH = 1.852
COMMON_COMMANDS = {
    "ping",
    "invite",
    "statistics",
    "yikes",
    "github",
    "copyright",
    "rsmc_list",
    "feedback",
    "get_past_storm",
    "get_forecast",
    "server",
}
USEFUL_COMMANDS = {
    "invite",
    "rsmc_list",
    "feedback",
    "get_past_storm",
    "get_forecast",
    "server",
}
ADMIN_COMMANDS = {
    "set_tracking_channel",
    "update",
    "update_alt",
    "set_basins",
    "set_language",
}
CONFIG_COMMANDS = {
    "set_tracking_channel",
    "set_basins",
    "set_language",
}
INTERNAL_COMMANDS = {
    "update_all",
    "update_all_alt",
    "announce_all",
    "announce_basin",
    "announce_file",
    "get_data",
    "get_data_alt",
    "atcf_reset",
    "get_log",
    "suspend_updates",
    "resume_updates",
    "contact_guild",
}
bot = discord.Bot(intents=discord.Intents.default())
# it is ideal to put out the information as soon as possible, but there may be overrides
times = [
    datetime.time(2, 0, tzinfo=datetime.UTC),
    datetime.time(8, 0, tzinfo=datetime.UTC),
    datetime.time(14, 0, tzinfo=datetime.UTC),
    datetime.time(20, 0, tzinfo=datetime.UTC),
]
log = logging.getLogger(__name__)
languages = ["C", "en_US"]
emojis = {}
most_recent_dissipation = None
help = bot.create_group("help", CM_HELP_GENERAL)


class monitor(commands.Cog):
    """This class governs automated routines."""

    def __init__(self, bot):
        self.bot = bot
        self.last_update = global_vars.get("last_update")
        self.last_ibtracs_update = global_vars.get("last_ibtracs_update")
        self.auto_update.start()
        self.daily_ibtracs_update.start()
        self.is_best_track_updating = False

    def cog_unload(self):
        logging.info(LOG_MONITOR_STOP)
        self.auto_update.cancel()
        self.daily_ibtracs_update.cancel()

    @staticmethod
    def should_suppress(prev_timestamps: dict):
        """Compare two lists of timestamps and return a boolean."""
        suppressed = []
        for index, (cyclone, timestamp) in enumerate(
            zip(atcf.cyclones, atcf.timestamps)
        ):
            if cyclone == most_recent_dissipation:
                suppressed.append(True)
            else:
                try:
                    # will this system request for a suppression?
                    suppressed.append(prev_timestamps[cyclone] >= timestamp)
                except LookupError:
                    suppressed.append(False)
                logging.debug(
                    LOG_TIMESTAMP_COMPARISON.format(cyclone, suppressed[index])
                )
        if not atcf.cyclones:
            suppressed.append(False)
        # only suppress an automatic update if all active systems requested a suppression
        for do_suppress in suppressed:
            if not do_suppress:
                return False
        return True

    @tasks.loop(time=times)
    async def auto_update(self):
        logging.info(LOG_AUTO_UPDATE_BEGIN)
        prev_timestamps = {
            cid: time for cid, time in zip(atcf.cyclones, atcf.timestamps)
        }
        try:
            await atcf.get_data()
        except atcf.ATCFError as e:
            logging.exception(ERROR_AUTO_UPDATE_FAILED)
            return
        self.last_update = math.floor(time.time())
        global_vars.write("last_update", self.last_update)
        for cid in prev_timestamps:
            if cid not in atcf.cyclones:
                most_recent_dissipation = cid
        if self.should_suppress(prev_timestamps):
            # try alternate source
            logging.warning(LOG_SUPPRESSED)
            try:
                await atcf.get_data_alt()
            except atcf.ATCFError as e:
                logging.exception(ERROR_AUTO_UPDATE_FAILED)
                return
            if self.should_suppress(prev_timestamps):
                logging.warning(LOG_SUPPRESSED_TRY_2)
                for guild in bot.guilds:
                    channel_id = server_vars.get("tracking_channel", guild.id)
                    channel = bot.get_channel(channel_id)
                    if channel is not None:
                        try:
                            await channel.send(CM_SUPPRESSED_MESSAGE)
                            await channel.send(
                                NEXT_AUTO_UPDATE.format(
                                    math.floor(
                                        cog.auto_update.next_iteration.timestamp()
                                    )
                                )
                            )
                        except discord.errors.HTTPException:
                            logging.warning(LOG_GUILD_UNAVAILABLE.format(guild.id))
                            continue
                return
        for guild in bot.guilds:
            channel_id = server_vars.get("tracking_channel", guild.id)
            if channel_id is not None:
                await update_guild(guild.id, channel_id)

    @auto_update.error
    async def on_update_error(self, error):
        if not isinstance(error, errors.LogRequested):
            logging.exception(CM_ERROR_WHILE_UPDATING)
        app = await self.bot.application_info()
        bot_owner = app.owner
        if bot_owner is not None:
            try:
                with open("bot.log", "rb") as log:
                    await bot_owner.send(CM_ATTACH_LOG, file=discord.File(log))
            except discord.HTTPException:
                logging.exception(ERROR_LOG_SEND_FAIL)
        else:
            logging.warning(LOG_NO_OWNER)
        if not isinstance(error, errors.LogRequested):
            for guild in bot.guilds:
                channel_id = server_vars.get("tracking_channel", guild.id)
                channel = bot.get_channel(channel_id)
                if channel is not None:
                    await channel.send(CM_AUTO_UPDATE_FAILED_MESSAGE)

    @tasks.loop(time=datetime.time(0, 0, tzinfo=datetime.UTC))
    async def daily_ibtracs_update(self, *, _force_full=False):
        self.is_best_track_updating = True
        now = datetime.datetime.now(datetime.UTC)
        logging.info(LOG_IBTRACS_UPDATE_BEGIN)
        if (now.day == 2) or _force_full:
            await ibtracs.update_db("full")
        else:
            await ibtracs.update_db("last3")
        global_vars.write("last_ibtracs_update", math.floor(time.time()))
        self.is_best_track_updating = False

    @daily_ibtracs_update.error
    async def on_ibtracs_update_error(self, error):
        logging.error(LOG_IBTRACS_UPDATE_FAILED_ATTEMPT_1)
        await asyncio.sleep(10)
        for i in range(4):
            try:
                logging.info(LOG_NEXT_ATTEMPT.format(i + 2))
                await self.daily_ibtracs_update()
            except Exception as e:
                logging.error(LOG_ATTEMPT_FAILED.format(i + 2))
                if i == 3:
                    logging.exception(ERROR_IBTRACS_UPDATE_FAILED)
                    self.is_best_track_updating = False
                    raise e from error
                else:
                    logging.error(LOG_TRY_AGAIN.format(10 * (i + 2)))
                    await asyncio.sleep(10 * (i + 2))
                    continue
            else:
                break
        self.is_best_track_updating = False

    async def am_i_late(self):
        # force an automatic update if last_update is not set or more than 6
        # hours have passed since the last update
        if (self.last_update is None) or (
            math.floor(time.time()) - self.last_update > 21600
        ):
            await self.auto_update()
        # same idea as above but for IBTrACS data, and the limit is 24 hours
        if (self.last_ibtracs_update is None) or (
            math.floor(time.time()) - self.last_ibtracs_update > 86400
        ):
            await self.daily_ibtracs_update()

    async def wait_for_ibtracs(self):
        while self.is_best_track_updating:
            await asyncio.sleep(1)


async def update_guild(guild: int, to_channel: int):
    """Given a guild ID and channel ID, post ATCF data."""
    set_locale(server_vars.get("lang", guild))
    logging.info(LOG_UPDATE_GUILD.format(guild))
    channel = bot.get_channel(to_channel)
    if channel is None:
        logging.warning(LOG_GUILD_UNAVAILABLE.format(guild))
        return
    enabled_basins = server_vars.get("basins", guild)
    current_TC_record = global_vars.get("strongest_storm")  # record-keeping
    if enabled_basins is not None:
        sent_list = []
        for (
            cyc_id,
            basin,
            wind,
            name,
            timestamp,
            lat,
            long,
            pressure,
            tc_class,
            lat_real,
            long_real,
            movement_speed,
            movement_dir,
        ) in zip(
            atcf.cyclones,
            atcf.basins,
            atcf.winds,
            atcf.names,
            atcf.timestamps,
            atcf.lats,
            atcf.longs,
            atcf.pressures,
            atcf.tc_classes,
            atcf.lats_real,
            atcf.longs_real,
            atcf.movement_speeds,
            atcf.movement_dirs,
        ):
            # per standard, we round to the nearest 5
            mph = round(wind * KT_TO_MPH / 5) * 5
            kmh = round(wind * KT_TO_KMH / 5) * 5
            c_dir = get_dir(movement_dir)
            if (not c_dir) or (movement_speed < 0):
                movement_str = NOT_AVAILABLE
            elif movement_speed < 2:
                movement_str = NEARLY_STATIONARY
            elif movement_speed == 0:
                movement_str = STATIONARY
            else:
                movement_mph = movement_speed * KT_TO_MPH
                movement_kph = movement_speed * KT_TO_KMH
                movement_str = STORM_MOVEMENT.format(
                    c_dir, movement_speed, movement_mph, movement_kph
                )
            # accomodate for basin crossovers
            if lat_real > 0 and long_real > 30 and long_real < 97:
                basin = "IO"
            elif lat_real > 0 and long_real > 97:
                basin = "WPAC"
            elif lat_real > 0 and long_real < -140:
                basin = "CPAC"
            elif lat_real > 0 and (
                (lat_real < 7.6 and long_real < -77)
                or (lat_real < 10 and long_real < -85)
                or (lat_real < 15 and long_real < -87)
                or (lat_real < 16 and long_real < -92.5)
                or long_real < -100
            ):
                basin = "EPAC"
            logging.debug(LOG_BASIN.format(cyc_id, basin))

            if pressure == 0:
                pressure = math.nan
            """
            Wind speeds are ignored when marking an invest.
            There is one exception, which is for subtropical cyclones, because not all agencies issue advisories/warnings on STCs (notably CPHC and JTWC).
            We can make an exception for STCs because ATCF doesn't autoflag them (more on that below).
            All wind speed values shown are in knots rounded to the nearest 5 (except for ones after > operators)
            """
            if name == "INVEST" and (not (tc_class == "SD" or tc_class == "SS")):
                tc_class = CLASS_AOI
            if tc_class == "EX":
                if not name == "INVEST":
                    tc_class = CLASS_PTC
                emoji = emojis.get("ex")
            elif tc_class == "LO" or tc_class == "INVEST":
                if not name == "INVEST":
                    tc_class = CLASS_PTC
                emoji = emojis.get("low")
            elif tc_class == "DB" or tc_class == "WV":
                if not name == "INVEST":
                    tc_class = CLASS_RL
                emoji = emojis.get("remnants")
            elif wind < 35:
                if not (tc_class == "SD" or name == "INVEST"):
                    # ignored if invest in case of autoflagging
                    # ATCF will autoflag a system to be a TD once it has attained 1-minute sustained winds of between 23 and 33 kt
                    tc_class = CLASS_TD
                    emoji = emojis.get("td")
                elif name == "INVEST" and not tc_class == "SD":
                    emoji = emojis.get("low")
                else:
                    tc_class = CLASS_SD
                    emoji = emojis.get("sd")
            elif wind > 34 and wind < 65:
                if not (tc_class == "SS" or name == "INVEST"):
                    tc_class = CLASS_TS
                    emoji = emojis.get("ts")
                elif name == "INVEST" and not tc_class == "SS":
                    emoji = emojis.get("low")
                else:
                    tc_class = CLASS_SS
                    emoji = emojis.get("ss")
            else:
                # determine the term to use based on the basin
                # we assume at this point that the system is either a TC or extratropical
                if basin == "ATL" or basin == "EPAC" or basin == "CPAC":
                    if wind < 100:
                        tc_class = CLASS_HU
                    else:
                        tc_class = CLASS_MH
                elif basin == "WPAC":
                    if wind < 130:
                        tc_class = CLASS_TY
                    else:
                        tc_class = CLASS_STY
                else:
                    tc_class = CLASS_CY

                # for custom emoji to work, the bot needs to be in the server it's from
                # you also need the emoji's ID
                if wind < 85:
                    emoji = emojis.get("cat1")
                elif wind > 84 and wind < 100:
                    emoji = emojis.get("cat2")
                elif wind > 99 and wind < 115:
                    emoji = emojis.get("cat3")
                elif wind > 114 and wind < 140:
                    emoji = emojis.get("cat4")
                elif wind > 139 and wind < 155:
                    emoji = emojis.get("cat5")
                elif wind > 154 and wind < 170:
                    emoji = emojis.get("cat5intense")
                else:
                    emoji = emojis.get("cat5veryintense")
            if name == "INVEST":
                name = display_name = cyc_id
            else:
                display_name = f"{cyc_id} ({name})"
            if emoji is None:
                emoji = ":cyclone:"
            # update TC records
            if current_TC_record is not None:
                if (wind > int(current_TC_record[5])) or (
                    wind == int(current_TC_record[5])
                    and pressure < int(current_TC_record[8])
                ):
                    logging.info(LOG_NEW_RECORD)
                    global_vars.write(
                        "strongest_storm",
                        [
                            emoji,
                            tc_class,
                            cyc_id,
                            name,
                            str(timestamp),
                            str(wind),
                            str(mph),
                            str(kmh),
                            str(pressure),
                        ],
                    )
            else:
                logging.info(LOG_NO_RECORD)
                global_vars.write(
                    "strongest_storm",
                    [
                        emoji,
                        tc_class,
                        cyc_id,
                        name,
                        str(timestamp),
                        str(wind),
                        str(mph),
                        str(kmh),
                        str(pressure),
                    ],
                )

            # this check is really long since it needs to accomodate for every possible situation
            send_message = (
                (basin == "ATL" and enabled_basins[0] == "1")
                or (basin == "EPAC" and enabled_basins[1] == "1")
                or (basin == "CPAC" and enabled_basins[2] == "1")
                or (basin == "WPAC" and enabled_basins[3] == "1")
                or (basin == "IO" and enabled_basins[4] == "1")
                or (basin == "SHEM" and enabled_basins[5] == "1")
            )
            sent_list.append(send_message)
            if math.isnan(pressure):
                pressure = "N/A"
            if send_message and channel is not None:
                try:
                    await channel.send(
                        CM_STORM_INFO.format(
                            emoji,
                            tc_class,
                            display_name,
                            f"<t:{timestamp}:f>",
                            name,
                            lat,
                            long,
                            wind,
                            mph,
                            kmh,
                            pressure,
                            movement_str,
                        )
                    )
                except discord.errors.HTTPException:
                    logging.warning(LOG_GUILD_UNAVAILABLE.format(guild))
                    return
            elif channel is None:
                logging.warning(LOG_GUILD_UNAVAILABLE.format(guild))
                return

        for was_sent in sent_list:
            if was_sent:
                break
        else:  # no break
            if channel is not None:
                await channel.send(CM_NO_STORMS)
        try:
            next_run = int(cog.auto_update.next_iteration.timestamp())
        except AttributeError:
            next_run = NO_AUTO_UPDATE
        # it is best practice to use official sources when possible
        if channel is not None:
            await channel.send(CM_NEXT_AUTO_UPDATE.format(next_run))
            await channel.send(CM_MORE_INFO)


def get_first_available_channel(guild: discord.Guild) -> discord.TextChannel:
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            return channel
    return None


@bot.event
async def on_ready():
    global cog
    locale_init()
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name=CM_WATCHING)
    )
    logging.info(LOG_READY.format(bot.user))
    global_vars.write("guild_count", len(bot.guilds))
    cog = monitor(bot)
    bot.add_cog(cog)
    await cog.am_i_late()


@bot.event
async def on_disconnect():
    cog: monitor = bot.get_cog("monitor")
    if not (cog is None or cog.is_best_track_updating):
        bot.remove_cog("monitor")
    if cog is not None and cog.is_best_track_updating:
        try:
            await asyncio.wait_for(cog.wait_for_ibtracs(), timeout=60.0)
        finally:
            bot.remove_cog("monitor")
            if bot.is_ready():
                bot.add_cog(monitor())


@bot.event
async def on_resumed():
    global cog
    if bot.get_cog("monitor") is None and bot.is_ready():
        # The cog is already closed; it's safe to overwrite the old cog
        cog = monitor(bot)
        bot.add_cog(cog)
        await cog.am_i_late()


@bot.event
async def on_guild_join(guild: discord.Guild):
    logging.info(LOG_NEW_GUILD.format(guild.name))
    count = len(bot.guilds)
    global_vars.write("guild_count", count)
    channel = get_first_available_channel(guild)
    if channel is not None:
        await channel.send(CM_GUILD_ADDED)


@bot.event
async def on_guild_remove(guild: discord.Guild):
    logging.info(LOG_GUILD_REMOVED.format(guild.name))
    count = len(bot.guilds)
    server_vars.remove_guild(guild.id)
    global_vars.write("guild_count", count)


@bot.event
async def on_application_command(ctx: discord.ApplicationContext):
    server_lang = server_vars.get("lang", ctx.guild_id)
    if server_lang is not None:
        set_locale(server_lang)
    else:
        set_locale("C")


@bot.event
async def on_application_command_error(
    ctx: discord.ApplicationContext, error: BaseException
):
    if isinstance(error, commands.errors.MissingPermissions) or isinstance(
        error, commands.errors.NotOwner
    ):
        try:
            await ctx.respond(CM_NO_PERMISSION, ephemeral=True)
        except discord.errors.HTTPException:
            logging.exception(ERROR_CANNOT_RESPOND)
        logging.warning(
            LOG_NO_PERMISSION.format(
                ctx.author,
                ctx.command.name,
                ctx.author.id,
                ctx.guild,
                ctx.guild.id,
                ctx.channel,
                ctx.channel_id,
                ctx.selected_options,
            )
        )
    elif isinstance(error, commands.errors.NoPrivateMessage):
        try:
            await ctx.respond(CM_NO_DM, ephemeral=True)
        except discord.errors.HTTPException:
            logging.exception(ERROR_CANNOT_RESPOND)
    else:
        logging.exception(LOG_COMMAND_ERROR.format(ctx.command.name, error))
        try:
            await ctx.respond(CM_COMMAND_ERROR.format(error), ephemeral=True)
        except discord.errors.HTTPException:
            logging.exception(ERROR_CANNOT_RESPOND)


@bot.slash_command(name="ping", description=CM_PING)
async def ping(ctx):
    await ctx.defer(ephemeral=True)
    await ctx.respond(CM_PONG.format(int(bot.latency * 1000)), ephemeral=True)


@bot.slash_command(name="set_tracking_channel", description=CM_SET_TRACKING_CHANNEL)
@guild_only()
@default_permissions(manage_channels=True)
@commands.has_guild_permissions(manage_channels=True)
@option("channel", discord.TextChannel, description=CM_CHANNEL_TO_USE)
async def set_tracking_channel(ctx, channel):
    await ctx.defer(ephemeral=True)
    if not isinstance(channel, discord.TextChannel):
        await ctx.respond(ERROR_NOT_A_TEXT_CHANNEL, ephemeral=True)
    else:
        if channel.permissions_for(ctx.me).send_messages:
            server_vars.write("tracking_channel", channel.id, ctx.guild_id)
            await ctx.respond(CM_SET_CHANNEL_SUCCESS.format(channel), ephemeral=True)
        else:
            await ctx.respond(CM_CANNOT_SEND_MESSAGE, ephemeral=True)


@bot.slash_command(name="update", description=CM_UPDATE)
@guild_only()
@default_permissions(manage_messages=True)
@commands.has_guild_permissions(manage_messages=True)
async def update(ctx):
    await ctx.defer(ephemeral=True)
    channel_id = server_vars.get("tracking_channel", ctx.guild_id)
    if bot.get_channel(channel_id) is None:
        await ctx.respond(ERROR_NO_TRACKING_CHANNEL, ephemeral=True)
    await atcf.get_data()
    cog.last_update = math.floor(time.time())
    global_vars.write("last_update", cog.last_update)
    await update_guild(ctx.guild_id, channel_id)
    await ctx.respond(CM_UPDATE_SUCCESS, ephemeral=True)
    atcf.reset()


@bot.slash_command(name="update_alt", description=CM_UPDATE_ALT)
@guild_only()
@default_permissions(manage_messages=True)
@commands.has_guild_permissions(manage_messages=True)
async def update_alt(ctx):
    await ctx.defer(ephemeral=True)
    channel_id = server_vars.get("tracking_channel", ctx.guild_id)
    if bot.get_channel(channel_id) is None:
        await ctx.respond(ERROR_NO_TRACKING_CHANNEL, ephemeral=True)
    await atcf.get_data_alt()
    cog.last_update = math.floor(time.time())
    global_vars.write("last_update", cog.last_update)
    await update_guild(ctx.guild_id, channel_id)
    await ctx.respond(CM_UPDATE_SUCCESS, ephemeral=True)
    atcf.reset()


@bot.slash_command(name="set_basins", description=CM_SET_BASINS)
@guild_only()
@default_permissions(manage_guild=True)
@commands.has_guild_permissions(manage_guild=True)
async def set_basins(
    ctx: discord.ApplicationContext,
    natl: Option(bool, CM_NATL),  # type: ignore
    epac: Option(bool, CM_EPAC),  # type: ignore
    cpac: Option(bool, CM_CPAC),  # type: ignore
    wpac: Option(bool, CM_WPAC),  # type: ignore
    nio: Option(bool, CM_NIO),  # type: ignore
    shem: Option(bool, CM_SHEM),  # type: ignore
):
    await ctx.defer(ephemeral=True)
    # fmt: off
    # this effectively represents a 6-bit binary value
    enabled_basins = f"{int(natl)}{int(epac)}{int(cpac)}{int(wpac)}{int(nio)}{int(shem)}"
    # fmt: on
    server_vars.write("basins", enabled_basins, ctx.guild_id)
    await ctx.respond(CM_BASINS_SAVED, ephemeral=True)


@bot.slash_command(name="update_all", description=CM_UPDATE_ALL)
@default_permissions(administrator=True)
@commands.is_owner()
async def update_all(ctx):
    await ctx.defer(ephemeral=True)
    await atcf.get_data()
    cog.last_update = math.floor(time.time())
    global_vars.write("last_update", cog.last_update)
    for guild in bot.guilds:
        channel_id = server_vars.get("tracking_channel", guild.id)
        # attempt to update only if the tracking channel is set
        if channel_id is not None:
            await update_guild(guild.id, channel_id)
    await ctx.respond(CM_UPDATE_SUCCESS, ephemeral=True)


@bot.slash_command(name="update_all_alt", description=CM_UPDATE_ALL_ALT)
@default_permissions(administrator=True)
@commands.is_owner()
async def update_all_alt(ctx):
    await ctx.defer(ephemeral=True)
    await atcf.get_data_alt()
    cog.last_update = math.floor(time.time())
    global_vars.write("last_update", cog.last_update)
    for guild in bot.guilds:
        channel_id = server_vars.get("tracking_channel", guild.id)
        # attempt to update only if the tracking channel is set
        if channel_id is not None:
            await update_guild(guild.id, channel_id)
    await ctx.respond(CM_UPDATE_SUCCESS, ephemeral=True)


@bot.slash_command(name="announce_all", description=CM_ANNOUNCE_ALL)
@default_permissions(administrator=True)
@commands.is_owner()
async def announce_all(
    ctx: discord.ApplicationContext, announcement: Option(str, CM_TO_ANNOUNCE)  # type: ignore
):
    await ctx.defer(ephemeral=True)
    for guild in bot.guilds:
        channel_id = server_vars.get("tracking_channel", guild.id)
        channel = bot.get_channel(channel_id)
        if channel is not None:
            try:
                await channel.send(announcement)
            except discord.errors.HTTPException:
                logging.warning(LOG_GUILD_UNAVAILABLE.format(guild.id))
                continue
    await ctx.respond(CM_ANNOUNCE_ALL_SUCCESS.format(announcement), ephemeral=True)


@bot.slash_command(name="announce_basin", description=CM_ANNOUNCE_BASIN)
@default_permissions(administrator=True)
@commands.is_owner()
async def announce_basin(
    ctx: discord.ApplicationContext,
    basin: Option(
        str,
        CM_BASIN_TO_ANNOUNCE,
        choices=["natl", "epac", "cpac", "wpac", "nio", "shem"],
    ),  # type: ignore
    announcement: Option(str, CM_TO_ANNOUNCE),  # type: ignore
):
    await ctx.defer(ephemeral=True)
    for guild in bot.guilds:
        channel_id = server_vars.get("tracking_channel", guild.id)
        enabled_basins = server_vars.get("basins", guild.id)
        channel = bot.get_channel(channel_id)
        if channel is not None:
            send_message = (
                (basin == "natl" and enabled_basins[0] == "1")
                or (basin == "epac" and enabled_basins[1] == "1")
                or (basin == "cpac" and enabled_basins[2] == "1")
                or (basin == "wpac" and enabled_basins[3] == "1")
                or (basin == "nio" and enabled_basins[4] == "1")
                or (basin == "shem" and enabled_basins[5] == "1")
            )
            if send_message:
                try:
                    await channel.send(
                        CM_BASIN_ANNOUNCEMENT.format(basin, announcement)
                    )
                except discord.errors.HTTPException:
                    logging.warning(LOG_GUILD_UNAVAILABLE.format(guild.id))
                    continue
    await ctx.respond(
        CM_ANNOUNCE_BASIN_SUCCESS.format(basin, announcement), ephemeral=True
    )


@bot.slash_command(name="announce_file", description=CM_ANNOUNCE_FILE)
@default_permissions(administrator=True)
@commands.is_owner()
async def announce_file(
    ctx: discord.ApplicationContext,
    file: Option(discord.SlashCommandOptionType.attachment, CM_TXT_FILE),  # type: ignore
):
    await ctx.defer(ephemeral=True)
    print(file.content_type)
    if file.content_type.startswith("text"):
        with open("announcement.md", "wb") as f:
            await file.save(f)
        announcement = open("announcement.md", "r").read()
        for guild in bot.guilds:
            channel_id = server_vars.get("tracking_channel", guild.id)
            channel = bot.get_channel(channel_id)
            if channel is not None:
                try:
                    await channel.send(announcement)
                except discord.errors.HTTPException:
                    logging.warning(LOG_GUILD_UNAVAILABLE.format(guild.id))
                    continue
        await ctx.respond(CM_ANNOUNCE_ALL_SUCCESS.format(announcement), ephemeral=True)
    else:
        await ctx.respond(ERROR_NOT_A_TXT_FILE, ephemeral=True)


@bot.slash_command(name="invite", description=CM_INVITE)
async def invite(ctx):
    await ctx.respond(CM_INVITE_MESSAGE.format(INVITE), ephemeral=True)


def total_member_count() -> int:
    member_count = 0
    for guild in bot.guilds:
        member_count += guild.member_count
    return member_count


@bot.slash_command(name="statistics", description=CM_STATISTICS_DESC)
async def statistics(ctx):
    await ctx.defer()
    strongest_storm = global_vars.get("strongest_storm")
    if strongest_storm is None:
        # If the above method returned None then it means that it cannot load the JSON file.
        await ctx.respond(ERROR_NO_GLOBAL_VARS, ephemeral=True)
        return
    yikes_count = global_vars.get("yikes_count")
    guild_count = global_vars.get("guild_count")
    await ctx.respond(
        CM_STATISTICS.format(
            guild_count,
            strongest_storm,
            yikes_count,
            process_uptime_human_readable(),
            total_member_count(),
        )
    )


@bot.slash_command(name="yikes", description=CM_YIKES)
async def yikes(ctx: discord.ApplicationContext):
    await ctx.defer(ephemeral=True)
    count = global_vars.get("yikes_count")
    if count is not None:
        count += 1
    else:
        count = 1
    global_vars.write("yikes_count", count)
    for guild in bot.guilds:
        channel_id = server_vars.get("tracking_channel", guild.id)
        channel = bot.get_channel(channel_id)
        if channel is not None:
            await channel.send(CM_INC_YIKES_COUNT.format(count))
    logging.info(CM_INC_YIKES_COUNT.format(ctx.author, ctx.author.id))
    await ctx.respond(CM_YIKES_RESPONSE.format(count))


@bot.slash_command(name="get_data", description=CM_GET_DATA)
@default_permissions(administrator=True)
@commands.is_owner()
async def get_data(ctx):
    await ctx.defer(ephemeral=True)
    try:
        await atcf.get_data()
        cog.last_update = math.floor(time.time())
        global_vars.write("last_update", cog.last_update)
        with open("atcf_sector_file", "r") as f:
            content = f.read()
            await ctx.respond(CM_GET_DATA_SUCCESS.format(content), ephemeral=True)
    except atcf.ATCFError as e:
        await ctx.respond(CM_GET_DATA_FAILED.format(e), ephemeral=True)


@bot.slash_command(name="get_data_alt", description=CM_GET_DATA_ALT)
@default_permissions(administrator=True)
@commands.is_owner()
async def get_data_alt(ctx):
    await ctx.defer(ephemeral=True)
    try:
        await atcf.get_data_alt()
        cog.last_update = math.floor(time.time())
        global_vars.write("last_update", cog.last_update)
        with open("atcf_sector_file", "r") as f:
            content = f.read()
            await ctx.respond(CM_GET_DATA_SUCCESS.format(content), ephemeral=True)
    except atcf.ATCFError as e:
        await ctx.respond(CM_GET_DATA_FAILED.format(e), ephemeral=True)


@bot.slash_command(name="atcf_reset", description=CM_ATCF_RESET)
@default_permissions(administrator=True)
@commands.is_owner()
async def atcf_reset(ctx):
    atcf.reset()
    await ctx.respond(CM_ATCF_RESET_SUCCESS, ephemeral=True)


@bot.slash_command(name="github", description=CM_GITHUB)
async def github(ctx):
    await ctx.respond(CM_GITHUB_RESPONSE.format(GITHUB), ephemeral=True)


@bot.slash_command(name="copyright", description=CM_COPYRIGHT)
async def copyright(ctx):
    await ctx.respond(copyright_notice, ephemeral=True)


@bot.slash_command(name="rsmc_list", description=CM_RSMC_LIST)
async def rsmc_list(ctx):
    await ctx.defer(ephemeral=True)
    await ctx.respond(CM_RSMC_LIST_RESPONSE)


@bot.slash_command(name="get_log", description=CM_GET_LOG)
@default_permissions(administrator=True)
@commands.is_owner()
async def get_log(ctx):
    await ctx.defer(ephemeral=True)
    await cog.on_update_error(errors.LogRequested(LOG_REQUESTED))
    await ctx.respond(CM_LOG_SENT)


@bot.slash_command(name="suspend_updates", description=CM_SUSPEND_UPDATES)
@default_permissions(administrator=True)
@commands.is_owner()
async def suspend_updates(ctx):
    await ctx.defer(ephemeral=True)
    if cog.auto_update.next_iteration is not None:
        cog.auto_update.cancel()
        await ctx.respond(CM_SUSPEND_UPDATES_SUCCESS)
    else:
        await ctx.respond(CM_UPDATES_ALREADY_SUSPENDED)


@bot.slash_command(name="resume_updates", description=CM_RESUME_UPDATES)
@default_permissions(administrator=True)
@commands.is_owner()
async def resume_updates(ctx):
    await ctx.defer(ephemeral=True)
    if cog.auto_update.next_iteration is None:
        cog.auto_update.start()
        await ctx.respond(CM_RESUME_UPDATES_SUCCESS)
    else:
        await ctx.respond(CM_UPDATES_ALREADY_RUNNING)


@bot.slash_command(name="feedback", description=CM_FEEDBACK)
async def feedback(
    ctx: discord.ApplicationContext, msg: Option(str, CM_FEEDBACK_TO_SEND)  # type: ignore
):
    await ctx.defer(ephemeral=True)
    app = await bot.application_info()
    bot_owner = app.owner
    if bot_owner is not None:
        await bot_owner.send(CM_FEEDBACK_RECEIVED.format(ctx.author, msg))
        await ctx.respond(CM_FEEDBACK_SENT.format(msg))
    else:
        await ctx.respond(CM_NO_OWNER)


@bot.slash_command(name="get_past_storm", description=CM_GET_PAST_STORM)
async def get_past_storm(
    ctx: discord.ApplicationContext,
    name: Option(str, CM_PAST_STORM_NAME, default=None),  # type: ignore
    season: Option(int, CM_PAST_STORM_SEASON, min_value=1841, default=0),  # type: ignore
    basin: Option(
        str,
        CM_PAST_STORM_BASIN,
        choices=["NA", "SA", "EP", "WP", "SP", "NI", "SI"],
        default=None,
    ),  # type: ignore
    atcf_id: Option(str, CM_PAST_STORM_ATCF, default=None),  # type: ignore
    ibtracs_id: Option(str, CM_PAST_STORM_SID, default=None),  # type: ignore
    table: Option(
        str,
        CM_PAST_STORM_TABLE,
        choices=["LastThreeYears", "AllBestTrack"],
        default="LastThreeYears",
    ),  # type: ignore
):
    await ctx.defer(ephemeral=True)
    if cog.is_best_track_updating:
        await ctx.respond(CM_WAIT_FOR_IBTRACS_UPDATE)
        response = await ctx.interaction.original_response()
        while cog.is_best_track_updating:
            await asyncio.sleep(0.25)
        await response.edit_message(content=CM_SEARCHING)
    else:
        await ctx.respond(CM_SEARCHING)
        response = await ctx.interaction.original_response()
    try:
        results = ibtracs.get_storm(
            name=name,
            season=season,
            basin=basin,
            atcf_id=atcf_id,
            ibtracs_id=ibtracs_id,
            table=table,
            lang=server_vars.get("lang", ctx.guild_id),
        )
    except ValueError as e:
        await response.edit(CM_ERROR.format(e))
        return
    if isinstance(results, GeneratorType):
        res_tmp = StringIO()
        res_tmp.write(CM_MULTIPLE_STORMS)
        lines = [f"{s}\n" for s in results]
        res_tmp.writelines(lines)
        await response.edit(res_tmp.getvalue())
        res_tmp.close()
    elif isinstance(results, ibtracs.Storm):
        peak_timestamp = int(
            datetime.datetime.fromisoformat(results.time_of_peak)
            .replace(tzinfo=datetime.UTC)
            .timestamp()
        )
        nature = results.nature().title()
        name = results.name.title()
        if name == "Not_Named":
            descriptor = CM_UNNAMED_STORM.format(nature)
        else:
            descriptor = f"{nature} {name}"
        if not results.peak_winds:
            peak_winds = CM_UNKNOWN
            peak_time = CM_UNKNOWN
        else:
            peak_winds = f"{results.peak_winds} kt"
            peak_time = f"<t:{peak_timestamp}:f>"
        if not results.peak_pres:
            peak_pres = CM_UNKNOWN
        else:
            peak_pres = f"{results.peak_pres} mb"
        if results.atcf_id is None:
            atcf_id = CM_UNKNOWN
        else:
            atcf_id = results.atcf_id
        await response.edit(
            content=CM_PAST_STORM_INFO.format(
                descriptor,
                results.season,
                results.basin,
                peak_winds,
                peak_pres,
                peak_time,
                atcf_id,
                results.best_track_id,
            )
        )
    elif results is None:
        await response.edit(content=CM_NO_RESULTS)
    else:
        # you should never see this error ;-)
        raise TypeError(ERROR_WTF.format(type(results)))


@bot.slash_command(name="set_language", description=CM_SET_LANGUAGE)
@default_permissions(manage_guild=True)
@commands.has_guild_permissions(manage_guild=True)
async def set_language(
    ctx: discord.ApplicationContext,
    language: Option(str, CM_LANG_TO_USE, choices=languages),  # type: ignore
):
    await ctx.defer(ephemeral=True)
    server_vars.write("lang", language, ctx.guild.id)
    set_locale(language)
    await ctx.respond(CM_SET_LANGUAGE_SUCCESS.format(language))


async def storms(ctx: discord.AutocompleteContext):
    return [n for n in atcf.names if n != "INVEST"]


@bot.slash_command(name="get_forecast", description=CM_GET_FORECAST)
async def get_forecast(
    ctx: discord.ApplicationContext,
    name: Option(
        str, CM_STORM_NAME, autocomplete=discord.utils.basic_autocomplete(storms)
    ),  # type: ignore
):
    await ctx.defer()
    name = name.upper()
    if name == "INVEST":
        await ctx.respond(CM_IS_AN_INVEST)
        return

    try:
        ext = await atcf.get_forecast(name=name)
    except atcf.NoActiveStorms:
        await ctx.respond(CM_NO_ACTIVE_STORMS)
    except Exception as e:
        await on_application_command_error(ctx, e)
    else:
        if ext is None:
            await ctx.respond(
                CM_CANNOT_FIND_STORM.format(
                    "\n".join([n for n in atcf.names if n != "INVEST"])
                )
            )
        else:
            with open(f"forecast.{ext}", "rb") as f:
                await ctx.respond(file=discord.File(f))


@bot.slash_command(name="server", description=CM_SERVER)
async def server(ctx: discord.ApplicationContext):
    await ctx.respond(SERVER, ephemeral=True)


async def guilds(ctx: discord.AutocompleteContext):
    return [str(guild.id) for guild in bot.guilds]


@bot.slash_command(name="contact_guild", description="Attempt to message a guild")
@default_permissions(administrator=True)
@commands.is_owner()
async def contact_guild(
    ctx: discord.ApplicationContext,
    guild: Option(str, autocomplete=discord.utils.basic_autocomplete(guilds)),  # type: ignore
    message: str,
):
    # stupid limitations require me to make the ID a string
    # now we have to convert it back to an int
    guild = int(guild)
    await ctx.defer(ephemeral=True)
    to_guild = bot.get_guild(guild)
    if to_guild is None:
        raise ValueError
    channel_id = server_vars.get("tracking_channel", guild)
    channel = bot.get_channel(channel_id)
    channel = get_first_available_channel(to_guild) if channel is None else channel
    if channel is None:
        await ctx.respond("No channels available in this server.", ephemeral=True)
        return
    await channel.send(f"Message from the developer:\n{message}")
    await ctx.respond(f"Successfully sent to {to_guild}:\n{message}", ephemeral=True)


@help.command(name="general", description=CM_HELP_GENERAL)
async def help_general(ctx: discord.ApplicationContext):
    await ctx.respond(CM_GENERAL_HELP)


async def help_wrapper(ctx: discord.ApplicationContext, commands: int):
    await ctx.defer()
    with StringIO() as ss:
        match commands:
            case 0:
                info = CM_INTERNAL_COMMANDS
                command_set = INTERNAL_COMMANDS
            case 1:
                info = CM_ADMIN_COMMANDS
                command_set = ADMIN_COMMANDS
            case 2:
                info = CM_CONFIG_COMMANDS
                command_set = CONFIG_COMMANDS
            case 3:
                info = CM_USEFUL_COMMANDS
                command_set = USEFUL_COMMANDS
            case 4:
                info = CM_COMMON_COMMANDS
                command_set = COMMON_COMMANDS
            case _:  # output all commands by default
                info = CM_ALL_COMMANDS
                command_set = COMMON_COMMANDS | ADMIN_COMMANDS
        ss.write(info)
        for command in command_set:
            cmd_real = bot.get_application_command(command)
            if not isinstance(cmd_real, discord.SlashCommand):
                continue
            ss.write(f"`/{cmd_real.qualified_name}` -- {cmd_real.description}\n")
        await ctx.respond(ss.getvalue())


@help.command(name="common", description=CM_HELP_COMMON)
async def help_common(ctx: discord.ApplicationContext):
    await help_wrapper(ctx, 4)


@help.command(name="useful", description=CM_HELP_USEFUL)
async def help_useful(ctx: discord.ApplicationContext):
    await help_wrapper(ctx, 3)


@help.command(name="admin", description=CM_HELP_ADMIN)
async def help_admin(ctx: discord.ApplicationContext):
    await help_wrapper(ctx, 1)


@help.command(name="config", description=CM_HELP_CONFIG)
async def help_config(ctx: discord.ApplicationContext):
    await help_wrapper(ctx, 2)


@help.command(name="internal", description=CM_HELP_INTERNAL)
async def help_internal(ctx: discord.ApplicationContext):
    await help_wrapper(ctx, 0)


@help.command(name="all", description=CM_HELP_ALL)
async def help_all(ctx: discord.ApplicationContext):
    await help_wrapper(ctx, 5)


def commands(ctx: discord.AutocompleteContext):
    return [
        cmd.qualified_name
        for cmd in bot.walk_application_commands()
        if isinstance(cmd, discord.SlashCommand)
    ]


@help.command(name="command", description=CM_HELP_COMMAND)
async def help_command(
    ctx: discord.ApplicationContext,
    cmd: Option(
        str, CM_WHICH_COMMAND, autocomplete=discord.utils.basic_autocomplete(commands)
    ),  # type: ignore
):
    await ctx.defer()
    cmd_real = bot.get_application_command(cmd)
    if not isinstance(cmd_real, discord.SlashCommand):
        raise TypeError(ERROR_WTF.format(type(cmd_real)))
    ext_desc = globals().get(
        f"CM_EXTENDED_{cmd_real.qualified_name.upper().replace(" ", "_")}",
        MISSING_DESCRIPTION,
    )
    with StringIO() as ss:
        ss.write(f"# {cmd_real.qualified_name}\n")
        ss.write(f"`/{cmd_real.qualified_name}` -- {cmd_real.description}\n")
        ss.write(ext_desc)
        ss.write("\n")
        if cmd_real.options:
            ss.write(PARAMETERS)
            for option in cmd_real.options:
                ss.write(f"`{option.name}` -- {option.description}\n")
        else:
            ss.write(HAS_NO_PARAMETERS)
        if cmd in INTERNAL_COMMANDS:
            ss.write("\n")
            ss.write(FOR_INTERNAL_USE_ONLY)
        await ctx.respond(ss.getvalue())
