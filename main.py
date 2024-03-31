"""
CycloMonitor - Discord bot that provides the latest information on TCs based on data from the US NRL's ATCF.
Copyright (c) 2023 Virtual Nate

This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

For those hosting a copy of this bot, you should have received a copy of the GNU Affero General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
import discord
from discord import option, default_permissions, SlashCommandOptionType, guild_only, Option
from discord.ext import tasks, commands
import math
import server_vars
import global_vars
import atcf
import errors
import datetime
import logging
import time
import asyncio
import ibtracs
from types import GeneratorType
from uptime import *
from dir_calc import get_dir
from io import StringIO
from sys import exit

copyright_notice = """
CycloMonitor - Discord bot that provides the latest information on TCs based on data from the US NRL's ATCF.
Copyright (c) 2023 Virtual Nate

This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

For those hosting a copy of this bot, you should have received a copy of the GNU Affero General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
logname = 'bot.log'
logging.basicConfig(filename=logname,
                    filemode='a',
                    format='%(asctime)s.%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)
try:
    from tendo import singleton
except ModuleNotFoundError:
    logging.warning("Module tendo not found. Single-instance checking will not be available.")

try:
    me = singleton.SingleInstance() # Prevent more than one instance from running at once
except singleton.SingleInstanceException:
    print("Another instance of CycloMonitor is already running!")
    exit(1)
except NameError:
    pass

bot = discord.Bot(intents=discord.Intents.default())
# it is ideal to put out the information as soon as possible, but there may be overrides
times = [
    datetime.time(2, 0, tzinfo=datetime.UTC),
    datetime.time(8, 0, tzinfo=datetime.UTC),
    datetime.time(14, 0, tzinfo=datetime.UTC),
    datetime.time(20, 0, tzinfo=datetime.UTC)
]
KT_TO_MPH = 1.15077945
KT_TO_KMH = 1.852


class monitor(commands.Cog):
    """This class governs automated routines."""

    def __init__(self, bot):
        self.bot = bot
        self.last_update = global_vars.get("last_update")
        self.last_ibtracs_update = global_vars.get("last_ibtracs_update")
        self.is_best_track_updating = False

    def cog_unload(self):
        logging.info("Stopping monitor...")
        self.auto_update.cancel()

    def should_suppress(self, prev_timestamps: list):
        """Compare two lists of timestamps and return a boolean."""
        suppressed = []
        for index, (cyclone, timestamp) in enumerate(zip(
            atcf.cyclones, atcf.timestamps
        )):
            try:
                # will this system request for a suppression?
                suppressed.append(prev_timestamps[index] >= timestamp)
            except IndexError:
                suppressed.append(False)
            logging.debug(f"Comparison of timestamps for {cyclone} returned {suppressed[index]}.")
        if not atcf.cyclones:
            suppressed.append(False)
        # only suppress an automatic update if all active systems requested a suppression
        for do_suppress in suppressed:
            if not do_suppress:
                return False
        return True

    @tasks.loop(time=times)
    async def auto_update(self):
        logging.info("Beginning automatic update...")
        try:
            prev_timestamps = atcf.timestamps.copy()
        except Exception:
            prev_timestamps = []
        try:
            atcf.get_data()
        except atcf.ATCFError as e:
            logging.exception("Failed to get ATCF data. Aborting update.")
            return
        if self.should_suppress(prev_timestamps):
            # try alternate source
            logging.warn("Suppression from main source called. Trying fallback source...")
            try:
                atcf.get_data_alt()
            except atcf.ATCFError as e:
                logging.exception("Failed to get ATCF data. Aborting update.")
                return
            if self.should_suppress(prev_timestamps):
                logging.warn("The most recent automatic update was suppressed. Investigate the cause.")
                for guild in bot.guilds:
                    channel_id = server_vars.get("tracking_channel", guild.id)
                    if channel_id is not None:
                        channel = bot.get_channel(channel_id)
                        await channel.send("Automatic update suppressed. This could be because of one of the following:\n- ATCF is taking longer to update than expected\n- ATCF is down\n- All active systems dissipated recently\n- A manual update was called recently")
                        await channel.send(f"Next automatic update: <t:{math.floor(cog.auto_update.next_iteration.timestamp())}:f>")
                return
        self.last_update = math.floor(time.time())
        global_vars.write("last_update", self.last_update)
        for guild in bot.guilds:
            channel_id = server_vars.get("tracking_channel", guild.id)
            if channel_id is not None:
                await update_guild(guild.id, channel_id)

    @auto_update.error
    async def on_update_error(self, error):
        if not isinstance(error, errors.LogRequested):
            logging.exception("CycloMonitor encountered an error while updating.")
        app = await self.bot.application_info()
        bot_owner = app.owner
        if bot_owner is not None:
            try:
                with open('bot.log', 'rb') as log:
                    await bot_owner.send(f"ERROR ERROR PLEASE HELP\nAutomatic update failed due to an exception.\nAttaching log...", file=discord.File(log))
            except discord.HTTPException:
                logging.exception("Failed to send log to the bot owner.")
        else:
            logging.warning("Could not fetch owner.")
        if not isinstance(error, errors.LogRequested):
            for guild in bot.guilds:
                channel_id = server_vars.get("tracking_channel", guild.id)
                if channel_id is not None:
                    channel = bot.get_channel(channel_id)
                    await channel.send(f"CycloMonitor encountered an error while updating. This incident has been reported to the bot owner.")

    @tasks.loop(time=datetime.time(0, 0, tzinfo=datetime.UTC))
    async def daily_ibtracs_update(self, *, _force_full=False):
        self.is_best_track_updating = True
        now = datetime.datetime.now(datetime.UTC)
        logging.info("Begin daily IBTrACS update.")
        if (now.month == 1 and now.day == 1) or _force_full:
            ibtracs.update_db("full")
        else:
            ibtracs.update_db("last3")
        global_vars.write("last_ibtracs_update", math.floor(time.time()))
        self.is_best_track_updating = False

    @daily_ibtracs_update.error
    async def on_ibtracs_update_error(self, error):
        logging.error("Failed to update IBTrACS data. Trying again in 10 seconds...")
        await asyncio.sleep(10)
        for i in range(4):
            try:
                logging.info(f"Attempt {i + 2}...")
                await self.daily_ibtracs_update()
            except Exception as e:
                logging.error(f"Attempt {i + 2} failed.")
                if i == 3:
                    logging.exception("Failed to get IBTrACS data after 5 attempts.")
                    self.is_best_track_updating = False
                    raise e from error
                else:
                    logging.error(f"Trying again in {10 * (i + 2)} seconds...")
                    await asyncio.sleep(10 * (i + 2))
                    continue
            else:
                break
        self.is_best_track_updating = False


# this function needs to be a coroutine since other coroutines are called
async def update_guild(guild: int, to_channel: int):
    """Given a guild ID and channel ID, post ATCF data."""
    logging.info(f"Performing update routines for guild {guild}")
    channel = bot.get_channel(to_channel)
    enabled_basins = server_vars.get("basins", guild)
    current_TC_record = global_vars.get("strongest_storm") # record-keeping
    if enabled_basins is not None:
        sent_list = []
        for (
            cyc_id, basin, wind, name, timestamp, lat, long, pressure,
            tc_class, lat_real, long_real, movement_speed, movement_dir
        ) in zip(
            atcf.cyclones, atcf.basins, atcf.winds, atcf.names,
            atcf.timestamps, atcf.lats, atcf.longs, atcf.pressures,
            atcf.tc_classes, atcf.lats_real, atcf.longs_real,
            atcf.movement_speeds, atcf.movement_dirs
        ):
            mph = round(wind * KT_TO_MPH / 5) * 5 # per standard, we round to the nearest 5
            kmh = round(wind * KT_TO_KMH / 5) * 5
            c_dir = get_dir(movement_dir)
            if (not c_dir) or (movement_speed < 0):
                movement_str = "not available"
            else:
                movement_mph = movement_speed * KT_TO_MPH
                movement_kph = movement_speed * KT_TO_KMH
                movement_str = f"{c_dir} at {movement_speed:.0f} kt ({movement_mph:.0f} mph/{movement_kph:.0f} kph)"
            # accomodate for basin crossovers
            if lat_real > 0 and long_real > 30 and long_real < 97:
                basin = "IO"
            elif lat_real > 0 and long_real > 97:
                basin = "WPAC"
            elif lat_real > 0 and long_real < -140:
                basin = "CPAC"
            elif lat_real > 0 and ((lat_real < 7.6 and long_real < -77) or (lat_real < 10 and long_real < -85) or (lat_real < 15 and long_real < -87) or (lat_real < 16 and long_real < -92.5) or long_real < -100):
                basin = "EPAC"
            logging.info(f"Storm {cyc_id} is in {basin}.")

            if pressure == 0:
                pressure = math.nan
            '''
            Wind speeds are ignored when marking an invest.
            There is one exception, which is for subtropical cyclones, because not all agencies issue advisories/warnings on STCs (notably CPHC and JTWC).
            We can make an exception for STCs because ATCF doesn't autoflag them (more on that below).
            All wind speed values shown are in knots rounded to the nearest 5 (except for ones after > operators)
            '''
            if name == "INVEST" and (not (tc_class == "SD" or tc_class == "SS")):
                tc_class = "INVEST"
            if tc_class == "EX":
                if not name == "INVEST":
                    tc_class = "POST-TROPICAL CYCLONE"
                emoji = "<:ex:1109994645431259187>"
            elif tc_class == "LO" or tc_class == "INVEST":
                if not name == "INVEST":
                    tc_class = "POST-TROPICAL CYCLONE"
                emoji = "<:low:1109997033227558923>"
            elif (tc_class == "DB" or tc_class == "WV"):
                if not name == "INVEST":
                    tc_class = "REMNANTS OF"
                emoji = "<:remnants:1109994646932836386>"
            elif wind < 35:
                if not (tc_class == "SD" or name == "INVEST"):
                    # ignored if invest in case of autoflagging
                    # ATCF will autoflag a system to be a TD once it has attained 1-minute sustained winds of between 23 and 33 kt
                    tc_class = "TROPICAL DEPRESSION"
                    emoji = "<:td:1109994651169079297>"
                elif name == "INVEST" and not tc_class == "SD":
                    emoji = "<:low:1109997033227558923>"
                else:
                    tc_class = "SUBTROPICAL DEPRESSION"
                    emoji = "<:sd:1109994648300163142>"
            elif wind > 34 and wind < 65:
                if not (tc_class == "SS" or name == "INVEST"):
                    tc_class = "TROPICAL STORM"
                    emoji = "<:ts:1109994652368650310>"
                elif name == "INVEST" and not tc_class == "SS":
                    emoji = "<:low:1109997033227558923>"
                else:
                    tc_class = "SUBTROPICAL STORM"
                    emoji = "<:ss:1109994649654935563>"
            else:
                # determine the term to use based on the basin
                # we assume at this point that the system is either a TC or extratropical
                if basin == "ATL" or basin == "EPAC" or basin == "CPAC":
                    if wind < 100:
                        tc_class = "HURRICANE"
                    else:
                        tc_class = "MAJOR HURRICANE"
                elif basin == "WPAC":
                    if wind < 130:
                        tc_class = "TYPHOON"
                    else:
                        tc_class = "SUPER TYPHOON"
                else:
                    tc_class = "CYCLONE"

                # for custom emoji to work, the bot needs to be in the server it's from
                # you also need the emoji's ID
                if wind < 85:
                    emoji = "<:cat1:1109994357257420902>"
                elif wind > 84 and wind < 100:
                    emoji = "<:cat2:1109994593895862364>"
                elif wind > 99 and wind < 115:
                    emoji = "<:cat3:1109994641094357024>"
                elif wind > 114 and wind < 140:
                    emoji = "<:cat4:1109994643057295401>"
                elif wind > 139 and wind < 155:
                    emoji = "<:cat5:1109994644386893864>"
                elif wind > 154 and wind < 170:
                    emoji = "<:cat5intense:1111376977664954470>"
                else:
                    emoji = "<:cat5veryintense:1111378049448026126>"
            if name == "INVEST":
                name = display_name = cyc_id
            else:
                display_name = f"{cyc_id} ({name})"
            # update TC records
            if current_TC_record is not None:
                if (wind > int(current_TC_record[5])) or (wind == int(current_TC_record[5]) and pressure < int(current_TC_record[8])):
                    logging.info("Looks like we have a new record!")
                    global_vars.write("strongest_storm", [emoji, tc_class, cyc_id, name, str(timestamp), str(wind), str(mph), str(kmh), str(pressure)])
            else:
                logging.info("No TC record found. Creating record...")
                global_vars.write("strongest_storm", [emoji, tc_class, cyc_id, name, str(timestamp), str(wind), str(mph), str(kmh), str(pressure)])

            # this check is really long since it needs to accomodate for every possible situation
            send_message = (basin == "ATL" and enabled_basins[0] == "1") or (basin == "EPAC" and enabled_basins[1] == "1") or (basin == "CPAC" and enabled_basins[2] == "1") or (basin == "WPAC" and enabled_basins[3] == "1") or (basin == "IO" and enabled_basins[4] == "1") or (basin == "SHEM" and enabled_basins[5] == "1")
            sent_list.append(send_message)
            if math.isnan(pressure):
                pressure = "N/A"
            if send_message:
                try:
                    await channel.send(f"# {emoji} {tc_class} {display_name}\nAs of <t:{timestamp}:f>, the center of {name} was located near {lat}, {long}. Maximum 1-minute sustained winds were {wind} kt ({mph} mph/{kmh} kph) and the minimum central pressure was {pressure} mb. Present movement was {movement_str}.")
                except discord.HTTPError:
                    logging.warning(f"Guild {guild} is unavailable. Skipping this guild.")
                    return

        for was_sent in sent_list:
            if was_sent:
                break
        else: # no break
            await channel.send(f"No TCs or areas of interest active at this time.")
        try:
            next_run = int(cog.auto_update.next_iteration.timestamp())
        except AttributeError:
            next_run = "Auto update task is not running. Please let the owner know so they can fix this."
        # it is best practice to use official sources when possible
        await channel.send(f"Next automatic update: <t:{next_run}:f>")
        await channel.send("For more information, check your local RSMC website (see `/rsmc_list`) or go to <https://www.metoc.navy.mil/jtwc/jtwc.html>.")


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="cyclones around the world!"))
    logging.info(f"We have logged in as {bot.user}")
    global_vars.write("guild_count", len(bot.guilds))
    global cog
    # stop the monitor if it is already running
    # this is to prevent a situation where there are two instances of a task running in some edge cases
    try:
        cog.auto_update.cancel()
        cog.daily_ibtracs_update().cancel()
    except NameError:
        cog = monitor(bot)
    if cog.auto_update.next_iteration is None:
        cog.auto_update.start()
    if cog.daily_ibtracs_update.next_iteration is None:
        cog.daily_ibtracs_update.start()
    # force an automatic update if last_update is not set or more than 6 hours have passed since the last update
    if (cog.last_update is None) or (math.floor(time.time()) - cog.last_update > 21600):
        await cog.auto_update()
    # same idea as above but for IBTrACS data, and the limit is 24 hours
    if (cog.last_ibtracs_update is None) or (math.floor(time.time()) - cog.last_ibtracs_update > 86400):
        await cog.daily_ibtracs_update()


