copyright_notice = """
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
import calendar
import warnings
import logging
from uptime import *
from sys import exit

logname='bot.log'
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
    logging.critical("Another instance of CycloMonitor is already running!")
    exit(1)
except NameError:
    pass

token = open('TOKEN','r').read().split()[0] # split in case of any newlines or spaces
bot=discord.Bot(intents=discord.Intents.default())
# it is ideal to put out the information as soon as possible, but there may be overrides
times=[
    datetime.time(2,0,tzinfo=datetime.UTC),
    datetime.time(8,0,tzinfo=datetime.UTC),
    datetime.time(14,0,tzinfo=datetime.UTC),
    datetime.time(20,0,tzinfo=datetime.UTC)
]

class monitor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def cog_unload(self):
        logging.info("Stopping monitor...")
        self.auto_update.cancel()
    
    def should_suppress(self,prev_timestamps: list):
        suppressed = []
        for index, (cyclone, timestamp) in enumerate(zip(atcf.cyclones, atcf.timestamps)):
            try:
                # will this system request for a suppression?
                suppressed.append(prev_timestamps[index] >= timestamp)
                logging.info(f"Comparison of timestamps for {cyclone} returned {suppressed[i]}.")
            except:
                suppressed.append(False)
        if len(atcf.cyclones) == 0:
            suppressed.append(False)
        # only suppress an automatic update if all active systems requested a suppression
        for do_suppress in suppressed:
            if not do_suppress:
                return False
        else:
            return True

    @tasks.loop(time=times)
    async def auto_update(self):
        logging.info("Beginning automatic update...")
        try:
            prev_timestamps = atcf.timestamps.copy()
        except:
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
                    channel_id = server_vars.get("tracking_channel",guild.id)
                    if channel_id is not None:
                        channel = bot.get_channel(channel_id)
                        await channel.send("Automatic update suppressed. This could be because of one of the following:\n- ATCF is taking longer to update than expected\n- ATCF is down\n- All active systems dissipated recently\n- A manual update was called recently")
                        await channel.send(f"Next automatic update: <t:{calendar.timegm(cog.auto_update.next_iteration.utctimetuple())}:f>")
                return
        for guild in bot.guilds:
            channel_id = server_vars.get("tracking_channel",guild.id)
            if channel_id is not None:
                await update_guild(guild.id,channel_id)
    
    @auto_update.error
    async def on_update_error(self, error):
        if not isinstance(error, errors.LogRequested):
            logging.exception("CycloMonitor encountered an error while updating.")
        app = await self.bot.application_info()
        bot_owner = app.owner
        if bot_owner is not None:
            try:
                with open('bot.log','rb') as log:
                    await bot_owner.send(f"ERROR ERROR PLEASE HELP\nAutomatic update failed due to an exception.\nAttaching log...",file=discord.File(log))
            except:
                logging.exception("Failed to send log to the bot owner.")
        else:
            logging.warning("Could not fetch owner.")
        if not isinstance(error, errors.LogRequested):
            for guild in bot.guilds:
                channel_id = server_vars.get("tracking_channel",guild.id)
                if channel_id is not None:
                    channel = bot.get_channel(channel_id)
                    await channel.send(f"CycloMonitor encountered an error while updating. This incident has been reported to the bot owner.")

# this function needs to be a coroutine since other coroutines are called
async def update_guild(guild: int, to_channel: int):
    logging.info(f"Performing update routines for guild {guild}")
    channel = bot.get_channel(to_channel)
    enabled_basins = server_vars.get("basins",guild)
    current_TC_record = global_vars.get("strongest_storm") # record-keeping
    if enabled_basins is not None:
        for cyc_id, basin, wind, name, timestamp, lat, long, pressure, tc_class, lat_real, long_real in zip(atcf.cyclones, atcf.basins, atcf.winds, atcf.names, atcf.timestamps, atcf.lats, atcf.longs, atcf.pressures, atcf.tc_classes, atcf.lats_real, atcf.longs_real):
            mph = round(wind * 1.15077945 / 5) * 5 # per standard, we round to the nearest 5
            kmh = round(wind * 1.852 / 5) * 5
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
            sent_list = []
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
                    global_vars.write("strongest_storm",[emoji,tc_class,cyc_id,name,str(timestamp),str(wind),str(mph),str(kmh),str(pressure)])
            else:
                logging.info("No TC record found. Creating record...")
                global_vars.write("strongest_storm",[emoji,tc_class,cyc_id,name,str(timestamp),str(wind),str(mph),str(kmh),str(pressure)])

            # this check is really long since it needs to accomodate for every possible situation
            send_message = (basin == "ATL" and enabled_basins[0] == "1") or (basin == "EPAC" and enabled_basins[1] == "1") or (basin == "CPAC" and enabled_basins[2] == "1") or (basin == "WPAC" and enabled_basins[3] == "1") or (basin == "IO" and enabled_basins[4] == "1") or (basin == "SHEM" and enabled_basins[5] == "1")
            sent_list.append(send_message)
            if math.isnan(pressure):
                pressure = "N/A"
            if send_message:
                await channel.send(f"# {emoji} {tc_class} {display_name}\nAs of <t:{timestamp}:f>, the center of {name} was located near {lat}, {long}. Maximum 1-minute sustained winds were {wind} kt ({mph} mph/{kmh} kph) and the minimum central pressure was {pressure} mb.")

        for was_sent in sent_list:
            if was_sent:
                break
        else:
            await channel.send(f"No TCs or areas of interest active at this time.")
        if len(atcf.cyclones) == 0:
            await channel.send(f"No TCs or areas of interest active at this time.")
        # it is best practice to use official sources when possible
        await channel.send(f"Next automatic update: <t:{calendar.timegm(cog.auto_update.next_iteration.utctimetuple())}:f>")
        await channel.send("For more information, check your local RSMC website (see `/rsmc_list`) or go to <https://www.metoc.navy.mil/jtwc/jtwc.html>.")

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching,name="cyclones around the world!"))
    logging.info(f"We have logged in as {bot.user}")
    global_vars.write("guild_count",len(bot.guilds))
    global cog
    # stop the monitor if it is already running
    # this is to prevent a situation where there are two instances of the task running in some edge cases
    try:
        cog.auto_update.stop()
    except NameError:
        pass
    cog = monitor(bot)
    cog.auto_update.start()

@bot.event
async def on_guild_join(guild: discord.Guild):
    logging.info(f"Bot added to guild: {guild.name}")
    count = len(bot.guilds)
    global_vars.write("guild_count",count)
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            await channel.send("Thanks for adding me!\nTo configure this bot for your server, first set the channel for cyclone updates to be posted in with `/set_tracking_channel`. Then set the basins you'd like to see with `/set_basins`.")
            break

@bot.event
async def on_guild_remove(guild: discord.Guild):
    logging.info(f"Bot removed from guild: {guild.name}")
    count = len(bot.guilds)
    server_vars.remove_guild(guild.id)
    global_vars.write("guild_count",count)

@bot.event
async def on_application_command_error(ctx: discord.ApplicationContext, error):
    if isinstance(error, commands.errors.MissingPermissions) or isinstance(error, commands.errors.NotOwner):
        try:
            await ctx.respond("You do not have permission to use this command. This incident will be reported.",ephemeral=True)
        except:
            logging.exception("Failed to send response.")
        logging.warn(f"User {ctx.author} attempted to execute {ctx.command.name}, but does not have permission to do so.")
    elif isinstance(error, commands.errors.NoPrivateMessage):
        try:
            await ctx.respond("This command cannot be used in a DM context.",ephemeral=True)
        except:
            logging.exception("Failed to send response.")
    else:
        logging.exception(f"An exception occurred while executing command {ctx.command.name}.\n{error}")
        try:
            await ctx.respond(f"An exception occurred while executing this command.\n{error}",ephemeral=True)
        except:
            logging.exception("Failed to send response.")

@bot.slash_command(name="ping",description="Test the response time")
async def ping(ctx):
    await ctx.defer(ephemeral=True)
    await ctx.respond(f"Pong! `"+str(math.floor(bot.latency*1000))+" ms`",ephemeral=True)

@bot.slash_command(name="set_tracking_channel",description="Set the tracking channel")
@guild_only()
@commands.has_guild_permissions(manage_channels=True)
@option(
    "channel",
    discord.TextChannel,
    description="The channel to use"
)
async def set_tracking_channel(ctx,channel):
    await ctx.defer(ephemeral=True)
    if not isinstance(channel, discord.TextChannel):
        await ctx.respond(f"Error: Must be a text channel!",ephemeral=True)
    else:
        if channel.permissions_for(ctx.me).send_messages:
            server_vars.write("tracking_channel",channel.id,ctx.guild_id)
            await ctx.respond(f"Successfully set the tracking channel to {channel}!",ephemeral=True)
        else:
            await ctx.respond(f"I cannot send messages to that channel! Give me permission to send messages there, or try a different channel.",ephemeral=True)

@bot.slash_command(name="update",description="Cause CycloMonitor to update immediately")
@guild_only()
@commands.has_guild_permissions(manage_messages=True)
async def update(ctx):
    await ctx.defer(ephemeral=True)
    channel_id = server_vars.get("tracking_channel",ctx.guild_id)
    atcf.get_data()
    if channel_id is not None:
        await update_guild(ctx.guild_id,channel_id)
        await ctx.respond("Updated!",ephemeral=True)
    else:
        await ctx.respond("Tracking channel is not set!",ephemeral=True)
    atcf.reset()
    
@bot.slash_command(name="update_alt",description="Cause CycloMonitor to update immediately (Fallback source)")
@guild_only()
@commands.has_guild_permissions(manage_messages=True)
async def update_alt(ctx):
    await ctx.defer(ephemeral=True)
    channel_id = server_vars.get("tracking_channel",ctx.guild_id)
    atcf.get_data_alt()
    if channel_id is not None:
        await update_guild(ctx.guild_id,channel_id)
        await ctx.respond("Updated!",ephemeral=True)
    else:
        await ctx.respond("Tracking channel is not set!",ephemeral=True)
    atcf.reset()
        
@bot.slash_command(name="set_basins",description="Set basins to track")
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
    enabled_basins = str(int(natl)) + str(int(epac)) + str(int(cpac)) + str(int(wpac)) + str(int(nio)) + str(int(shem)) # this effectively represents a 6-bit binary value
    server_vars.write("basins",enabled_basins,ctx.guild_id)
    await ctx.respond("Basin configuration saved.",ephemeral=True)

@bot.slash_command(name="update_all",description="Force CycloMonitor to update all guilds immediately")
@commands.is_owner()
async def update_all(ctx):
    await ctx.defer(ephemeral=True)
    atcf.get_data()
    for guild in bot.guilds:
        channel_id = server_vars.get("tracking_channel",guild.id)
        # attempt to update only if the tracking channel is set
        if channel_id is not None:
            await update_guild(guild.id,channel_id)
    await ctx.respond("Updated!",ephemeral=True)

@bot.slash_command(name="update_all_alt",description="Force CycloMonitor to update all guilds immediately (Fallback source)")
@commands.is_owner()
async def update_all_alt(ctx):
    await ctx.defer(ephemeral=True)
    atcf.get_data_alt()
    for guild in bot.guilds:
        channel_id = server_vars.get("tracking_channel",guild.id)
        # attempt to update only if the tracking channel is set
        if channel_id is not None:
            await update_guild(guild.id,channel_id)
    await ctx.respond("Updated!",ephemeral=True)

@bot.slash_command(name="announce_all",description="Make an announcement to all servers")
@commands.is_owner()
async def announce_all(
    ctx: discord.ApplicationContext,
    announcement: Option(str, "Message to announce")
):
    await ctx.defer(ephemeral=True)
    for guild in bot.guilds:
        channel_id = server_vars.get("tracking_channel",guild.id)
        if channel_id is not None:
            channel = bot.get_channel(channel_id)
            await channel.send(announcement)
    await ctx.respond(f"Announced to all servers:\n{announcement}",ephemeral=True)

@bot.slash_command(name="announce_basin",description="Make an announcement regarding a specific basin")
@commands.is_owner()
async def announce_basin(
    ctx: discord.ApplicationContext,
    basin: Option(str, "Basin which this applies to",choices=["natl","epac","cpac","wpac","nio","shem"]),
    announcement: Option(str, "Message to announce")
):
    await ctx.defer(ephemeral=True)
    for guild in bot.guilds:
        channel_id = server_vars.get("tracking_channel",guild.id)
        enabled_basins = server_vars.get("basins",guild.id)
        if channel_id is not None:
            channel = bot.get_channel(channel_id)
            send_message = (basin == "natl" and enabled_basins[0] == "1") or (basin == "epac" and enabled_basins[1] == "1") or (basin == "cpac" and enabled_basins[2] == "1") or (basin == "wpac" and enabled_basins[3] == "1") or (basin == "nio" and enabled_basins[4] == "1") or (basin == "shem" and enabled_basins[5] == "1")
            if send_message:
                await channel.send(f"Announcement for {basin}:\n{announcement}")
    await ctx.respond(f"Announced for {basin}:\n{announcement}",ephemeral=True)
    
@bot.slash_command(name="announce_file",description="Announce to all servers from a text file")
@commands.is_owner()
async def announce_file(
    ctx: discord.ApplicationContext,
    file: Option(discord.SlashCommandOptionType.attachment,"Text file")
):
    await ctx.defer(ephemeral=True)
    print(file.content_type)
    if file.content_type.startswith('text'):
        with open('announcement.md','wb') as f:
            await file.save(f)
        announcement = open('announcement.md','r').read()
        for guild in bot.guilds:
            channel_id = server_vars.get("tracking_channel",guild.id)
            if channel_id is not None:
                channel = bot.get_channel(channel_id)
                await channel.send(announcement)
        await ctx.respond(f"Announced to all servers:\n{str(announcement)}",ephemeral=True)
    else:
        await ctx.respond("Error: Not a text file!",ephemeral=True)

@bot.slash_command(name="invite",description="Add this bot to your server!")
async def invite(ctx):
    await ctx.respond("Here's my invite link!\n<https://discord.com/api/oauth2/authorize?client_id=1107462705004167230&permissions=67496000&scope=bot>",ephemeral=True)

@bot.slash_command(name="statistics",description="Show this bot's records")
async def statistics(ctx):
    await ctx.defer()
    strongest_storm = global_vars.get("strongest_storm")
    if strongest_storm is None:
        # If the above method returned None then it means that it cannot load the JSON file.
        await ctx.respond("Could not get global variables.",ephemeral=True)
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

@bot.slash_command(name="yikes",description="Yikes!")
async def yikes(ctx):
    await ctx.defer(ephemeral=True)
    count = global_vars.get("yikes_count")
    if count is not None:
        count += 1
    else:
        count = 1
    global_vars.write("yikes_count",count)
    for guild in bot.guilds:
        channel_id = server_vars.get("tracking_channel",guild.id)
        if channel_id is not None:
            channel = bot.get_channel(channel_id)
            await channel.send(f"The yikes count is now {count}!")
    logging.info(f"The yikes count is now {count}!")
    await ctx.respond(f"# Yikes!\nThe yikes count is now {count}.")

@bot.slash_command(name="get_data",description="Get the latest ATCF data without triggering an update")
@commands.is_owner()
async def get_data(ctx):
    await ctx.defer(ephemeral=True)
    try:
        atcf.get_data()
        with open('atcf_sector_file','r') as f:
            content = f.read()
            await ctx.respond(f"ATCF data downloaded.\n{content}",ephemeral=True)
    except Exception as e:
        await ctx.respond(f"Could not get data!\n{e}",ephemeral=True)

@bot.slash_command(name="get_data_alt",description="Get the latest ATCF data without triggering an update (Fallback source)")
@commands.is_owner()
async def get_data_alt(ctx):
    await ctx.defer(ephemeral=True)
    try:
        atcf.get_data_alt()
        with open('atcf_sector_file','r') as f:
            content = f.read()
            await ctx.respond(f"ATCF data downloaded.\n{content}",ephemeral=True)
    except Exception as e:
        await ctx.respond(f"Could not get data!\n{e}",ephemeral=True)

@bot.slash_command(name="atcf_reset",description="Reset ATCF data back to its default state.")
@commands.is_owner()
async def atcf_reset(ctx):
    atcf.reset()
    await ctx.respond("ATCF data reset.",ephemeral=True)

@bot.slash_command(name="github",description="Link to CycloMonitor's GitHub repository")
async def github(ctx):
    # PLEASE CHANGE THE LINK IF YOU ARE FORKING THIS PROJECT.
    await ctx.respond("CycloMonitor is free software licensed under the terms of the GNU Affero General Public License Version 3. The source code is available at https://github.com/ntvmb/cyclomonitor, and the full license can be found in the repository's `LICENSE` file.\nFYI, you can use the GitHub repository to report issues.",ephemeral=True)

@bot.slash_command(name="copyright",description="Copyright notice")
async def copyright(ctx):
    await ctx.respond(copyright_notice,ephemeral=True)

@bot.slash_command(name="rsmc_list",description="A list of links Regional Specialized Meteorological Center (RSMC) websites.")
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
Philippine Atmospheric, Geophysical and Astronomical Services Administration (PAGASA): <https://bagong.pagasa.dost.gov.ph/>"
    )

@bot.slash_command(name="get_log", description="Send the log to the owner")
@commands.is_owner()
async def get_log(ctx):
    await ctx.defer(ephemeral=True)
    await cog.on_update_error(errors.LogRequested("The bot's log was requested."))
    await ctx.respond("Attempted to send the log!")

bot.run(token)
