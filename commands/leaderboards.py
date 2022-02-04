import json
import discord

from discord.ext import commands, tasks

from discord_slash.cog_ext import cog_slash
from discord_slash import SlashContext

from utils.paginator import Paginator as paginator

from constants import const


class LeaderboardCommands(commands.Cog):
    def __init__(self, client) -> None:
        self.client = client

        self.update_leaderboards.start()


    @tasks.loop(minutes=1.0)
    async def update_leaderboards(self):

        with open("data/level_system/chatlb.json", "w") as f:
            json.dump(self.client.chatlb, f, indent=2)
    
    @update_leaderboards.before_loop
    async def before_update_leaderboards(self):
        await self.client.wait_until_ready()


    @cog_slash(name="leaderboard", description="Display the messages leaderboard", guild_ids=const.slash_guild_ids)
    async def leaderboard(self, ctx:SlashContext):
        
        await ctx.defer(hidden=False)

        if not self.client.chatlb:
            return await ctx.send("I have no leaderboard data yet. Please wait for someone to start talking.")

        ranked = sorted(self.client.chatlb, key=lambda f: self.client.chatlb[f]["total_xp"], reverse=True)

        embeds = []

        add_on = [y for y in range(9, len(self.client.chatlb), 10)] if len(self.client.chatlb) >= 10 else [len(self.client.chatlb)-1]

        if len(add_on) > 1 and add_on[-1] % 10 != 0:
            add_on.append(len(self.client.chatlb)-1)
        
        em = discord.Embed(color=self.client.failure, title="Messages Leadernoard Rakings", description="")
        
        MyID = str(ctx.author_id)

        for x in range(len(self.client.chatlb)):
            
            name = self.client.chatlb[ranked[x]]["name"]
            level = self.client.chatlb[ranked[x]]["level"]
            
            if x == 0:
                if ranked[x] == MyID:
                    em.description += f"**🏆. `(Me)` {name}** - Lvl {level}\n"
                else:
                    em.description += f"**🏆. {name}** - Lvl {level}\n"
            elif x == 1:
                if ranked[x] == MyID:
                    em.description += f"**🥈. `(Me)` {name}** - lvl {level}\n"
                else:
                    em.description += f"**🥈. {name}** - lvl {level}\n"
            elif x == 2:
                if ranked[x] == MyID:
                    em.description += f"**🥉. `(Me)` {name}** - lvl {level}\n"
                else:
                    em.description += f"**🥉. {name}** - lvl {level}\n"
            else:
                if ranked[x] == MyID:
                    em.description += f"**{x+1}. `(Me)` {name}** - lvl {level}\n"
                else:
                    em.description += f"**{x+1}. {name}** - lvl {level}\n"

            if x in add_on:
                em.set_footer(text=f"Pixel | Leveling Systep | Page {add_on.index(x)+1}/{len(add_on)}",
                icon_url=self.client.png)
                embeds.append(em)

                em = discord.Embed(color=self.client.failure, title="Messages Leadernoard Rakings", description="")

        await paginator(embeds, ctx).run()

def setup(client):
    client.add_cog(LeaderboardCommands(client))