@bot.event
async def on_guild_join(guild: discord.Guild):
    logging.info(f"Bot added to guild: {guild.name}")
    count = len(bot.guilds)
    global_vars.write("guild_count", count)
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            await channel.send("Thanks for adding me!\nTo configure this bot for your server, first set the channel for cyclone updates to be posted in with `/set_tracking_channel`. Then set the basins you'd like to see with `/set_basins`.")
            break


@bot.event
async def on_guild_remove(guild: discord.Guild):
    logging.info(f"Bot removed from guild: {guild.name}")
    count = len(bot.guilds)
    server_vars.remove_guild(guild.id)
    global_vars.write("guild_count", count)


@bot.event
async def on_application_command_error(ctx: discord.ApplicationContext, error):
    if isinstance(error, commands.errors.MissingPermissions) or isinstance(error, commands.errors.NotOwner):
        try:
            await ctx.respond("You do not have permission to use this command. This incident will be reported.", ephemeral=True)
        except discord.HTTPError:
            logging.exception("Failed to send response.")
        logging.warn(f"User {ctx.author} attempted to execute {ctx.command.name}, but does not have permission to do so.")
    elif isinstance(error, commands.errors.NoPrivateMessage):
        try:
            await ctx.respond("This command cannot be used in a DM context.", ephemeral=True)
        except discord.HTTPError:
            logging.exception("Failed to send response.")
    else:
        logging.exception(f"An exception occurred while executing command {ctx.command.name}.\n{error}")
        try:
            await ctx.respond(f"An exception occurred while executing this command.\n{error}", ephemeral=True)
        except discord.HTTPError:
            logging.exception("Failed to send response.")


