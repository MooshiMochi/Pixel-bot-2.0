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


from constants import const

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


class PixelContext(commands.Context):
    async def embed(self, embed, *, footer=None):

        if footer is None:
            footer = "Pixel Housing"
        embed.set_footer(icon_url=self.bot.png, text=f"Pixel | {footer}")
        embed.timestamp = datetime.utcnow()

        try:
            return await self.send(embed=embed)
        except discord.HTTPException as e:   
            raise e


class PixelSlashContext(SlashContext):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def embed(self, embed, *, footer=None):

        if footer is None:
            footer = "Pixel Housing"
        embed.set_footer(icon_url=self.bot.png, text=f"Pixel | {footer}")
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

discord_slash.context.SlashContext = PixelSlashContext


class BotConfig:
    def __init__(self, config):
        self.log_channel = config


class MyClient(commands.Bot):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._BotBase__cogs = commands.core._CaseInsensitiveDict()

        self.png = "https://cdn.discordapp.com/attachments/932411327727677462/939247777785983066/HD-T-ICON.png?size=2048"
        self.success = 0x00FF00
        self.failure = 0xff0000
        self.warn = 0xffff00

        self.no = "❌"
        self.yes = "✅"

        self.config = BotConfig(const.log_channel_id)

        self.owner_ids = {383287544336613385}

        self.user_cache = {}

    async def get_context(self, message, *, cls=PixelContext):
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
                "level": 0
            }
            return True

        elif str(msg.author.id) in self.lbs["chatlb"].keys():
            return True
        else:
            return False

    async def addcoins(self, userid, amount):
        if amount < 0:
            async with client.session.get(f"https://unbelievaboat.com/api/v1/guilds/{const.guild_id}/users/{userid}", headers={"Authorization": const.unbelievaboattoken}) as r:
                if r.status == 200:
                    r = await r.json()
                    if r["bank"] < (amount/-1):
                        return "You are too poor to afford a private chat."
                else:
                    print(r.status, await r.json())
                    return
                    
        headers = {"Authorization": const.unbelievaboattoken,
                   'Accept': 'application/json'}
        async with client.session.patch(f"https://unbelievaboat.com/api/v1/guilds/{const.guild_id}/users/{userid}",
                                        headers=headers,
                                        json={"bank": amount, "reason": "Guessed the riddle correct."}) as f:
            data = await f.json()
            return data

    async def close(self):
        await self.session.close()
        await super().close()

    async def on_ready(self):
        print(f"\033[1;32m┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n" + "\033[1;32mBot is Online".center(78) + "\n\033[1;32m┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛")
        self.logger.info(f"Logged in as {self.user}: {self.user.id}")
    
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

with open("data/games/payouts.json", "r") as f:
    client.payouts = json.load(f)

    client.payouts["mm"] = {"ts": 0, "month": 1} if "mm" not in client.payouts.keys() else client.payouts["mm"]


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


@slash.slash(name="reload", guild_ids = [932736074139185292],description="[DEVELOPER] Reload a client extension.", options=[
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


@slash.slash(name="load", guild_ids = [932736074139185292], description="[DEVELOPER] Load a client extension.", options=[
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


@slash.slash(name="unload", guild_ids = [932736074139185292], description="[DEVELOPER] Unload a client extension.", options=[
    create_option(name="filename", description="The name of the extension file to unload.", option_type=str,
    required=True, choices=[create_choice(value=x, name=x) for x in const.command_exts])])
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
loop.set_debug(True)
loop.create_task(client.run(const.token))
loop.run_forever()