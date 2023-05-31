import discord
from discord import option, default_permissions, SlashCommandOptionType, guild_only, Option
from discord.ext import tasks, commands
import math
import server_vars
import global_vars
import atcf
import datetime
import calendar

token = 'your.token.here'
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
        self.auto_update.start()

    def cog_unload(self):
        self.auto_update.cancel()

    @tasks.loop(time=times)
    async def auto_update(self):
        atcf.get_data()
        for guild in bot.guilds:
            channel_id = server_vars.get("tracking_channel",guild.id)
            if channel_id is not None:
                await update_guild(guild.id,channel_id)
    
    @auto_update.error
    async def on_update_error(self, error):
        for guild in bot.guilds:
            channel_id = server_vars.get("tracking_channel",guild.id)
            if channel_id is not None:
                channel = bot.get_channel(channel_id)
                await channel.send(f"CycloMonitor encountered an error while updating. This incident has be reported to the bot owner.")
        print(f"CycloMonitor encountered an error while updating. Here's what happened:\n{error}")

# this function needs to be a coroutine since other coroutines are called
async def update_guild(guild: int, to_channel: int):
    channel = bot.get_channel(to_channel)
    enabled_basins = server_vars.get("basins",guild)
    current_TC_record = global_vars.get("strongest_storm") # record-keeping
    if enabled_basins is not None:
        for i in range(len(atcf.cyclones)):
            cyc_id = atcf.cyclones[i]
            basin = atcf.basins[i]
            wind = atcf.winds[i] # winds are tracked internally in knots (kt)
            mph = round(wind * 1.15077945 / 5) * 5 # per standard, we round to the nearest 5
            kmh = round(wind * 1.852 / 5) * 5
            name = atcf.names[i]
            timestamp = atcf.timestamps[i]
            lat = atcf.lats[i]
            long = atcf.longs[i]
            pressure = atcf.pressures[i]
            if pressure == 0:
                pressure = math.nan
            sent_list = []
            # we should ignore wind speeds for designating an invest
            # all wind speed values shown are in knots rounded to the nearest 5 (except for ones after > operators)
            if name == "INVEST":
                tc_class = "INVEST"
                name = cyc_id
                emoji = "<:low:1109997033227558923>"
            elif wind < 35:
                tc_class = "TROPICAL DEPRESSION"
                emoji = "<:td:1109994651169079297>"
            elif wind > 34 and wind < 65:
                tc_class = "TROPICAL STORM"
                emoji = "<:ts:1109994652368650310>"
            else:
                # determine the term to use based on the basin
                if basin == "ATL" or basin == "EPAC" or basin == "CPAC":
                    tc_class = "HURRICANE"
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
            # update TC records
            if (wind > int(current_TC_record[5])) or (wind == int(current_TC_record[5]) and pressure < int(current_TC_record[8])):
                global_vars.write("strongest_storm",[emoji,tc_class,cyc_id,name,str(timestamp),str(wind),str(mph),str(kmh),str(pressure)])

            # this check is really long since it needs to accomodate for every possible situation
            send_message = (basin == "ATL" and enabled_basins[0] == "1") or (basin == "EPAC" and enabled_basins[1] == "1") or (basin == "CPAC" and enabled_basins[2] == "1") or (basin == "WPAC" and enabled_basins[3] == "1") or (basin == "IO" and enabled_basins[4] == "1") or (basin == "SHEM" and enabled_basins[5] == "1")
            sent_list.append(send_message)
            if math.isnan(pressure):
                pressure = "N/A"
            if send_message:
                await channel.send(f"# {emoji} {tc_class} {name}\nAs of <t:{timestamp}:f>, the center of {name} was located near {lat}, {long}. Maximum 1-minute sustained winds were {wind} kt ({mph} mph/{kmh} kph) and the minimum central pressure was {pressure} mb.")
            for was_sent in sent_list:
                if was_sent:
                    break
            else:
                await channel.send(f"No TCs or areas of interest active at this time.\nNext automatic update: <t:{calendar.timegm(cog.auto_update.next_iteration.utctimetuple())}:f>")
        # it is best practice to use official sources when possible
        await channel.send("For north Atlantic and eastern Pacific storms, see https://www.nhc.noaa.gov for more information.\nFor others, check your RSMC website or see https://www.metoc.navy.mil/jtwc/jtwc.html for more information.")

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching,name="cyclones around the world!"))
    print(f"We have logged in as {bot.user}")
    for guild in bot.guilds:
        print(guild)
    global cog
    # this will trigger the __init__ function which will start the automated monitoring
    cog = monitor(bot)