@bot.slash_command(name="ping", description="Test the response time")
async def ping(ctx):
    await ctx.defer(ephemeral=True)
    await ctx.respond(f"Pong! `"+str(math.floor(bot.latency*1000))+" ms`", ephemeral=True)


@bot.slash_command(name="set_tracking_channel", description="Set the tracking channel")
@guild_only()
@commands.has_guild_permissions(manage_channels=True)
@option(
    "channel",
    discord.TextChannel,
    description="The channel to use"
)
async def set_tracking_channel(ctx, channel):
    await ctx.defer(ephemeral=True)
    if not isinstance(channel, discord.TextChannel):
        await ctx.respond(f"Error: Must be a text channel!", ephemeral=True)
    else:
        if channel.permissions_for(ctx.me).send_messages:
            server_vars.write("tracking_channel", channel.id, ctx.guild_id)
            await ctx.respond(f"Successfully set the tracking channel to {channel}!", ephemeral=True)
        else:
            await ctx.respond(f"I cannot send messages to that channel! Give me permission to send messages there, or try a different channel.", ephemeral=True)


@bot.slash_command(name="update", description="Cause CycloMonitor to update immediately")
@guild_only()
@commands.has_guild_permissions(manage_messages=True)
async def update(ctx):
    await ctx.defer(ephemeral=True)
    channel_id = server_vars.get("tracking_channel", ctx.guild_id)
    atcf.get_data()
    cog.last_update = math.floor(time.time())
    global_vars.write("last_update", cog.last_update)
    if channel_id is not None:
        await update_guild(ctx.guild_id, channel_id)
        await ctx.respond("Updated!", ephemeral=True)
    else:
        await ctx.respond("Tracking channel is not set!", ephemeral=True)
    atcf.reset()


