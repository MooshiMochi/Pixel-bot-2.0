
import json
import discord
import asyncio

from random import sample
from random import choice, randint

from discord.ext import commands
from discord.ext import tasks

from discord_slash import SlashContext
from discord_slash.cog_ext import cog_slash
from discord_slash.utils.manage_commands import create_option, create_choice

from utils.paginator import Paginator

from constants import const


class Riddles(commands.Cog):
    def __init__(self, client):
        self.client = client

        self.last_user_msgs_count = 0

        with open("data/games/riddles_config.json", "r") as f:
            self.config = json.load(f)

            if "channel_id" not in self.config.keys():
                self.config["channel_id"] = None

            if "active" not in self.config.keys():
                self.config["active"] = False

        with open("data/games/riddles.json", "r") as f:
            self.riddles = json.load(f)

        self.main_ch = self.config.get("channel_id", None)
        
        self.riddle_nonce = "aerhagj33££!34$$bea13513te131UKW!²╪Ur134hthh[}{ajwhd[]9a}_--=-#~jkwnanjavOKEadk:!@!"

        self.used_riddles = {}
        self.used_categories = []
        self.current_riddle = {"question": self.riddle_nonce, "answer": self.riddle_nonce}
        self.random_win = 500
        self.is_riddle_guessed = False

        self.get_ready.start()

        if self.config['active']:
            self.run_riddles.start()

    
    async def scramblestring(self, string: str):
        result = []
        for word in string.split(" "):
            result.append("".join(sample(word, len(word))))

        return " ".join(result)
    
    
    @tasks.loop(count=1)
    async def get_ready(self):
        guild = self.client.get_guild(const.guild_id)
        try:
            self.main_ch = guild.get_channel(self.main_ch)
            if not self.main_ch:
                self.config["active"] = False
        except (TypeError, AttributeError):
            self.client.logger.error("Unloading 'commands.games.riddles'. Failed to get guild object.\nRiddles will not work.")
            self.client.remove_cog("commands.games.riddles")


    @tasks.loop(minutes=5.0)
    async def run_riddles(self):
        await asyncio.sleep(5)

        if not self.config['active']: return

        if self.last_user_msgs_count < 4:
            return

        cat_opts = [key for key in self.riddles.keys() if key not in self.used_categories]

        if not cat_opts:
            cat_opts = [key for key in self.riddles.keys() if key != self.used_categories[-1]]
            self.used_categories = []

        cat = choice(list(self.riddles.keys()))
        self.used_categories.append(cat)

        if cat not in self.used_riddles.keys(): 
            self.used_riddles[cat] = {}
        
        riddle_opts = [key for key in self.riddles[cat].keys() if key not in self.used_riddles[cat].keys()]
        
        if not riddle_opts:
            riddle_opts = [key for key in self.riddles[cat].keys() if key != list(self.used_riddles[cat].keys())[-1]]
            self.used_riddles[cat] = {}

        riddle_num = choice(riddle_opts)

        self.used_riddles[cat][riddle_num] = self.riddles[cat][riddle_num]
        self.current_riddle = self.riddles[cat][riddle_num]
        
        if cat == "unscramble":
            self.current_riddle["question"] = await self.scramblestring(self.current_riddle["answer"])
            msg = f"Unscramble: {self.current_riddle['question']}"
        else:
            msg = self.current_riddle["question"]

        self.random_win = randint(500, 2500)

        em = discord.Embed(color=self.client.failure, title="New chat riddle", description=msg+f"\n\n*Answer the riddle correctly for {self.random_win} 💸!*")
        em.set_footer(text="TitanMC | Riddles", icon_url=self.client.png)

        self.is_riddle_guessed = False

        try:
            await self.main_ch.send(embed=em)
            self.last_user_msgs_count = 0
        except (discord.HTTPException, discord.Forbidden):
            pass

    @run_riddles.before_loop
    @get_ready.before_loop
    async def before_run_riddles(self):
        await self.client.wait_until_ready()

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):

        if msg.author.bot:
            return
        else:
            if not isinstance(self.main_ch, int):
                if msg.channel.id == self.main_ch.id:
                    self.last_user_msgs_count += 1

        if self.is_riddle_guessed:
            return
        
        elif self.config["active"]:
            if msg.content.lower() == self.current_riddle["answer"].lower():
                self.is_riddle_guessed = True

                if str(msg.author.id) not in self.client.lbs["riddles"].keys():
                    self.client.lbs["riddles"][str(msg.author.id)] = 1
                else:
                    self.client.lbs["riddles"][str(msg.author.id)] += 1

                await self.client.addcoins(msg.author.id, self.random_win, reason="Guessed riddle correctly!")

                em = discord.Embed(
                    description=f"Congratulations {msg.author.mention}!         You guessed the riddle! You got `{self.random_win}` 💸",
                    color=self.client.failure)
                em.set_footer(text="TitanMC | Riddles",
                              icon_url=str(self.client.user.avatar_url_as(static_format="png", size=2048)))

                await msg.channel.send(embed=em)


    @cog_slash(name="riddles_config", description="[ADMIN] Configure riddles", guild_ids=const.slash_guild_ids, options=[
        create_option(name="active", description="Activate or deactivate riddles", option_type=5, required=False),
        create_option(name="riddles_channel", description="Channel where riddles will be sent", option_type=7, required=False),
    ])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def riddles_config(self, ctx:SlashContext, active:bool=None, riddles_channel:discord.TextChannel=None):
        
        await ctx.defer(hidden=True)

        text = "Config settings:\n"

        if active is not None:
            if active == self.config["active"]:
                text += f"> Activated: Already set to `{active}`\n"
            else:
                self.config["active"] = active
                text += f"> Activated: Set to `{active}`\n"
        else:
            text += f"> Activated: `{active}` (unchanged)\n"

        if riddles_channel:
            if riddles_channel.id != self.config["channel_id"]:
                if isinstance(riddles_channel, discord.VoiceChannel):
                    return await ctx.send("Riddles channel must be a Text Channel, not a Voice Channel!", hidden=True)

                self.config["channel_id"] = riddles_channel.id
                self.main_ch = riddles_channel
                text += f"> Channel: Set to <#{riddles_channel.id}>\n"
            else:
                text += f"> Channel: Already set to <#{self.config['channel_id']}>\n"
        
        else:
            if not self.config['channel_id'] and self.config['active']:
                return await ctx.send("'Riddles channel' parameter MUST be specified if 'active' parameter is set to TRUE", hidden=True)
            text += f"> Channel: <#{self.config['channel_id']}> (unchanged)"

        with open("data/games/riddles_config.json", "w") as f:
            json.dump(self.config, f, indent=2)

        if self.config['active']:
            try:
                if self.run_riddles.is_running():
                    self.run_riddles.cancel()
                self.run_riddles.start()
            except RuntimeError:
                if self.run_riddles.is_running():
                    self.run_riddles.cancel()
                self.run_riddles.start()

        else:
            if self.run_riddles.is_running():
                self.run_riddles.cancel()

        return await ctx.send(text, hidden=True)


    @cog_slash(name="riddles_add", description="[ADMIN] Add a riddle", guild_ids=const.slash_guild_ids, options=[
        create_option(name="type", description="Type of riddle", option_type=3, required=True, choices=[
            create_choice(value="question", name="Question"),
            create_choice(value="trivia", name="Trivia"),
            create_choice(value="riddle", name="Riddle"),
            create_choice(value="unscramble", name="Unscramble")
        ]),
        create_option(name="question", description="The question the users have to answer", option_type=3, required=True),
        create_option(name="answer", description="The answer to the question", option_type=3, required=True)
    ])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def riddles_add(self, ctx:SlashContext, type:str=None, question:str=None, answer:str=None):
        
        await ctx.defer(hidden=True)

        self.riddles[type][str(len(self.riddles[type])+1)] = {
            "question": question,
            "answer": answer
        }

        em = discord.Embed(color=self.client.failure, title="New riddle added", 
        description=f"**Type: __{type.capitalize()}__**\n\n`#{len(self.riddles[type])}. {question}`\n> {answer}")
        
        with open("data/games/riddles.json", "w") as f:
            json.dump(self.riddles, f, indent=2)

        return await ctx.embed(embed=em, footer="Riddles")


    @cog_slash(name="riddles_delete", description="[ADMIN] Delete a riddle", guild_ids=const.slash_guild_ids, options=[
        create_option(name="type", description="Type of riddle", option_type=3, required=True, choices=[
            create_choice(value="question", name="Question"),
            create_choice(value="trivia", name="Trivia"),
            create_choice(value="riddle", name="Riddle"),
            create_choice(value="unscramble", name="Unscramble")
        ]),
        create_option(name="riddle_number", description="The number of the riddle (use /riddles_questions)", option_type=4, required=True)
    ])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def riddles_delete(self, ctx:SlashContext, type:str=None, riddle_number:int=None):
        
        await ctx.defer(hidden=True)

        if not str(riddle_number) in self.riddles[type].keys():
            return await ctx.send(f"That riddle doesn't exist in the {type.capitalize()} category.", hidden=True)

        question = self.riddles[type][str(riddle_number)]["question"]
        answer = self.riddles[type][str(riddle_number)]["answer"]
        
        if not self.riddles[type].pop(str(riddle_number), False):
            return await ctx.send(f"That riddle doesn't exist in the {type.capitalize()} category.", hidden=True)

        copied_dict = self.riddles[type].copy()
        self.riddles[type] = {}

        for index, qna in enumerate(copied_dict.values()):
            self.riddles[type][str(index+1)] = qna

        em = discord.Embed(color=self.client.failure, title="Riddle deleted", 
        description=f"**Type: __{type.capitalize()}__**\n\n`#{riddle_number}. {question}`\n> {answer}")
        
        with open("data/games/riddles.json", "w") as f:
            json.dump(self.riddles, f, indent=2)

        return await ctx.embed(embed=em, footer="Riddles")


    @cog_slash(name="riddles_questions", description="[ADMIN] Display all Riddles questions and answers", guild_ids=const.slash_guild_ids, options=[
        create_option(name="type", description="Type of riddles", option_type=3, required=True, choices=[
            create_choice(value="question", name="Question"),
            create_choice(value="trivia", name="Trivia"),
            create_choice(value="riddle", name="Riddle"),
            create_choice(value="unscramble", name="Unscramble")
        ]) | {"focused": True}])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def riddles_questions(self, ctx:SlashContext, type:str=None):
        await ctx.defer(hidden=True)
        
        ranked = list(self.riddles[type].keys())

        embeds = []

        add_on = [y for y in range(9, len(self.riddles[type]), 10)] if len(self.riddles[type]) >= 10 else [len(self.riddles[type])-1]

        if len(add_on) > 1 and add_on[-1] % 10 != 0:
            add_on.append(len(self.riddles[type])-1)
        
        em = discord.Embed(color=self.client.failure, title=f"Riddles Q & A's ({type.capitalize()})", description="")
        
        for x in range(len(self.riddles[type])):
            
            question = self.riddles[type][ranked[x]]["question"]
            answer = self.riddles[type][ranked[x]]["answer"]
            
            em.description += f"`#{ranked[x]}. {question}`\n"
            em.description += f"> {answer}\n\n"

            if x in add_on:
                em.set_footer(text=f"TitanMC | Riddles | Page {add_on.index(x)+1}/{len(add_on)-1}",
                icon_url=self.client.png)
                embeds.append(em)

                em = discord.Embed(color=self.client.failure, title=f"Riddles Q & A's ({type.capitalize()})", description="")

        for index, embed in enumerate(embeds):
            embed: discord.Embed
            embed.set_footer(text=f"TitanMC | Riddles | Page {index+1}/{len(embeds)}", icon_url=self.client.png)

        return await Paginator(embeds, ctx).run()
        

def setup(client):
    client.add_cog(Riddles(client))
    