import json
import discord

from discord.ext import commands, tasks

from datetime import datetime

from constants import const

class PayoutTasks(commands.Cog):
    def __init__(self, client):
        self.client = client

        self.mm_monthly_payout.start()
        self.clear_user_cache.start()
    
    @tasks.loop(hours=24)
    async def clear_user_cache(self):
        self.client.user_cache = {}


    @tasks.loop(minutes=1)
    async def mm_monthly_payout(self):

        scheduled_pay_time = datetime.strptime("2022-03-01 05:01:00", "%Y-%m-%d %H:%M:%S").timestamp()

        if "ts" in self.client.payouts["mm"].keys() and self.client.payouts["mm"]["ts"]:
            scheduled_pay_time = self.client.payouts["mm"]["ts"]

        if datetime.utcnow().timestamp() >= scheduled_pay_time:

            _date = str(datetime.utcnow().date())
            next_schedule = ""    
            if int(_date[5:7]) > 12:
                next_schedule = datetime.strptime(
                    str(int(str(datetime.utcnow().date())[:4])+1) + "-01-01 05:01:00", "%Y-%m-%d %H:%M:%S").timestamp()
            else:
                if int(str(datetime.utcnow().date())[5:7])+1 < 10:
                    filler = "0"
                else:
                    filler = ""
        
                next_schedule = datetime.strptime(str(datetime.utcnow().date())[:5] + filler + str(int(str(datetime.utcnow().date())[5:7])+1) + "-01 05:01:00", "%Y-%m-%d %H:%M:%S").timestamp()
            
            # payout code here
            data = sorted([[key, self.client.lbs["mm_tournament"][key]] for key in self.client.lbs["mm_tournament"].keys()], key=lambda e: e[1], reverse=True)[:10]
    
            payouts = [500000, 400000, 300000, 200000, 100000, 80000, 60000, 40000, 20000, 10000]
            
            guild = self.client.get_guild(const.guild_id)

            ch = guild.get_channel(const.giveaway_ch_id)

            for index in range(10):
                
                if self.unbelievaboat_api_enabled:
                    await self.client.addcoins(int(data[index][0]), payouts[0])
                
                mem = await self.get_user(int(data[index][0]))

                em = discord.Embed(colro=0x78BB67, description=f"<:Checkmark:886699674277396490> Added <:money:903467440829259796>**{payouts[0]:,}** to {mem}'s bank balance.")
                em.set_author(name="Top 10 Monthly Minecraft Maddness Winner Payout", icon_url=self.client.user.avatar_url_as(static_format="png", size=2048))
                
                await ch.send(embed=em)

                print(f"Added {payouts[0]} coins to {mem} - {data[index][0]} | {self.client.lbs['mm_tournament'][data[index][0]]}")
                payouts.pop(0)


            if not "month" in self.client.payouts["mm"].keys():
                self.client.payouts["mm"]["month"] = 2
            else:
                self.client.payouts["mm"]["month"] += 1
            
            self.client.lbs["mm_tournament"] = {}

            self.client.payouts["mm"]["ts"] = next_schedule
        
            with open("data/payouts.json", "w") as f:
                json.dump(self.client.po_data, f, indent=2)

    @mm_monthly_payout.before_loop
    async def before_mm_monthly_payout(self):
        await self.client.wait_until_ready()

def setup(client):
    client.add_cog(PayoutTasks(client))