@bot.slash_command(name="update_alt", description="Cause CycloMonitor to update immediately (Fallback source)")
@guild_only()
@commands.has_guild_permissions(manage_messages=True)
async def update_alt(ctx):
    await ctx.defer(ephemeral=True)
    channel_id = server_vars.get("tracking_channel", ctx.guild_id)
    atcf.get_data_alt()
    cog.last_update = math.floor(time.time())
    global_vars.write("last_update", cog.last_update)
    if channel_id is not None:
        await update_guild(ctx.guild_id, channel_id)
        await ctx.respond("Updated!", ephemeral=True)
    else:
        await ctx.respond("Tracking channel is not set!", ephemeral=True)
    atcf.reset()


@bot.slash_command(name="set_basins", description="Set basins to track")
@guild_only()
@commands.has_guild_permissions(manage_guild=True)
async def set_basins(
    ctx: discord.ApplicationContext,
    natl: Option(bool, "North Atlantic"),
    epac: Option(bool, "Northeastern Pacific"),
    cpac: Option(bool, "North central Pacific"),
    wpac: Option(bool, "Northwestern Pacific"),
    nio: Option(bool, "North Indian Ocean (Arabian Sea and Bay of Bengal)"),
    shem: Option(bool, "Southern hemisphere")
):
    await ctx.defer(ephemeral=True)
    enabled_basins = f"{int(natl)}{int(epac)}{int(cpac)}{int(wpac)}{int(nio)}{int(shem)}" # this effectively represents a 6-bit binary value
    server_vars.write("basins", enabled_basins, ctx.guild_id)
    await ctx.respond("Basin configuration saved.", ephemeral=True)