@bot.event
async def on_guild_join(guild: discord.Guild):
    count = len(bot.guilds)
    global_vars.write("guild_count",count)
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            await channel.send("Thanks for adding me!\nTo configure this bot for your server, first set the channel for cyclone updates to be posted in with `/set_tracking_channel`. Then set the basins you'd like to see with `/set_basins`.")
            break

@bot.event
async def on_guild_remove(guild: discord.Guild):
    count = len(bot.guilds)
    server_vars.remove_guild(guild.id)
    global_vars.write("guild_count",count)

@bot.slash_command(name="ping",description="Test the response time")
async def ping(ctx: commands.Context):
    await ctx.respond(f"Pong! `"+str(math.floor(bot.latency*1000))+" ms`",ephemeral=True)

@bot.slash_command(name="set_tracking_channel",description="Set the tracking channel")
@guild_only()
@commands.has_guild_permissions(manage_channels=True)
@option(
    "channel",
    SlashCommandOptionType.channel,
    description="The channel to use"
)
async def set_tracking_channel(ctx,channel):
    if not isinstance(channel, discord.TextChannel):
        await ctx.respond(f"Error: Must be a text channel!",ephemeral=True)
    else:
        server_vars.write("tracking_channel",channel.id,ctx.guild_id)
        await ctx.respond(f"Successfully set the tracking channel to {channel}!",ephemeral=True)

@bot.slash_command(name="update",description="Cause CycloMonitor to update immediately")
@guild_only()
@commands.has_guild_permissions(manage_messages=True)
async def update(ctx):
    channel_id = server_vars.get("tracking_channel",ctx.guild_id)
    atcf.get_data()
    if channel_id is not None:
        await update_guild(ctx.guild_id,channel_id)
        await ctx.respond("Updated!",ephemeral=True)
    else:
        await ctx.respond("Tracking channel is not set!",ephemeral=True)
        
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
    enabled_basins = str(int(natl)) + str(int(epac)) + str(int(cpac)) + str(int(wpac)) + str(int(nio)) + str(int(shem)) # this effectively represents a 6-bit binary value
    server_vars.write("basins",enabled_basins,ctx.guild_id)
    await ctx.respond("Basin configuration saved.",ephemeral=True)

@bot.slash_command(name="update_all",description="Force CycloMonitor to update all guilds immediately")
@commands.is_owner()
async def update_all(ctx):
    atcf.get_data()
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
    for guild in bot.guilds:
        channel_id = server_vars.get("tracking_channel",guild.id)
        enabled_basins = server_vars.get("basins",guild.id)
        if channel_id is not None:
            channel = bot.get_channel(channel_id)
            send_message = (basin == "natl" and enabled_basins[0] == "1") or (basin == "epac" and enabled_basins[1] == "1") or (basin == "cpac" and enabled_basins[2] == "1") or (basin == "wpac" and enabled_basins[3] == "1") or (basin == "nio" and enabled_basins[4] == "1") or (basin == "shem" and enabled_basins[5] == "1")
            if send_message:
                await channel.send(f"Announcement for {basin}:\n{announcement}")
    await ctx.respond(f"Announced for {basin}:\n{announcement}",ephemeral=True)

@bot.slash_command(name="invite",description="Add this bot to your server!")
async def invite(ctx):
    # Remember to change the link if you are running your own instance of the bot!
    await ctx.respond("Here's my invite link!\n<https://discord.com/api/oauth2/authorize?client_id=1107462705004167230&permissions=67233792&scope=bot>",ephemeral=True)

@bot.slash_command(name="statistics",description="Show this bot's records")
async def statistics(ctx):
    strongest_storm = global_vars.get("strongest_storm")
    yikes_count = global_vars.get("yikes_count")
    guild_count = global_vars.get("guild_count")
    await ctx.respond(
        f"# CycloMonitor statistics\n\
Currently serving {guild_count} guilds.\n\
Strongest cyclone recorded by this bot: {strongest_storm[0]} {strongest_storm[1]} {strongest_storm[2]} ({strongest_storm[3]})\n\
- Wind peak: {strongest_storm[5]} kt ({strongest_storm[6]} mph/{strongest_storm[7]} kph)\n\
- Pressure peak: {strongest_storm[8]} mb\n\
- Time recorded: <t:{strongest_storm[4]}:f>\n\
Current yikes counter: {yikes_count}"
    )

@bot.slash_command(name="yikes",description="Yikes!")
async def yikes(ctx):
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
    await ctx.respond(f"# Yikes!\nThe yikes count is now {count}.")

bot.run(token)