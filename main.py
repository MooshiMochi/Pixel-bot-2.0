import os
import sys
import json
import aiohttp
import asyncio
import logging
from datetime import datetime

import discord
from discord.ext import commands

import discord_slash
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils.manage_commands import create_option, create_choice
from discord_slash.error import AlreadyResponded

from dotenv import load_dotenv

from constants import const

load_dotenv(".env")

TOKEN = os.getenv("TOKEN")
TEST_MODE = False
if TEST_MODE:
    const.guild_id = 932736074139185292

    TOKEN = os.getenv("TEST_TOKEN")
    const.slash_guild_ids = [const.guild_id]
    const.prefix = "."

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.WARNING)
formatter = logging.Formatter('\x1b[38;5;203m[%(levelname)s: %(name)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
handler = logging.FileHandler(filename='logs/discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


class TNContext(commands.Context):
    async def embed(self, embed, *, footer=None):

        if footer is None:
            footer = "Titan Network"
        embed.set_footer(icon_url=self.bot.png, text=f"TitanMC | {footer}")
        embed.timestamp = datetime.utcnow()

        try:
            return await self.send(embed=embed)
        except discord.HTTPException as e:   
            raise e


class TNSlashContext(SlashContext):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def embed(self, embed, *, footer=None):

        if footer is None:
            footer = "Titan Network"
        embed.set_footer(icon_url=self.bot.png, text=f"TitanMC | {footer}")
        embed.timestamp = datetime.utcnow()

        try:
            if self.deferred:
                if not self.responded:
                    return await self.send(embed=embed, hidden=self._deferred_hidden)
                
                return await self.channel.send(embed=embed)
            if not self.responded:
                return await self.send(embed=embed)
            
            try:
                return await self.channel.send(embed=embed)
            except AlreadyResponded:
                guild = self.bot.get_guild(self.guild_id)
                ch = guild.get_channel(self.channel_id)
                return await ch.send(embed=embed)

        except discord.HTTPException as e:   
            raise e

discord_slash.context.SlashContext = TNSlashContext


class BotConfig:
    def __init__(self, config):
        self.log_channel = config


class MyClient(commands.Bot):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._BotBase__cogs = commands.core._CaseInsensitiveDict()

        self.png = "https://cdn.discordapp.com/attachments/932411327727677462/939629297331740702/T-ICON-DISCORD.png?size=2048"
        self.success = 0x00FF00
        self.failure = 0xff0000
        self.warn = 0xffff00

        self.no = "❌"
        self.yes = "✅"

        self.config = BotConfig(const.log_channel_id)

        self.owner_ids = {383287544336613385}

        self.user_cache = {}

        self.eco_config = {}
        self.economydata = {}
        self.eco_user_logs = {}

    async def get_context(self, message, *, cls=TNContext):
        # override get_context
        return await super().get_context(message, cls=cls)

    async def on_connect(self):
        self.session = aiohttp.ClientSession()

    async def check_user(self, msg: discord.Message):

        if str(msg.author.id) not in self.lbs["chatlb"].keys():
            self.lbs["chatlb"][str(msg.author.id)] = {
                "name": msg.author.name,
                "display_name": msg.author.display_name if msg.author.display_name else None,
                "disc": msg.author.discriminator,
                "xp": 0,
                "total_xp": 0,
                "level": 0,
                "url": msg.author.avatar_url_as(static_format="png", size=4096)
            }
            return True

        elif str(msg.author.id) in self.lbs["chatlb"].keys():
            return True
        else:
            return False

    async def addcoins(self, userid:int, amount:int, reason:str=None, where:str="bank"):
        
        e = await self.__check_user(userid)
        
        e[where] += amount

        if self.eco_config.get("income_logs", False):
            channel_id = self.eco_config.get("income_logs_channel_id", 0)
            if channel_id:
                # guild = self.get_guild(const.guild_id)
                # ch = guild.get_channel(channel_id)
                ch = self.get_channel(channel_id)
                embed = discord.Embed(title="💸 Income Log",
                                  description=f"Username: <@!{userid}>\nAmount: {await self.round_int(amount)}\nBefore: {int(e['wallet'] + e['bank'] - amount)}\nNow: {int(e['wallet'] + e['bank'])}\nReason: {reason}",
                                  color=self.failure)

                embed.set_footer(text="TitanMC | Economy", icon_url=self.png)
                await ch.send(embed=embed)

        if not self.eco_user_logs.get(str(userid), False):
            self.eco_user_logs[str(userid)] = {
                "pay_logs": [],
                "income_logs": [{
                    "money_before": e['wallet'] + e['bank'] - amount,
                    "money_after": e['wallet'] + e['bank'],
                    "reason": reason
                }],
                "cash_logs": []
                }
        else:
            self.eco_user_logs[str(userid)]["income_logs"].append(
                {
                    "money_before": e['wallet'] + e['bank'] - amount,
                    "money_after": e['wallet'] + e['bank'],
                    "reason": reason
                }
            )

    async def __check_user(self, authorid):
        if int(self.user.id) == int(authorid):
            return {
                "wallet": 0,
                "bank": 0,
                "inventory": [],
            }
        try:
            return self.economydata[str(authorid)]
        except KeyError:
            self.economydata[str(authorid)] = {
                "wallet": 0,
                "bank": 10000,
                "inventory": [],
            }
            return self.economydata[str(authorid)]

    async def close(self):
        await self.session.close()
        await super().close()

    async def on_ready(self):
        # print(
            # f"\033[1;32m┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n".encode("utf-8"),
            # "\033[1;32mBot is Online".center(78).encode("utf-8"), 
            # "\n\033[1;32m┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛".encode("utf-8"), 
            # sep="")
        self.logger.info(f"Logged in as {self.user}: {self.user.id}")

        await self.change_presence(status=discord.Status.online, activity=discord.Game(name="titanmc.gg"))
    
    @staticmethod
    async def format_duration(ts_duration: str):
        number = ""
        totalamountofseconds = 0
        for i in ts_duration.lower():
            if i == "s" and len(number) != 0:
                totalamountofseconds += float(number)
                number = ""
            elif i == "m" and len(number) != 0:
                totalamountofseconds += float(number) * 60
                number = ""
            elif i == "h" and len(number) != 0:
                totalamountofseconds += float(number) * 3600
                number = ""
            elif i == "d" and len(number) != 0:
                totalamountofseconds += float(number) * 86400
                number = ""
            elif i == "w" and len(number) != 0:
                totalamountofseconds += float(number) * 604800
                number = ""
            elif i in ("mo", "month") and len(number) != 0:
                totalamountofseconds += float(number) * 2678400
                number = ""
            elif i == "y" and len(number) != 0:
                totalamountofseconds += float(number) * 32140800
                number = ""
            else:
                try:
                    int(i)
                    number += i
                except ValueError:
                    if i == ".":
                        number += i

        if not totalamountofseconds and number:
            totalamountofseconds = float(number)

        return round(totalamountofseconds, 2)

    @staticmethod
    async def round_int(my_val):
        def truncate(n, decimals=0):
            multiplier = 10 ** decimals
            return int(n * multiplier) / multiplier
    
        if my_val >= 1000000000000:
            return f"{truncate(my_val / 1000000000000, 1)}T"
        elif my_val >= 1000000000:
            return f"{truncate(my_val / 1000000000, 1)}B"
        elif 1000000 <= my_val <= 1000000000:
            return f"{truncate(my_val / 1000000, 1)}M"
        elif 1000 <= my_val <= 1000000:
            return f"{int(truncate(my_val / 1000, 0))}K"
        else:
            return my_val

    @staticmethod
    async def sec_to_time(seconds:int):
        try:
            seconds = int(seconds)
        except ValueError:
            return f"ValueError: {seconds} is not convertible to INTEGER"

        m, sec = divmod(seconds, 60)
        h, m = divmod(m, 60)

        msg = f"{sec} second"
        msg += "s." if sec != 1 else "."

        msg = f"{m} minutes " + msg if m and m != 1 else f"{m} minute " + msg if m else msg

        msg = f"{h} hours " + msg if h and h != 1 else f"{h} hour " + msg if h else msg

        return msg

    @staticmethod
    async def parse_int(string_amount:str):
        
        clean_content = string_amount.replace(" ", "").replace(",", "").lower()

        if clean_content.endswith("k"):
            rv = float(clean_content.replace("k", "")) * 1e3

        elif clean_content.endswith("m"):
            rv = float(clean_content.replace("m", "")) * 1e6

        elif clean_content.endswith("b"):
            rv = float(clean_content.replace("b", "")) * 1e9

        elif clean_content.endswith("t"):
            rv = float(clean_content.replace("t", "")) * 1e12

        else:
            rv = float(clean_content)

        return rv


client = MyClient(command_prefix=commands.when_mentioned_or(const.prefix), case_insensitive=True,
                  allowed_mentions=discord.AllowedMentions(everyone=False, roles=False), intents=discord.Intents.all())


with open("data/level_system/config.json", "r") as f:
    client.lvlsys_config = json.load(f)

with open("data/leaderboards.json", "r") as f:
    client.lbs = json.load(f)

    client.lbs["chatlb"] = {} if "chatlb" not in client.lbs.keys() else client.lbs["chatlb"]
    
    client.lbs["mm_tournament"] = {} if "mm_tournament" not in client.lbs.keys() else client.lbs["mm_tournament"]

    client.lbs["mm_casual"] = {} if "mm_casual" not in client.lbs.keys() else client.lbs["mm_casual"]

    client.lbs["riddles"] = {} if "riddles" not in client.lbs.keys() else client.lbs["riddles"]

    client.lbs["msgs"] = {} if "msgs" not in client.lbs.keys() else client.lbs["msgs"]

with open("data/games/payouts.json", "r") as f:
    client.payouts = json.load(f)

    client.payouts["mm"] = {"ts": 0, "month": 1} if "mm" not in client.payouts.keys() else client.payouts["mm"]

    client.payouts["msgs"] = {"ts": 1643605260, "month": 1} if "msgs" not in client.payouts.keys() else client.payouts["msgs"]

with open("data/economy/config.json", "r") as f:
    client.eco_config = json.load(f)

    if "cash_logs" not in client.eco_config.keys():
        client.eco_config["cash_logs"] = False

    if "cash_logs_channel_id" not in client.eco_config.keys():
        client.eco_config["cash_logs_channel_id"] = None

    if "income_logs" not in client.eco_config.keys():
        client.eco_config["income_logs"] = False

    if "income_logs_channel_id" not in client.eco_config.keys():
        client.eco_config["income_logs_channel_id"] = None
    
    if "pay_logs" not in client.eco_config.keys():
        client.eco_config["pay_logs"] = False

    if "pay_logs_channel_id" not in client.eco_config.keys():
        client.eco_config["pay_logs_channel_id"] = None

    if "gems_logs" not in client.eco_config.keys():
        client.eco_config["gems_logs"] = False
    
    if "gems_logs_channel_id" not in client.eco_config.keys():
        client.eco_config["gems_logs_channel_id"] = None


with open("data/verified_players.json", "r") as f:
    client.players = json.load(f)

with open("data/wab.json", "r") as f:
    client.wab_data = json.load(f)
        
    if not "fee" in client.wab_data.keys():
        client.wab_data["fee"] = 150_000

    client.play_price = client.wab_data["fee"]


client.load_extension('utils.logger')
client.logger = client.get_cog('Logger')

client.logger.setLevel('info')
client.logger.debug("")
client.logger.debug("===== (REBOOT) =====")
client.logger.debug("")
client.logger.info("Client class has been initialized.")


slash = SlashCommand(client, sync_commands=True, sync_on_cog_reload=True)


client.logger.info("Loading Extensions...")

for ext in const.command_exts:
    client.load_extension(ext)

for dir_name in ["events"]:
    for file in os.listdir(dir_name):
        if file.endswith(".py"):
            client.load_extension(f"{dir_name}.{file}".replace('.py', ''))

skipped = 0
for dir_name in ["utils"]:
    for file in os.listdir(dir_name):
        if file.endswith(".py"):
            try:
                client.load_extension(f"{dir_name}.{file}".replace('.py', ''))
            except (commands.NoEntryPointError, commands.ExtensionAlreadyLoaded) as e:
                client.logger.debug(f"Extension {dir_name}.{file.replace('.py', '')} not loaded: {e}")
                skipped += 1

client.logger.info(len(client.extensions), "extensions loaded,", skipped, "skipped.")


@slash.slash(name="reload", guild_ids=const.slash_guild_ids, description="[DEVELOPER] Reload a client extension.", options=[
    create_option(name="filename", description="The name of the extension file to reload.", option_type=str,
    required=True, choices=[create_choice(value=x, name=x) for x in const.command_exts])])
@commands.is_owner()
async def reload(ctx, filename):
    try:
        client.unload_extension(filename)
        client.load_extension(filename)
        return await ctx.send(f"Reloaded `{filename}.py`.", hidden=True)
    except Exception as e:
        if len(str(e)) > 1800:
            with open("error.txt", "w") as f:
                f.write(str(e))
            return await ctx.send(content="An error occured.", file=discord.File(fp="error.txt", filename="error.txt"))
        await ctx.send(f"```yaml\n{e}\n```")


@slash.slash(name="load", guild_ids=const.slash_guild_ids, description="[DEVELOPER] Load a client extension.", options=[
    create_option(name="filename", description="The name of the extension file to load.", option_type=str,
    required=True, choices=[create_choice(value=x, name=x) for x in const.command_exts])])
@commands.is_owner()
async def load(ctx, filename):
    try:
        client.load_extension(filename)
        return await ctx.send(f"Loaded `{filename}.py`.", hidden=True)
    except Exception as e:
        if len(str(e)) > 1800:
            with open("error.txt", "w") as f:
                f.write(str(e))
            return await ctx.send(content="An error occured.", file=discord.File(fp="error.txt", filename="error.txt"))
        await ctx.send(f"```yaml\n{e}\n```")


@slash.slash(name="unload", guild_ids=const.slash_guild_ids, description="[DEVELOPER] Unload a client extension.", options=[
    create_option(name="filename", description="The name of the extension file to unload.", option_type=str,
    required=True, choices=[create_choice(value=x, name=x) for x in const.command_exts])])
@commands.is_owner()
async def unload(ctx, filename):
    if ctx.author.id not in client.owner_ids:
        return await ctx.send("You're not allowed to run this command.")

    try:
        client.unload_extension(filename)
        return await ctx.send(f"Unloaded `{filename}.py`.", hidden=True)
    except Exception as e:
        if len(str(e)) > 1800:
            with open("error.txt", "w") as f:
                f.write(str(e))
            return await ctx.send(content="An error occured.", file=discord.File(fp="error.txt", filename="error.txt"))
        await ctx.send(f"```yaml\n{e}\n```")


client.logger.info("Logging in...")
loop = asyncio.get_event_loop()
loop.set_debug(const.DEBUG)
loop.create_task(client.run(TOKEN))
loop.run_forever()