@bot.slash_command(name="update_all", description="Force CycloMonitor to update all guilds immediately")
@commands.is_owner()
async def update_all(ctx):
    await ctx.defer(ephemeral=True)
    atcf.get_data()
    cog.last_update = math.floor(time.time())
    global_vars.write("last_update", cog.last_update)
    for guild in bot.guilds:
        channel_id = server_vars.get("tracking_channel", guild.id)
        # attempt to update only if the tracking channel is set
        if channel_id is not None:
            await update_guild(guild.id, channel_id)
    await ctx.respond("Updated!", ephemeral=True)


@bot.slash_command(name="update_all_alt", description="Force CycloMonitor to update all guilds immediately (Fallback source)")
@commands.is_owner()
async def update_all_alt(ctx):
    await ctx.defer(ephemeral=True)
    atcf.get_data_alt()
    cog.last_update = math.floor(time.time())
    global_vars.write("last_update", cog.last_update)
    for guild in bot.guilds:
        channel_id = server_vars.get("tracking_channel", guild.id)
        # attempt to update only if the tracking channel is set
        if channel_id is not None:
            await update_guild(guild.id, channel_id)
    await ctx.respond("Updated!", ephemeral=True)


@bot.slash_command(name="announce_all", description="Make an announcement to all servers")
@commands.is_owner()
async def announce_all(
    ctx: discord.ApplicationContext,
    announcement: Option(str, "Message to announce")
):
    await ctx.defer(ephemeral=True)
    for guild in bot.guilds:
        channel_id = server_vars.get("tracking_channel", guild.id)
        if channel_id is not None:
            channel = bot.get_channel(channel_id)
            await channel.send(announcement)
    await ctx.respond(f"Announced to all servers:\n{announcement}", ephemeral=True)


