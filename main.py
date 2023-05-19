import discord
from discord import option, default_permissions, SlashCommandOptionType, guild_only, Option
from discord.ext import tasks, commands
import math
import server_vars
import atcf
import datetime
import asyncio

token = 'your.token.here'
bot=discord.Bot(intents=discord.Intents.default())
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
    
async def update_guild(guild: int, to_channel: int):
    channel = bot.get_channel(to_channel)
    enabled_basins = server_vars.get("basins",guild)
    if enabled_basins is not None:        
        for i in range(len(atcf.cyclones)):
            cyc_id = atcf.cyclones[i]
            basin = cyc_id[2]
            wind = atcf.winds[i]
            mph = round(wind * 1.15077945 / 5) * 5
            kmh = round(wind * 1.852 / 5) * 5
            name = atcf.names[i]
            timestamp = atcf.timestamps[i]
            lat = atcf.lats[i]
            long = atcf.longs[i]
            pressure = atcf.pressures[i]
            if name == "INVEST":
                tc_class = "INVEST"
                name = cyc_id
            elif wind < 35:
                tc_class = "TROPICAL DEPRESSION"
            elif wind > 34 and wind < 65:
                tc_class = "TROPICAL STORM"
            else:
                if basin == "L" or basin == "E" or basin == "C":
                    tc_class = "HURRICANE"
                elif basin == "W":
                    if wind < 130:
                        tc_class = "TYPHOON"
                    else:
                        tc_class = "SUPER TYPHOON"
                else:
                    tc_class = "CYCLONE"
            send_message = (basin == "L" and enabled_basins[0] == "1") or ((basin == "E" or basin == "C") and enabled_basins[1] == "1") or (basin == "W" and enabled_basins[2] == "1") or ((basin == "A" or basin == "B") and enabled_basins[3] == "1") or (basin == "S" and enabled_basins[4] == "1") or (basin == "P" and enabled_basins[5] == "1")
            if send_message:
                await channel.send(f"{tc_class} {name} as of <t:{timestamp}:f>\nPosition: {lat}, {long}\nMax 1-minute sustained winds: {wind} kt ({mph} mph/{kmh} kph)\nMinimum central pressure: {pressure} mb")
        await channel.send("For north Atlantic and eastern Pacific storms, see https://www.nhc.noaa.gov for more information.\nFor others, check your RSMC website or see https://www.metoc.navy.mil/jtwc/jtwc.html for more information.")

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching,name="cyclones around the world!"))
    print(f"We have logged in as {bot.user}")
    for guild in bot.guilds:
        print(guild)
    cog = monitor(bot)

@bot.event
async def on_guild_join(guild: discord.Guild):
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            await channel.send("Thanks for adding me!\nTo configure this bot for your server, first set the channel for cyclone updates to be posted in with `/set_tracking_channel`. Then set the basins you'd like to see with `/set_basins`.")
            break

@bot.slash_command(name="ping",description="Test the response time")
async def ping(ctx: commands.Context):
    await ctx.respond(f"Pong! `"+str(math.floor(bot.latency*1000))+" ms`")

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
    epac: Option(bool, "Northeastern and north central Pacific"),
    wpac: Option(bool, "Northwestern Pacific"),
    nio: Option(bool, "North Indian Ocean (Arabian Sea and Bay of Bengal)"),
    sio: Option(bool, "South Indian Ocean (including western Australia)"),
    spac: Option(bool, "South Pacific (including eastern Australia)")
):
    enabled_basins = str(int(natl)) + str(int(epac)) + str(int(wpac)) + str(int(nio)) + str(int(sio)) + str(int(spac))
    server_vars.write("basins",enabled_basins,ctx.guild_id)
    await ctx.respond("Basin configuration saved.",ephemeral=True)

@bot.slash_command(name="update_all",description="Force CycloMonitor to update all guilds immediately")
@commands.is_owner()
async def update_all(ctx):
    atcf.get_data()
    for guild in bot.guilds:
        channel_id = server_vars.get("tracking_channel",guild.id)
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
    basin: Option(str, "Basin which this applies to",choices=["natl","epac","wpac","nio","sio","spac"]),
    announcement: Option(str, "Message to announce")
):
    for guild in bot.guilds:
        channel_id = server_vars.get("tracking_channel",guild.id)
        enabled_basins = server_vars.get("basins",guild.id)
        if channel_id is not None:
            channel = bot.get_channel(channel_id)
            send_message = (basin == "natl" and enabled_basins[0] == "1") or (basin == "epac" and enabled_basins[1] == "1") or (basin == "wpac" and enabled_basins[2] == "1") or (basin == "nio" and enabled_basins[3] == "1") or (basin == "sio" and enabled_basins[4] == "1") or (basin == "spac" and enabled_basins[5] == "1")
            if send_message:
                await channel.send(f"Announcement for {basin}:\n{announcement}")
    await ctx.respond(f"Announced for {basin}:\n{announcement}",ephemeral=True)

@bot.slash_command(name="invite",description="Add this bot to your server!")
async def invite(ctx):
    # If you plan on using this for yourself, remember to change the OAuth2 URL.
    await ctx.respond("Here's my invite link!\n<https://discord.com/api/oauth2/authorize?client_id=1107462705004167230&permissions=67233792&scope=bot>",ephemeral=True)

bot.run(token)