
import json
import discord

from random import sample
from random import choice, randint

from discord.ext import commands
from discord.ext import tasks


from constants import const


class Riddles(commands.Cog):
    def __init__(self, client):
        self.client = client

        with open("data/games/riddles_config.json", "r") as f:
            self.config = json.load(f)

        with open("data/games/riddles.json", "r") as f:
            self.riddles = json.load(f)

        self.main_ch = self.config.get("channel_id", None)
        self.active = self.config.get("active", False)
        
        self.riddle_nonce = "aerhagj33££!34$$bea13513te131UKW!²╪Ur134hthh[}{ajwhd[]9a}_--=-#~jkwnanjavOKEadk:!@!"

        self.used_riddles = {}
        self.used_categories = []
        self.current_riddle = {"question": self.riddle_nonce, "answer": self.riddle_nonce}
        self.random_win = 500
        self.is_riddle_guessed = False

        self.get_ready.start()
        self.run_riddles.start()

    
    async def scramblestring(self, string: str):
        result = []
        for word in string.split(" "):
            result.append("".join(sample(word, len(word))))

        return " ".join(result)
    
    
    @tasks.loop(count=1)
    async def get_ready(self):
        guild = self.client.get_guild(const.guild_id)
        self.main_ch = guild.get_channel(self.main_ch)

    
    @tasks.loop(minutes=5.0)
    async def run_riddles(self):

        if not self.active: return

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

        em = discord.Embed(color=self.client.failure, title="New chat riddle", description=msg+f"\n\n*Answer the riddle correctly for {self.random_win} <:money:903467440829259796>!*")
        em.set_footer(text="TN | Riddles", icon_url=self.client.png)

        self.is_riddle_guessed = False

        await self.main_ch.send(embed=em)


    @run_riddles.before_loop
    async def before_run_riddles(self):
        await self.client.wait_until_ready()

    @get_ready.before_loop
    async def before_get_ready(self):
        await self.client.wait_until_ready()


    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author.bot:
            return
        
        elif self.is_riddle_guessed:
            return

        elif self.active:
            if msg.content.lower() == self.current_riddle["answer"].lower():
                self.is_riddle_guessed = True

                if str(msg.author.id) not in self.client.lbs["riddles"].keys():
                    self.client.lbs["riddles"][str(msg.author.id)] = 1
                else:
                    self.client.lbs["riddles"][str(msg.author.id)] += 1

                await self.client.addcoins(msg.author.id, self.random_win)

                em = discord.Embed(
                    description=f"Congratulations {msg.author.mention}!         You guessed the riddle! You got `{self.random_win}` cash",
                    color=self.client.failure)
                em.set_footer(text="TN | Riddles",
                              icon_url=str(self.client.user.avatar_url_as(static_format="png", size=2048)))

                await msg.channel.send(embed=em)


def setup(client):
    client.add_cog(Riddles(client))
    