@bot.slash_command(name="announce_basin", description="Make an announcement regarding a specific basin")
@commands.is_owner()
async def announce_basin(
    ctx: discord.ApplicationContext,
    basin: Option(str, "Basin which this applies to", choices=["natl", "epac", "cpac", "wpac", "nio", "shem"]),
    announcement: Option(str, "Message to announce")
):
    await ctx.defer(ephemeral=True)
    for guild in bot.guilds:
        channel_id = server_vars.get("tracking_channel", guild.id)
        enabled_basins = server_vars.get("basins", guild.id)
        if channel_id is not None:
            channel = bot.get_channel(channel_id)
            send_message = (basin == "natl" and enabled_basins[0] == "1") or (basin == "epac" and enabled_basins[1] == "1") or (basin == "cpac" and enabled_basins[2] == "1") or (basin == "wpac" and enabled_basins[3] == "1") or (basin == "nio" and enabled_basins[4] == "1") or (basin == "shem" and enabled_basins[5] == "1")
            if send_message:
                await channel.send(f"Announcement for {basin}:\n{announcement}")
    await ctx.respond(f"Announced for {basin}:\n{announcement}", ephemeral=True)


@bot.slash_command(name="announce_file", description="Announce to all servers from a text file")
@commands.is_owner()
async def announce_file(
    ctx: discord.ApplicationContext,
    file: Option(discord.SlashCommandOptionType.attachment, "Text file")
):
    await ctx.defer(ephemeral=True)
    print(file.content_type)
    if file.content_type.startswith('text'):
        with open('announcement.md', 'wb') as f:
            await file.save(f)
        announcement = open('announcement.md', 'r').read()
        for guild in bot.guilds:
            channel_id = server_vars.get("tracking_channel", guild.id)
            if channel_id is not None:
                channel = bot.get_channel(channel_id)
                await channel.send(announcement)
        await ctx.respond(f"Announced to all servers:\n{announcement}", ephemeral=True)
    else:
        await ctx.respond("Error: Not a text file!", ephemeral=True)


@bot.slash_command(name="invite", description="Add this bot to your server!")
async def invite(ctx):
    await ctx.respond("Here's my invite link!\n<https://discord.com/api/oauth2/authorize?client_id=1107462705004167230&permissions=67496000&scope=bot>", ephemeral=True)


@bot.slash_command(name="statistics", description="Show this bot's records")
async def statistics(ctx):
    await ctx.defer()
    strongest_storm = global_vars.get("strongest_storm")
    if strongest_storm is None:
        # If the above method returned None then it means that it cannot load the JSON file.
        await ctx.respond("Could not get global variables.", ephemeral=True)
        return
    yikes_count = global_vars.get("yikes_count")
    guild_count = global_vars.get("guild_count")
    await ctx.respond(
        f"# CycloMonitor statistics\n\
Currently serving {guild_count} guilds.\n\
Strongest cyclone recorded by this bot: {strongest_storm[0]} {strongest_storm[1]} {strongest_storm[2]} ({strongest_storm[3]})\n\
- Wind peak: {strongest_storm[5]} kt ({strongest_storm[6]} mph/{strongest_storm[7]} kph)\n\
- Pressure peak: {strongest_storm[8]} mb\n\
- Time recorded: <t:{strongest_storm[4]}:f>\n\
Current yikes counter: {yikes_count}\n\
Bot uptime: {process_uptime_human_readable()}"
    )


@bot.slash_command(name="yikes", description="Yikes!")
async def yikes(ctx):
    await ctx.defer(ephemeral=True)
    count = global_vars.get("yikes_count")
    if count is not None:
        count += 1
    else:
        count = 1
    global_vars.write("yikes_count", count)
    for guild in bot.guilds:
        channel_id = server_vars.get("tracking_channel", guild.id)
        if channel_id is not None:
            channel = bot.get_channel(channel_id)
            await channel.send(f"The yikes count is now {count}!")
    logging.info(f"The yikes count is now {count}!")
    await ctx.respond(f"# Yikes!\nThe yikes count is now {count}.")


