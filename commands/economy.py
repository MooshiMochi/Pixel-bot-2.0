import json
import time
import discord

from datetime import datetime

from discord import NotFound
from discord.ext import commands, tasks

from discord_slash import SlashContext, ComponentContext
from discord_slash.model import ButtonStyle
from discord_slash.cog_ext import cog_slash
from discord_slash.utils.manage_commands import create_choice, create_option
from discord_slash.utils.manage_components import create_button, create_actionrow, wait_for_component

from asyncio import TimeoutError

from constants import const


class EconomyCommands(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.isready = False

        self.guild = const.guild_id

        with open("data/economy/config.json", "r") as f:
            self.config = json.load(f)

            if "money_changes" not in self.config.keys():
                self.config["money_changes"] = False

            if "log_channel_id" not in self.config.keys():
                self.config["log_channel_id"] = None

            if "inventory_usage" not in self.config.keys():
                self.config["inventory_usage"] = False

            if "inv_usage_channel_id" not in self.config.keys():
                self.config["inv_usage_channel_id"] = None
        
        self.log_channel = self.config.get("log_channel_id", 0)

        with open("data/economy/shopitems.json", "r") as f:
            self.shopdata = json.load(f)

        with open("data/economy/economydata.json", "r") as f:
            self.client.economydata = json.load(f)

        self.on_ready_replacement.start()


    @tasks.loop(count=1)
    async def on_ready_replacement(self):
        
        self.guild = self.client.get_guild(self.guild)
        self.log_channel = self.guild.get_channel(self.log_channel)
        self.update_loop.start()
        self.isready = True

    @tasks.loop(minutes=1)
    async def update_loop(self):

        with open("data/economy/economydata.json", "w") as f:
            economydatalocal = self.client.economydata.copy()
            json.dump(economydatalocal, f, indent=2)

        for item, itemdata in self.shopdata.copy().items():
            try:
                if itemdata["in_store_time"] is not None:
                    if time.time() >= itemdata["in_store_time"]:
                        del self.shopdata[item]
            except KeyError:
                pass
        with open("data/economy/shopitems.json", "w") as f:
            json.dump(self.shopdata, f, indent=2)


    async def check_user(self, authorid):
        if int(self.client.user.id) == int(authorid):
            return {
                "wallet": 0,
                "bank": 0,
                "inventory": [],
            }
        
        try:
            return self.client.economydata[str(authorid)]
        except KeyError:
            self.client.economydata[str(authorid)] = {
                "wallet": 0,
                "bank": 10000,
                "inventory": [],
            }
            return self.client.economydata[str(authorid)]

    async def log_money(self, member, amount: int, reason: str):
        if self.config["money_changes"]:
            channel = self.log_channel
            id1 = str(member).replace("<@", "").replace("!", "").replace(">", "")
            try:
                await self.check_user(id1)
            except ValueError:  # This is for @everyone.
                return
            e = self.client.economydata[str(id1)]

            embed = discord.Embed(title="Gems change",
                                  description=f"Username: {member}\nAmount: {await self.client.round_int(amount)}\nBefore: {int(e['wallet'] + e['bank'] - amount)}\nNow: {int(e['wallet'] + e['bank'])}\nReason: {reason}",
                                  color=self.client.failure)

            embed.set_footer(text="TN | Economy", icon_url=self.client.png)
            await channel.send(embed=embed)

    async def add_coins(self, ctx, user:discord.Member, amount:int, where:str="wallet", all:bool=False):
            data = await self.check_user(user.id)

            data[where] += amount

            if not all:
                await self.log_money(user.mention, amount, f"{ctx.author.mention} used /add_gems")
            return None


    @cog_slash(name="economy_config", description="Configure Economy System", guild_ids=const.slash_guild_ids,
    options=[
        create_option(name="money_changes", description="Log money changes", option_type=5, required=True),
        create_option(name="inventory_usage", description="Log inventory usage", option_type=5, required=True),
        create_option(name="money_logs_channel", description="The channel where to send the 'money changes' logs", option_type=7, required=False),
        create_option(name="inv_logs_channel", description="The channel where to send the 'inventory usage' logs", option_type=7, required=False)
    ])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def economy_config(self, ctx:SlashContext, money_changes:bool=False, inventory_usage:bool=False, money_logs_channel:discord.TextChannel=None, inv_logs_channel:discord.TextChannel=None):
        await ctx.defer(hidden=True)

        em = discord.Embed(color=self.client.failure, title="Economy Config Finished", description="")
        if money_changes:
            if not money_logs_channel:
                return await ctx.send("Param `money_logs_channel` must be specified if `money_changes` param is set to **`True`**", hidden=True)
            elif not isinstance(money_logs_channel, discord.TextChannel):
                return await ctx.send("Channel for `money_logs_channel` MUST be a TEXT CHANNEL", hidden=True)
            
            self.config["money_changes"] = money_changes
            self.config["log_channel_id"] = money_logs_channel.id

            em.description += f"**Money Changes Logs:**\n> Activated: `True`\n> Channel: <#{money_logs_channel.id}>\n\n"
        else:
            em.description += f"**Money Changes Logs:**\n> Activated `{self.config['money_changes']}` (unchanged)\n> Channel: <#{self.config['log_channel_id']}>\n\n"

        if inventory_usage:
            if not inv_logs_channel:
                return await ctx.send("Param `inv_logs_channel` must be specified if `inventory_usage` param is set to **`True`**", hidden=True)
            elif not isinstance(inv_logs_channel, discord.TextChannel):
                return await ctx.send("Channel for `inv_logs_channel` MUST be a TEXT CHANNEL", hidden=True)
            
            self.config["inventory_usage"] = inventory_usage
            self.config["inv_usage_channel_id"] = inv_logs_channel.id

            em.description += f"**Inventory Usage Logs:**\n> Activated: `True`\n> Channel: <#{inv_logs_channel.id}>\n\n"
        else:
            em.description += f"**Inventory Usage Logs:**\n> Activated `{self.config['inventory_usage']}` (unchanged)\n> Channel: <#{self.config['inv_usage_channel_id']}>\n\n"

        with open("data/economy/config.json", "w") as f:
            json.dump(self.config, f, indent=2)

        return await ctx.embed(embed=em, footer="Economy")
        

    @cog_slash(name="balance", description="Check your or a member's bank and wallet balance", guild_ids=const.slash_guild_ids, options=[
        create_option(name="member", description="The server memebr to check the balance for", option_type=6, required=False)])
    @commands.guild_only()
    async def balance(self, ctx, member:discord.Member=None):
        await ctx.defer(hidden=True)

        if member is None:
            member = ctx.author
        
        data = await self.check_user(member.id)

        embed = discord.Embed(title=f"{member.name}'s Balance \💰", color=self.client.failure)

        embed.add_field(name="👛 **Wallet:**",
                        value=f"{await self.client.round_int(int(data['wallet']))}💎",
                        inline=True)

        embed.add_field(name="🏦 **Bank:**",
                        value=f"{await self.client.round_int(int(data['bank']))}💎",
                        inline=True)

        embed.set_footer(text="TN | Economy",
                         icon_url=self.client.png)
        await ctx.send(embed=embed)


    @cog_slash(name="add_gems", description="Add x amount of 💎 to a user", guild_ids=const.slash_guild_ids, options=[
        create_option(name="amount", description="Amount of 💎 to add", option_type=4, required=True),
        create_option(name="member", description="The member to add the 💎 to", option_type=6, required=False),
        create_option(name="where", description="Where to add the 💎", option_type=3, required=False, choices=[
            create_choice(value="wallet", name="Wallet"),
            create_choice(value="bank", name="Bank")
        ]),
        create_option(name="add_to_everyone", description="Whether to add x amount of 💎 to every member", option_type=5, required=False)
    ])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def add_gems(self, ctx, member:discord.Member=None, amount:int=None, where:str="wallet", add_to_everyone:bool=False):
        await ctx.defer(hidden=True)

        if amount <= 0:
            return await ctx.send("Amount must be > 0", hidden=True)

        if add_to_everyone and not member:
            resp_content = "@everyone"
            for mem in ctx.guild.members:
                if not mem.bot:
                    await self.check_user(mem.id)
                    await self.add_coins(ctx, user=mem, amount=amount, were=where, all=True)
            await self.log_money("@everyone", amount, f"{ctx.author.mention} used /add_gems")

        else:
            if not member:
                member = ctx.author
            
            await self.check_user(member.id)

            await self.add_coins(ctx, user=member, amount=amount, where=where, all=False)
            await self.log_money(member.mention, amount, f"{ctx.author.mention} used /add_gems")
            resp_content = member.mention

        embed = discord.Embed(

            description=f"Added **__{await self.client.round_int(int(amount))} Titan Gems__** 💎 to {resp_content}'s {where} 🤑 ",
            color=self.client.failure)
        embed.set_footer(text="TN | Economy",
                         icon_url=self.client.png)
        return await ctx.send(embed=embed, hidden=True)


    @cog_slash(name="remove_gems", description="Remove x amount of 💎 from a member", guild_ids=const.slash_guild_ids, options=[
        create_option(name="amount", description="Amount of 💎 to remove", option_type=4, required=True) | {"focused": True},
        create_option(name="member", description="The member to remove the 💎 from", option_type=6, required=False),
        create_option(name="remove_from_everyone", description="Remove 💎 from everyone or not", option_type=5, required=False)
    ])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def remove_gems(self, ctx, amount:int=None, member:discord.Member=None, remove_from_everyone:bool=False):
        await ctx.defer(hidden=True)

        if amount <= 0:
            return await ctx.send("Amount must be > 0", hidden=True)

        if remove_from_everyone and not member:
            for mem in ctx.guild.members:
                if not mem.bot:
                    data = await self.check_user(mem.id)
                    if data["wallet"] - amount < 0:
                        if (data["wallet"] + data["bank"]) - amount >= 0:
                            wallet_amount = data["wallet"]
                            self.client.economydata[str(mem.id)]["wallet"] -= wallet_amount
                            self.client.economydata[str(mem.id)]["bank"] -= (amount - wallet_amount) 
                    else:
                        self.clint.economydata[str(mem.id)]["wallet"] -= amount

            await self.log_money("@everyone", -amount, f"{ctx.author.mention} used /remove_gems")
            result = "@everyone"

        else:
            if not member:
                member = ctx.author
            
            data = await self.check_user(member.id)
            if data["wallet"] - amount < 0:
                if (data["wallet"] + data["bank"]) - amount < 0:
                    embed = discord.Embed(
                        description=f"That person only has **__{await self.client.round_int(data['wallet'] + data['bank'])} Titan Gems.💎__**",
                        color=self.client.failure)
                    embed.set_footer(text="TN | Economy",
                                    icon_url=str(self.client.user.avatar_url_as(static_format='png', size=2048)))
                    return await ctx.send(embed=embed, hidden=True)
                    
                else:
                    pocketmoneyamount = data["wallet"]
                    self.client.economydata[str(member.id)]["wallet"] -= pocketmoneyamount
                    self.client.economydata[str(member.id)]["bank"] -= (amount - pocketmoneyamount)

            else:
                self.client.economydata[str(member.id)]["wallet"] -= amount

            await self.log_money(member.mention, -amount, f"{ctx.author.mention} used /remove_gems")
            result = member.mention

        embed = discord.Embed(
            description=f"Removed **__{await self.client.round_int(amount)} Titan Gems__** 💎 from {result} 😭",
            color=self.client.failure)
        embed.set_footer(text="TN | Economy",
                         icon_url=str(self.client.user.avatar_url_as(static_format='png', size=2048)))
        
        return await ctx.send(embed=embed, hidden=True)
   

   

    @cog_slash(name="deposit", description="Deposit 💎 from your wallet into your bank", guild_ids=const.slash_guild_ids,
    options=[
        create_option(name="amount", description="The amount to deposit (ignore to deposit ALL 💎)", option_type=4, required=False)
    ])
    async def deposit(self, ctx, amount:int=0):
        await ctx.defer(hidden=True)

        data = await self.check_user(ctx.author_id)

        if not data["wallet"]:
            em = discord.Embed(color=self.client.failure, description="You have nothing to depoist.")
            return await ctx.embed(embed=em, footer="Economy")

        if not amount:
            amount = data["wallet"]
            data["wallet"] = 0
            data["bank"] += amount

            dep_amount = amount

        else:
            if amount > data["wallet"]:
                dep_amount = data["wallet"]
                data["bank"], data["wallet"] = data["wallet"], 0 
            else:
                dep_amount = amount
                data["wallet"] -= amount
                data["bank"] += amount
        

        em = discord.Embed(
                description=f"Deposited **__{await self.client.round_int(int(dep_amount))} Titan Gems__** 💎",
                color=self.client.failure)
        em.set_footer(text="TN | Economy",
                         icon_url=self.client.png)

        return await ctx.send(embed=em, hidden=True)


    @cog_slash(name="withdraw", description="Withdraw 💎 from your bank", guild_ids=const.slash_guild_ids,
    options=[
        create_option(name="amount", description="The amount to withdraw (ignore to withdraw ALL 💎)", option_type=4, required=False)
    ])
    async def withdraw(self, ctx, amount:int=0):
        await ctx.defer(hidden=True)

        data = await self.check_user(ctx.author_id)

        if not data["bank"]:
            em = discord.Embed(color=self.client.failure, description="You have nothing to withdraw.")
            return await ctx.embed(embed=em, footer="Economy")

        if not amount:
            data["wallet"], data["bank"] = data["bank"], 0

            with_amount = amount

        else:
            if amount > data["bank"]:
                with_amount = data["bank"]
                data["wallet"], data["bank"] = data["bank"], 0 
            else:
                with_amount = amount
                data["bank"] -= amount
                data["wallet"] += amount
        

        em = discord.Embed(
                description=f"You withdrew **__{await self.client.round_int(int(with_amount))} gems__** 💎",
                color=self.client.failure)

        return await ctx.embed(embed=em, footer="Economy")

    @cog_slash(name="transfer", description="Give someone 💎 fromr your wallet", guild_ids=const.slash_guild_ids, options=[
        create_option(name="member", description="The person who will be receiving the 💎", option_type=6, required=True) | {"focused": True},
        create_option(name="amount", description="The amount of 💎 to give (ignore to transfer ALL (wallet) 💎)", option_type=4, required=False)
    ])
    async def transfer(self, ctx:SlashContext, amount:int=0, member:discord.Member=None):
        await ctx.defer(hidden=True)
        data = await self.check_user(ctx.author.id)

        recipient = await self.check_user(member.id)

        if not amount:
            amount = data["wallet"]

        if data["wallet"] - amount < 0:
            embed = discord.Embed(title="Transaction Failed",
                                  description=f"You don't have enough money!",
                                  color=self.client.failure)
            return await ctx.embed(embed=embed, footer="Economy")

        data["wallet"] -= amount
        await self.log_money(ctx.author.mention, -amount, f"Transfer to {member.mention}")

        recipient["wallet"] += amount
        await self.log_money(member.mention, amount, f"Transfer from {ctx.author.mention}")

        embed = discord.Embed(
            description=f"💎 | Gave **__{await self.client.round_int(int(amount))} Titan Gems__** to {member.mention} 👍",
            color=self.client.failure)
        return await ctx.embed(embed=embed, footer="Economy")


    @cog_slash(name="new", description="[STAFF] Create an item to put in /shop", guild_ids=const.slash_guild_ids, options=[
        create_option(name="item_name", description="The name that will appear in /shop", option_type=3, required=True),
        create_option(name="item_description", description="The description the item will have", option_type=3, required=True),
        create_option(name="price", description="The price to sell the item at in /shop", option_type=4, required=True),
        create_option(name="item_category", description="The category the item will belong to in /shop", option_type=3, required=True, choices=[
            create_choice(value="gems", name="💎 Titan Gems"),
            create_choice(value="perks", name="💬 Chat Perks"),
            create_choice(value="roles", name="🧻 Chat Roles")
        ]),
        create_option(name="stock_amount", description="Amount of this item for sale", option_type=4, required=False),
        create_option(name="availability_duration", description="Duration the item will be in store for (minimum 10 mins)", option_type=3, required=False),
        create_option(name="role_required", description="Role the buyer must have in order to purchase this item", option_type=8, required=False),
        create_option(name="role_to_receive", description="The role the buyer will receive when buying/using this item", option_type=8, required=False),
        create_option(name="role_to_remove", description="The role the buyer will lose when buying/using this item", option_type=8, required=False),
        create_option(name="min_balance", description="Minimum balance the buyer must have to be able to buy the item", option_type=4, required=False),
        create_option(name="message_when_purchased", description="The message the bot will reply with to the buyer when the item is purchased", option_type=3, required=False),
        create_option(name="show_in_inv", description="If the item will show in the buyer's inventory", option_type=5, required=False),
        ])
    @commands.has_permissions(manage_roles=True)
    @commands.guild_only()
    async def create_item(self, ctx:SlashContext, item_name:str=None, item_description:str=None, price:int=100000, stock_amount:int=None, item_category:str=None, show_in_inv:bool=True, availability_duration:str=None, role_to_receive:discord.Role=None, role_to_remove:discord.Role=None, min_balance:int=0, message_when_purchased:str=None, role_required:discord.Role=None):
        await ctx.defer(hidden=True)
        
        if availability_duration:
            time_in_seconds = int(await self.client.format_duration(availability_duration))
            if time_in_seconds < 600:
                return await ctx.send("It should atleast be 10 minutes in the store.", hidden=True)
            availability_duration = time_in_seconds

        if not role_to_receive and item_category == "roles":
            return await ctx.send("You must specify the `role_to_receieve` parameter if the item category is '💬 Chat Roles'", hidden=True)
            
        new_item = {
            "name": item_name,
            "desc": item_description,
            "price": price,
            "stock": stock_amount,
            "category": item_category,
            "show_in_inv": show_in_inv,
            "best_before": availability_duration,
            "role_to_receive": role_to_receive.id if role_to_receive else None,
            "role_to_remove": role_to_remove.id if role_to_remove else None,
            "min_balance": min_balance,
            "reply_msg": message_when_purchased,
            "role_req": role_required.id if role_required else None
        }

        self.shopdata[new_item["name"]] = new_item

        return await ctx.send("🎉 Item created successfully!", hidden=True)

    
    @cog_slash(name="shop", description="View the store 💎", guild_ids=const.slash_guild_ids)
    async def shop(self, ctx:SlashContext):
        await ctx.defer(hidden=False)
        
        main_desc = f"*Buy an item with `/purchase`.*\n*For more info about an item use `/item_info`*"

        tg = discord.Embed(title=f"💎 | Titan Gems", description=main_desc, color=self.client.failure)

        cp = discord.Embed(title=f"💬 | Chat Perks", description=main_desc, color=self.client.failure)

        cr = discord.Embed(title=f"🧻 | Chat Roles", description=main_desc, color=self.client.failure)
        
        shoplist = sorted([(x["price"], x) for x in self.shopdata.copy().values()], key=lambda f: f[0], reverse=False)
        
        titan_gems_embeds = []; tg_count = 0
        chat_perks_embeds = []; cp_count = 0
        chat_roles_embeds = []; cr_count = 0

        for price, data in shoplist:  # categories: gems, perks, roles
            if data["stock"] != 0:
                if data["category"] == "gems" and tg_count <= 10:
                    tg.add_field(name=f"💎 {await self.client.round_int(price)} - {data['name']}",
                    value=f"{data['desc']}\n\u200b", inline=False)
                    tg_count += 1

                elif data["category"] == "perks" and cp_count <= 10:
                    cp.add_field(name=f"💎 {await self.client.round_int(price)} - {data['name']}", 
                    value=f"{data['desc']}", inline=False)
                    cp_count += 1
                elif data["category"] == "roles" and cr_count <= 10:
                    cr.add_field(name=f"💎 {await self.client.round_int(price)} - {data['name']}",
                    value=f"{data['desc']}\n\u200b", inline=False)
                    cr_count += 1
            else:
                if data["category"] == "gems" and tg_count <= 10:
                    tg.add_field(name=f"💎 ~~{await self.client.round_int(price)} - {data['name']}~~ | `out of stock`",
                    value=f"{data['desc']}\n\u200b", inline=False)
                    tg_count += 1

                elif data["category"] == "perks" and cp_count <= 10:
                    cp.add_field(name=f"💎 ~~{await self.client.round_int(price)} - {data['name']}~~ | `out of stock`", 
                    value=f"{data['desc']}\n\u200b", inline=False)
                    cp_count += 1

                elif data["category"] == "roles" and cr_count <= 10:
                    cr.add_field(name=f"💎 ~~{await self.client.round_int(price)} - {data['name']}~~ | `out of stock`",
                    value=f"{data['desc']}\n\u200b", inline=False)
                    cr_count += 1

            if tg_count == 10:
                titan_gems_embeds.append(tg)
                tg = discord.Embed(title=f"💎 | Titan Gems", description=main_desc, color=self.client.failure)
                tg_count = 0

            if cp_count == 10:
                chat_perks_embeds.append(tg)
                cp = discord.Embed(title=f"💬 | Chat Perks", description=main_desc, color=self.client.failure)
                cp_count = 0

            if cr_count == 10:
                chat_roles_embeds.append(tg)
                cr = discord.Embed(title=f"🧻 | Chat Roles", description=main_desc, color=self.client.failure)
                cr_count = 0

            if (len(chat_roles_embeds)*10) + (len(chat_perks_embeds)*10) + (len(titan_gems_embeds)*10) + cp_count + cr_count + tg_count == len(shoplist):
                if tg_count != 0:
                    titan_gems_embeds.append(tg)
                    tg_count = 0
                if cp_count != 0:
                    chat_perks_embeds.append(cp)
                    cp_count = 0
                if cr_count != 0:
                    chat_roles_embeds.append(cr)
                    cr_count = 0

        ts = datetime.utcnow().timestamp()

        nav_buttons = [
            create_button(
                style=ButtonStyle.blue,
                label="Previous Page",
                custom_id=f"store_{ts}_l"),
            create_button(
                style=ButtonStyle.blue,
                label="Next Page",
                custom_id=f"store_{ts}_r"
            )
                
                ]

        category_buttons = [
            create_button(
                style=ButtonStyle.green,
                label="💎 Titan Gems",
                custom_id=f"store_{ts}_tg",
                disabled=True if not titan_gems_embeds else False
            ),
            create_button(
                style=ButtonStyle.green,
                label="💬 Chat Perks",
                custom_id=f"store_{ts}_cp",
                disabled=True if not chat_perks_embeds else False
            ),
            create_button(
                style=ButtonStyle.green,
                label="🧻 Chat Roles",
                custom_id=f"store_{ts}_cr",
                disabled=True if not chat_roles_embeds else False
            )
        ]

        timeout_buttons = [
            create_button(
                style=ButtonStyle.red,
                label="Timed Out",
                disabled=True
            )
        ]

        tg_ar = create_actionrow(*nav_buttons, *category_buttons[1:])
        cp_ar = create_actionrow(*nav_buttons, category_buttons[0], category_buttons[2])
        cr_ar = create_actionrow(*nav_buttons, *category_buttons[:-1])
        to_ar = create_actionrow(*timeout_buttons)

        if titan_gems_embeds:
            ar_in_use = tg_ar
            em_li_in_use = titan_gems_embeds
        elif chat_perks_embeds:
            ar_in_use = cp_ar
            em_li_in_use = chat_perks_embeds
        else:
            ar_in_use = cr_ar
            em_li_in_use = chat_roles_embeds

        page = 0

        if not shoplist:
            em = discord.Embed(title=f"Titan Network Store", description=main_desc + "\n\n`Store Empty`", color=self.client.failure)
            em.set_footer(text="TN | Economy", icon_url=self.client.png)
            return await ctx.send(embed=em)

        msg = await ctx.send(embed=em_li_in_use[0], components=[ar_in_use])

        while 1:

            try:
                button_ctx: ComponentContext = await wait_for_component(
                    self.client, components=[ar_in_use], timeout=30
                    )

                if button_ctx.author_id != ctx.author.id:
                    await button_ctx.reply("You were not the author of this command therefore cannot use these components.", hidden=True)
                    continue
                
                if button_ctx.custom_id == f"store_{ts}_l":
                    page -= 1
                    if page == -1:
                        page = len(em_li_in_use)-1


                elif button_ctx.custom_id == f"store_{ts}_r":
                    page += 1
                    if page > len(em_li_in_use)-1:
                        page = 0

                elif button_ctx.custom_id == f"store_{ts}_tg":
                    em_li_in_use = titan_gems_embeds
                    page = 0
                    ar_in_use = tg_ar

                elif button_ctx.custom_id == f"store_{ts}_cp":
                    em_li_in_use = chat_perks_embeds
                    page = 0
                    ar_in_use = cp_ar

                elif button_ctx.custom_id == f"store_{ts}_cr":
                    em_li_in_use = chat_roles_embeds
                    page = 0
                    ar_in_use = cr_ar

                try:
                    await button_ctx.edit_origin(embed=em_li_in_use[page], components=[ar_in_use])
                except NotFound:
                    # message was probably deleted so we will return without raising TimeoutError
                    return

            except TimeoutError:
                
                await msg.edit(embed=em_li_in_use[page], components=[to_ar])
                break


    @cog_slash(name="item_info", description="Display information about an item in /shop", guild_ids=const.slash_guild_ids,
    options=[
        create_option(name="item_name", description="The name of the item", option_type=3, required=True)
    ])
    @commands.guild_only()
    async def item_info(self, ctx:SlashContext, item_name:str=None):
        await ctx.defer(hidden=True)
        
        found = False
        for key in self.shopdata.keys():
            if item_name.lower() in key.lower():
                itemdata = self.shopdata[key]
                found = True
                break

        if found is False:
            userdata = await self.check_user(ctx.author.id)
            for item in userdata["inventory"]:
                if item_name.lower() in item["name"].lower():
                    itemdata = item
                    found = True
                    break

        if found is False:
            return await ctx.send("Was not able to find that item.", hidden=True)

        embed = discord.Embed(title=f"Item Info", color=self.client.failure)

        embed.add_field(name=f"Name",
                        value=f"{itemdata['name']}", inline=True)

        embed.add_field(name=f"Price",
                        value=f"{itemdata['price']}", inline=True)

        embed.add_field(name=f"Description",
                        value=f"{itemdata['desc']}", inline=True)


        embed.add_field(name=f"Show in inventory",
                        value=f"{itemdata['show_in_inv']}", inline=True)

        bb = itemdata.get('best_before', None)
        bb = f"<t:{bb}:R>" if bb else "Infinite"
        embed.add_field(name=f"Time remaining",
                        value=bb, inline=True)

        stock = itemdata.get('stock', None)
        stock = stock if stock else "Infinite"
        embed.add_field(name=f"Stock remaining",
                        value=stock, inline=True)

        role_req = itemdata.get('role_req', None)
        role_req = f"<@&{role_req}>" if role_req else None
        embed.add_field(name=f"Role required",
                        value=role_req, inline=True)

        role_give = itemdata.get('role_to_receive', None)
        role_give = f"<@&{role_give}>" if role_give else None
        embed.add_field(name=f"Role to give",
                        value=role_give, inline=True)

        role_remove = itemdata.get('role_to_remove', None)
        role_remove = f"<@&{role_remove}>" if role_remove else None
        embed.add_field(name=f"Role removed",
                        value=role_remove, inline=True)

        embed.add_field(name=f"Store category",
                        value=f"{itemdata['category']}".replace("gems", "💎 Titan Gems").replace("perks", "💬 Chat Perks").replace("roles", "🧻 Chat Roles"), inline=False)

        min_bal = itemdata.get('min_balance', 0)
        embed.add_field(name=f"Min required balance",
                        value=min_bal, inline=True)

        msg_reply = itemdata.get('reply_msg', None)
        embed.add_field(name=f"Reply message",
                        value=msg_reply, inline=True)

        return await ctx.embed(embed=embed, footer="Economy")


    @cog_slash(name="purchase", description="Purchase an item from /shop", guild_ids=const.slash_guild_ids, options=[
        create_option(name="item_name", description="Name of item to buy", option_type=3, required=True)
    ])
    @commands.guild_only()
    async def purchase(self, ctx:SlashContext, item_name:str=None):
        await ctx.defer(hidden=True)

        found = False
        for key in self.shopdata.keys():
            if item_name.lower() in key.lower():
                itemdata = self.shopdata[key].copy()
                found = True
                break
        if found is False:
            return await ctx.send("Was not able to find that item.", hidden=True)

        userdata = await self.check_user(ctx.author.id)

        if itemdata.get('role_req', None):
            if int(itemdata['role_req']) not in [i.id for i in ctx.author.roles]:
                embed = discord.Embed(
                    description=f"**You need the <@&{itemdata['role_req']}> role to buy this item.**",
                    color=self.client.failure)
                return await ctx.embed(embed=embed, footer="Economy")

        if itemdata.get("stock", None):
            if int(itemdata["stock"]) <= 0:
                return await ctx.send("This item is out of stock", hidden=True)

        if not itemdata.get("show_in_inv", False):
            if itemdata.get("min_balance", 0):
                if userdata["wallet"] + userdata["bank"] < itemdata["min_balance"]:
                    return await ctx.send(
                        f"You need at least **__{await self.client.round_int(itemdata['min_balance'])} 💵__**")

            if itemdata["price"] > 0:
                price = int(itemdata["price"])
                if userdata["wallet"] - price < 0:
                    if (userdata["wallet"] + userdata["bank"]) - price < 0:
                        embed = discord.Embed(title="Transaction Failed",
                                              description=f"You don't have enough money to buy this item!",
                                              color=self.client.failure)
                        return await ctx.embed(embed=embed, footer="Economy")

                    else:
                        pocketmoneyamount = userdata["wallet"]
                        self.client.economydata[str(ctx.author.id)]["wallet"] -= pocketmoneyamount
                        self.client.economydata[str(ctx.author.id)]["bank"] -= (price - pocketmoneyamount)

                else:
                    self.client.economydata[str(ctx.author.id)]["wallet"] -= price

            if itemdata["price"] < 0:
                self.client.economydata[str(ctx.author.id)]["wallet"] += abs(itemdata["price"])

            await self.log_money(ctx.author.mention, -itemdata["price"], f"Purchased {itemdata['name']}")

            if itemdata.get("stock", 0):
                self.shopdata[key]["stock"] -= 1

            if itemdata.get("role_to_receive", 0):
                guildrole = ctx.guild.get_role(int(itemdata["role_to_receive"]))
                await ctx.author.add_roles(guildrole)

            if itemdata.get("role_to_remove", 0):
                guildrole = ctx.guild.get_role(int(itemdata["role_to_remove"]))
                await ctx.author.remove_roles(guildrole)

            if itemdata.get("reply_msg", None):
                await ctx.send(itemdata["reply_msg"], hidden=True)

        if itemdata.get("show_in_inv", False):
            if itemdata["price"] > 0:
                price = int(itemdata["price"])
                if userdata["wallet"] - price < 0:
                    if (userdata["wallet"] + userdata["bank"]) - price < 0:
                        embed = discord.Embed(title="Economy",
                                              description=f"You don't have enough money to buy this item!",
                                              color=self.client.failure)
                        return await ctx.embed(embed=embed, footer="Economy")

                    else:
                        pocketmoneyamount = userdata["wallet"]
                        self.client.economydata[str(ctx.author.id)]["wallet"] -= pocketmoneyamount
                        self.client.economydata[str(ctx.author.id)]["bank"] -= (price - pocketmoneyamount)

                else:
                    self.client.economydata[str(ctx.author.id)]["wallet"] -= price

            if itemdata["price"] < 0:
                self.client.economydata[str(ctx.author.id)]["wallet"] += abs(itemdata["price"])

            if itemdata.get("stock", 0):
                self.shopdata[key]["stock"] -= 1

            self.client.economydata[str(ctx.author.id)]["inventory"].append(itemdata)
            await ctx.send(
                f"Added {itemdata['name']} to your inventory. Use /use to use the item or /inventory to see your inventory.", hidden=True)

            if self.config["inventory_usage"]:
                channel = self.guild.get_channel(self.config["inv_usage_channel_id"])
                embed = discord.Embed(title="User used inventory",
                                      description=f"Username: {ctx.author.mention}\nItem received: {itemdata['name']}",
                                      color=self.client.failure)
                embed.set_footer(text="TN | Economy",
                                 icon_url=str(self.client.user.avatar_url_as(static_format='png', size=2048)))
                await channel.send(embed=embed)
            return

    @cog_slash(name="delete_item", description="Delete an item from /shop", guild_ids=const.slash_guild_ids, options=[
        create_option(name="item_name", description="The name of the item to delete", option_type=3, required=True) | {"focused": True}
    ])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def delete_item(self, ctx:SlashContext, item_name:str=None):
        await ctx.defer(hidden=True)

        for key in self.shopdata.keys():
            if self.shopdata.pop(key, None):

                embed = discord.Embed(description=f"**Deleted {item_name}**",
                                      color=self.client.failure)
                return await ctx.embed(embed=embed, footer="Economy")

        return await ctx.send("Was not able to find that item.", hidden=True)


    @cog_slash(name="inventory", description="View your inventory", guild_ids=const.slash_guild_ids, options=[
        create_option(name="member", description="The member's inventory to view", option_type=6, required=False)
    ])
    async def inventory(self, ctx:SlashContext, member:discord.Member=None):
        await ctx.defer(hidden=True)

        if not member:
            member = ctx.author
        elif isinstance(member, int):
            member = member

        if self.config.get("inventory_usage", None):
            channel = self.guild.get_channel(self.config["inv_usage_channel_id"])
            embed = discord.Embed(title="User used inventory", description=f"Username: {ctx.author.mention}",
                                  color=self.client.failure)
            embed.set_footer(text="TN | Economy",
                             icon_url=str(self.client.user.avatar_url_as(static_format='png', size=2048)))
            await channel.send(embed=embed)

        if not isinstance(member, int) and self.client.user.id  == member.id:
            return await ctx.send("I'm not even a real person 😤", hidden=True)

        userdata = await self.check_user(member.id if not isinstance(member, int) else member)

        embed = discord.Embed(title=f"{member.name if not isinstance(member, int) else f'~~{member}~~'}'s Inventory",
                              description=f"Use an item with /use.\n"
                                          f"For more information on an item use the /item_info.",
                              color=self.client.failure)

        embed.set_footer(text="TN | Economy",
                         icon_url=self.client.png)

        inventory = sorted(userdata["inventory"], key=lambda x: x["price"], reverse=False)
        count = 0
        gotenbefore = []
        for itemdata in inventory:
            found = False
            for itemdata1 in gotenbefore:
                if itemdata["name"] == itemdata1["name"]:
                    itemdata1["count"] += 1
                    found = True
            if found is False:
                itemdata["count"] = 1
                gotenbefore.append(itemdata)

        for itemdata in gotenbefore:
            embed.add_field(
                name=f"{itemdata['count']}x 💵 {await self.client.round_int(itemdata['price'])} - {itemdata['name']}",
                value=f"{itemdata['desc']}", inline=False)
            count += 1

        return await ctx.embed(embed=embed, footer="Economy")


    @cog_slash(name="use", description="Use an item in your inventory", guild_ids=const.slash_guild_ids, options=[
        create_option(name="item_name", description="The name of the item to use", option_type=3, required=True) | {"focused": True}
    ])
    @commands.guild_only()
    async def use(self, ctx:SlashContext, item_name:str=None):
        await ctx.defer(hidden=True)
        found = False
        userdata = await self.check_user(ctx.author.id)
        for item in userdata["inventory"]:
            if item_name.lower() in item["name"].lower():

                if item["min_balance"] is not None:
                    if userdata["wallet"] + userdata["bank"] < item["min_balance"]:
                        return await ctx.send(
                            f"You need atleast **__{await self.client.round_int(item['min_balance'])}💵__** to use this item.", hidden=True)

                itemdata = self.client.economydata[str(ctx.author.id)]["inventory"].pop(userdata["inventory"].index(item))
                found = True
                break

        if found is False:
            return await ctx.send("Was not able to find that item.", hidden=True)

        if itemdata.get("role_to_receive", None):
            guildrole = ctx.guild.get_role(int(itemdata["role_to_receive"]))
            await ctx.author.add_roles(guildrole)

        if itemdata.get("role_to_remove", None):
            guildrole = ctx.guild.get_role(int(itemdata["role_to_remove"]))
            await ctx.author.remove_roles(guildrole)

        if itemdata.get("reply_msg", None):
            await ctx.send(itemdata["reply_msg"], hidden=True)

        if self.config["inventory_usage"]:
            channel = self.guild.get_channel(self.config["inv_usage_channel_id"])
            embed = discord.Embed(title="User used item",
                                  description=f"Username: {ctx.author.mention}\nItem used: {itemdata['name']}",
                                  color=self.client.failure)
            embed.set_footer(text="TN | Economy",
                             icon_url=str(self.client.user.avatar_url_as(static_format='png', size=2048)))
            await channel.send(embed=embed)

        return await ctx.send(f"Used {itemdata['name']} 🥳", hidden=True)


    @cog_slash(name="give_item", description="Give an item from your inventory to a server member", guild_ids=const.slash_guild_ids, options=[
        create_option(name="item_name", description="The name of the item", option_type=3, required=True),
        create_option(name="member", description="The person who will be receiving the item", option_type=6, required=True)
    ])
    @commands.guild_only()
    async def giveitem(self, ctx:SlashContext, item_name:str=None, member:discord.Member=None):
        await ctx.defer(hidden=True)
        
        await self.check_user(member.id if not isinstance(member, int) else member)

        userdata = await self.check_user(ctx.author.id)

        found = False
        for item in userdata["inventory"]:
            if item_name.lower() in item["name"].lower():
                itemdata = self.client.economydata[str(ctx.author.id)]["inventory"].pop(userdata["inventory"].index(item))
                self.client.economydata[str(member.id if not isinstance(member, int) else member)]["inventory"].append(itemdata)
                found = True
                break

        if found is False:
            return await ctx.send("Was not able to find that item.", hidden=True)

        embed = discord.Embed(description=f"**{ctx.author.mention} Gave {f'<@!{member.id}>' if not isinstance(member, int) else f'<@!{member}>'}:**",
                              color=self.client.failure)

        embed.add_field(name=itemdata['name'],
                        value=f"{itemdata['desc']}", inline=False)

        await ctx.embed(embed=embed, footer="Economy")

        if const.logging["inventory_usage"]:
            channel = self.guild.get_channel(const.logchannelid)
            embed = discord.Embed(title="User gave item",
                                  description=f"Username: {ctx.author.mention}\nItem given: {itemdata['name']}\nReceiver: {f'<@!{member.id}>' if not isinstance(member, int) else f'<@!{member}>'}",
                                  color=self.client.failure)
            embed.set_footer(text="TN | Economy",
                             icon_url=self.client.png)
            await channel.send(embed=embed)

    @cog_slash(name="add_stock", description="Add stock to an item in store", guild_ids=const.slash_guild_ids, options=[
        create_option(name="item_name", description="The item to increase the stock for", option_type=3, required=True),
        create_option(name="stock_amount", description="The new stock of item available", option_type=4, required=True)
    ])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def add_stock(self, ctx:SlashContext, item_name:str=None, stock_amount:int=None):
        await ctx.defer(hidden=True)

        found = False
        for key in self.shopdata.keys():
            if item_name.lower() in key.lower():
                itemdata = self.shopdata[key].copy()
                found = True
                break
        if found is False:
            return await ctx.send("Was not able to find that item.", hidden=True)

        if itemdata.get('stock', None) is not None:
            self.shopdata[itemdata['name']]['stock'] += stock_amount
            em = discord.Embed(color=self.client.failure, title="Stock Updated", 
            description=f"New stock for **{itemdata['name']}**: `{self.shopdata[itemdata['name']]['stock']}`")
            return await ctx.embed(embed=em, footer="Economy")
        
        else:
            em = discord.Embed(color=self.client.failure, title="Failed stock update",
            description=f"There is an unlimited amount of this item in stock.\nThere is no need to increase stock")
            return await ctx.embed(embed=em, footer="Economy")

    @cog_slash(name="delete_item", description="Delete an item from /shop", guild_ids=const.slash_guild_ids, options=[
        create_option(name="item_name", description="The item to delete", option_type=3, required=True) | {"focused": True}
    ])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def delete_item(self, ctx:SlashContext, item_name:str=None):
        await ctx.defer(hidden=True)

        found = False
        for key in self.shopdata.keys():
            if item_name.lower() in key.lower():
                result = self.shopdata.pop(key, False)
                if result:
                    em = discord.Embed(color=self.client.failure, title="Item deleted", description="This item will no longer appear in stores")
                    return await ctx.embed(embed=em, footer="Economy")
                
        if found is False:
            return await ctx.send("Was not able to find that item.", hidden=True)

    # @commands.command(aliases=["banklb", "bankleaderboard", "moneyleaderboard", "coinleaderboard", "coinlb", "moneylb", "economylb", "rich"])
    # async def baltop(self, ctx):
    #     playerslist = []
    #     totalcoins = 0
    #     for discordid, memberdata in self.client.economydata.copy().items():
    #         if discordid == "last_daily_pay_out":
    #             continue
    #         totalcoins += memberdata["wallet"] + memberdata["bank"]
    #         playerslist.append([discordid, memberdata["wallet"] + memberdata["bank"]])

    #     playerslist = sorted(playerslist, key=lambda x: x[1], reverse=True)

    #     embeds = []

    #     ranking = 1
    #     fieldcount = 0
    #     description1 = ""
    #     for player in playerslist:
    #         try:
    #             guild = ctx.guild
    #             discordid = player[0].replace("<@!", "").replace(">", "").replace("<@", "")
    #             discorduser = guild.get_member(int(discordid))
    #         except:
    #             continue
    #         if discorduser is None:
    #             continue
    #         # print(discorduser)

    #         if player[1] <= 10000:
    #             break
    #         tempranking = ranking
    #         if ranking == 1:
    #             tempranking = "🥇"
    #         elif ranking == 2:
    #             tempranking = "🥈"
    #         elif ranking == 3:
    #             tempranking = "🥉"
    #         else:
    #             tempranking = f"{ranking}."

    #         description1 += f"**{tempranking} {discorduser.mention}** <:waveydash:896680122076250143> **__{await self.client.formatint(int(player[1]))} <a:miasmacoin:902351657361371188>__**\n"

    #         ranking += 1
    #         fieldcount += 1
    #         if fieldcount >= 10:
    #             embed = discord.Embed(title=f"{ctx.guild.name}'s Net Leaderboard \💲",
    #                                   description=f"Total Titan Gems in the economy **__{await self.client.formatint(int(totalcoins))}__**\n\n{description1}",
    #                                   color=0x8b46d3)
    #             embed.set_footer(text="TN | Economy",
    #                              icon_url=str(self.client.user.avatar_url_as(static_format='png', size=2048)))
    #             embeds.append(embed)
    #             description1 = ""
    #             fieldcount = 0
    #         if ranking >= 50:
    #             break

    #     embed = discord.Embed(title=f"{ctx.guild.name}'s Net Leaderboard \💲",
    #                           description=f"Total Titan Gems in the economy **__{await self.client.formatint(int(totalcoins))}__**\n\n{description1}",
    #                           color=0x8b46d3)
    #     embed.set_footer(text="TN | Economy",
    #                      icon_url=str(self.client.user.avatar_url_as(static_format='png', size=2048)))
    #     embeds.append(embed)

    #     msg = await ctx.send(embed=embeds[0])

    #     pages = 0
    #     left = "◀"
    #     stop = "⏹"
    #     right = "▶"

    #     await msg.add_reaction("◀")
    #     await msg.add_reaction("⏹")
    #     await msg.add_reaction("▶")

    #     def check(reaction, user):
    #         return user == ctx.author and str(reaction.emoji) in [left, right, stop]

    #     while True:
    #         try:
    #             reaction, user = await self.client.wait_for("reaction_add", timeout=120, check=check)
    #             await msg.remove_reaction(reaction, user)

    #             if str(reaction.emoji) == left:
    #                 pages -= 1
    #                 if pages <= 0:
    #                     pages = 0

    #             if str(reaction.emoji) == right:
    #                 pages += 1
    #                 if pages >= len(embeds) - 1:
    #                     pages = len(embeds) - 1

    #             if str(reaction.emoji) == stop:
    #                 raise Exception("Stopped")

    #             await msg.edit(embed=embeds[pages])

    #         except:
    #             embed = discord.Embed(title="Timed out", color=0x8b46d3)
    #             embed.set_footer(text="TN | Economy",
    #                              icon_url=str(self.client.user.avatar_url_as(static_format='png', size=2048)))
    #             await msg.edit(embed=embed)
    #             break

    @on_ready_replacement.before_loop
    @update_loop.before_loop
    @on_ready_replacement.before_loop
    async def before_task_loop(self):
        await self.client.wait_until_ready()

def setup(client):
    client.add_cog(EconomyCommands(client))
    