@bot.slash_command(name="get_data", description="Get the latest ATCF data without triggering an update")
@commands.is_owner()
async def get_data(ctx):
    await ctx.defer(ephemeral=True)
    try:
        atcf.get_data()
        cog.last_update = math.floor(time.time())
        global_vars.write("last_update", cog.last_update)
        with open('atcf_sector_file', 'r') as f:
            content = f.read()
            await ctx.respond(f"ATCF data downloaded.\n{content}", ephemeral=True)
    except atcf.ATCFError as e:
        await ctx.respond(f"Could not get data!\n{e}", ephemeral=True)


@bot.slash_command(name="get_data_alt", description="Get the latest ATCF data without triggering an update (Fallback source)")
@commands.is_owner()
async def get_data_alt(ctx):
    await ctx.defer(ephemeral=True)
    try:
        atcf.get_data_alt()
        cog.last_update = math.floor(time.time())
        global_vars.write("last_update", cog.last_update)
        with open('atcf_sector_file', 'r') as f:
            content = f.read()
            await ctx.respond(f"ATCF data downloaded.\n{content}", ephemeral=True)
    except Exception as e:
        await ctx.respond(f"Could not get data!\n{e}", ephemeral=True)


@bot.slash_command(name="atcf_reset", description="Reset ATCF data back to its default state.")
@commands.is_owner()
async def atcf_reset(ctx):
    atcf.reset()
    await ctx.respond("ATCF data reset.", ephemeral=True)


@bot.slash_command(name="github", description="Link to CycloMonitor's GitHub repository")
async def github(ctx):
    # PLEASE CHANGE THE LINK IF YOU ARE FORKING THIS PROJECT.
    await ctx.respond("CycloMonitor is free software licensed under the terms of the GNU Affero General Public License Version 3. The source code is available at https://github.com/ntvmb/cyclomonitor, and the full license can be found in the repository's `LICENSE` file.\nFYI, you can use the GitHub repository to report issues.", ephemeral=True)


@bot.slash_command(name="copyright", description="Copyright notice")
async def copyright(ctx):
    await ctx.respond(copyright_notice, ephemeral=True)


@bot.slash_command(name="rsmc_list", description="A list of links Regional Specialized Meteorological Center (RSMC) websites.")
async def rsmc_list(ctx):
    await ctx.defer(ephemeral=True)
    await ctx.respond("# RSMC list\nAtlantic (NATL) and Eastern Pacific (EPAC) - National Hurricane Center (NHC, RSMC Miami): <https://www.nhc.noaa.gov/> (Active May 15th through November 30th)\n\
Central Pacific (CPAC) - Central Pacific Hurricane Center (CPHC, RSMC Honolulu): <https://www.nhc.noaa.gov/?cpac> (Active June 1st through November 30th)\n\
Western Pacific (WPAC) - Japan Meteorological Agency (JMA, RSMC Tokyo): <https://www.jma.go.jp/bosai/map.html#contents=typhoon&lang=en>\n\
North Indian Ocean (NIO) - India Meteorological Department (IMD, RSMC New Delhi): <https://mausam.imd.gov.in/responsive/cycloneinformation.php>\n\
Southwest Indian Ocean (SWIO) - Meteo France La Réunion (MFR, RSMC La Réunion): <https://meteofrance.re/fr/cyclone>\n\
Australia Region (AUS) - Bureau of Meteorology (BOM, RSMC Melbourne): <http://www.bom.gov.au/cyclone> (Active November 1st through April 30th)\n\
South Pacific (SPAC) - Fiji Meteorological Service (FMS, RSMC Nadi): <https://www.met.gov.fj> (Active November 1st through April 30th)\n\
## Some other tropical cyclone warning centers (TCWC)\n\
Joint Typhoon Warning Center (JTWC): <https://www.metoc.navy.mil/jtwc/jtwc.html>\n\
Philippine Atmospheric, Geophysical and Astronomical Services Administration (PAGASA): <https://bagong.pagasa.dost.gov.ph/>")


@bot.slash_command(name="get_log", description="Send the log to the owner")
@commands.is_owner()
async def get_log(ctx):
    await ctx.defer(ephemeral=True)
    await cog.on_update_error(errors.LogRequested("The bot's log was requested."))
    await ctx.respond("Attempted to send the log!")


@bot.slash_command(name="suspend_updates", description="Suspend automatic updates.")
@commands.is_owner()
async def suspend_updates(ctx):
    await ctx.defer(ephemeral=True)
    if cog.auto_update.next_iteration is not None:
        cog.auto_update.cancel()
        await ctx.respond("Suspended automatic updates.")
    else:
        await ctx.respond("The auto update task already stopped.")


@bot.slash_command(name="resume_updates", description="Resume automatic updates.")
@commands.is_owner()
async def resume_updates(ctx):
    await ctx.defer(ephemeral=True)
    if cog.auto_update.next_iteration is None:
        cog.auto_update.start()
        await ctx.respond("Resumed automatic updates.")
    else:
        await ctx.respond("The auto update task is already running.")


@bot.slash_command(name="feedback", description="Send feedback to the owner.")
async def feedback(
        ctx: discord.ApplicationContext,
        msg: Option(str, "Message to send.")
):
    await ctx.defer(ephemeral=True)
    app = await bot.application_info()
    bot_owner = app.owner
    if bot_owner is not None:
        await bot_owner.send(f"Message from {ctx.author}:\n{msg}")
        await ctx.respond(f"Successfully sent to the bot owner:\n{msg}")
    else:
        await ctx.respond("I cannot find the bot owner.")


@bot.slash_command(name="get_past_storm", description="Get a storm from the best track database.")
async def get_past_storm(
    ctx: discord.ApplicationContext,
    name: Option(str, "Search by name", default=None),
    season: Option(int, "Search by year (since 1841)", min_value=1841, default=0),
    basin: Option(str, "Search by basin", choices=["NA", "SA", "EP", "WP", "SP", "NI", "SI"], default=None),
    atcf_id: Option(str, "Search by ATCF ID", default=None),
    ibtracs_id: Option(str, "Search by IBTrACS ID", default=None),
    table: Option(str, "Prefer table", choices=["LastThreeYears", "AllBestTrack"], default="LastThreeYears")
):
    await ctx.defer(ephemeral=True)
    if cog.is_best_track_updating:
        await ctx.respond("Hang on... I'm currently getting best track data...")
        response = await ctx.interaction.original_response()
        while cog.is_best_track_updating:
            await asyncio.sleep(0.25)
        await response.edit_message(content="Searching...")
    else:
        await ctx.respond("Searching...")
        response = await ctx.interaction.original_response()
    try:
        results = ibtracs.get_storm(
            name=name,
            season=season,
            basin=basin,
            atcf_id=atcf_id,
            ibtracs_id=ibtracs_id,
            table=table
        )
    except ValueError as e:
        await response.edit(f"Error: {e}")
        return
    if isinstance(results, GeneratorType):
        res_tmp = StringIO()
        res_tmp.write("Multiple storms found. Try narrowing your search down.\n")
        lines = [f"{s}\n" for s in results]
        res_tmp.writelines(lines)
        await response.edit(res_tmp.getvalue())
        res_tmp.close()
    elif isinstance(results, ibtracs.Storm):
        peak_timestamp = int(datetime.datetime.fromisoformat(results.time_of_peak).replace(tzinfo=datetime.UTC).timestamp())
        nature = results.nature().title()
        name = results.name.title()
        if name == "Not_Named":
            descriptor = f"Unnamed {nature}"
        else:
            descriptor = f"{nature} {name}"
        if not results.peak_winds:
            peak_winds = "Unknown"
            peak_time = "Unknown"
        else:
            peak_winds = f"{results.peak_winds} kt"
            peak_time = f"<t:{peak_timestamp}:f>"
        if not results.peak_pres:
            peak_pres = "Unknown"
        else:
            peak_pres = f"{results.peak_pres} mb"
        if results.atcf_id is None:
            atcf_id = "Unknown"
        else:
            atcf_id = results.atcf_id
        await response.edit(content=f"# {descriptor} ({results.season})\n\
- Basin: {results.basin}\n\
- Peak winds: {peak_winds}\n\
- Peak pressure: {peak_pres}\n\
- Time of peak: {peak_time}\n\
- ATCF ID: {atcf_id}\n\
- IBTrACS ID: {results.best_track_id}\n\
Note: if these data are inaccurate, please complain to the WMO, not me.")
    elif results is None:
        await response.edit(content="No results found. Please try again with different paramaters.")
    else:
        # you should never see this error ;-)
        raise TypeError(f"What the fuck is this? {type(results)}")

# we don't want to expose the bot's token if this script is imported
if __name__ == "__main__":
    with open('TOKEN', 'r') as f:
        _token = f.read().split()[0] # split in case of any newlines or spaces
    bot.run(_token)
