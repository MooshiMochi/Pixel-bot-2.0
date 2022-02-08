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


    @cog_slash(name="balance", description="Check your or a member's bank and wallet balance", guild_ids=const.slash_guild_ids, options=[
        create_option(name="member", description="The server memebr to check the balance for", option_type=6, required=False)])
    @commands.guild_only()
    async def balance(self, ctx, member:discord.Member=None):
        await ctx.defer(hidden=True)

        if member is None:
            member = ctx.author
        
        data = await self.check_user(member.id)

        embed = discord.Embed(title=f"{member.name}'s Balance \💰", color=self.client.failure)

        embed.add_field(name="<:wallet:892887812909727744> **Wallet:**",
                        value=f"{await self.client.round_int(int(data['wallet']))}💎",
                        inline=True)

        embed.add_field(name="🏧 **Bank:**",
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


    @cog_slash(name="create_item", description="[STAFF] Create an item to put in /shop", guild_ids=const.slash_guild_ids, options=[
        create_option(name="item_name", description="The name that will appear in /shop", option_type=3, required=True),
        create_option(name="item_description", description="The description the item will have", option_type=3, required=True),
        create_option(name="price", description="The price to sell the item at in /shop", option_type=4, required=True),
        create_option(name="stock_amount", description="Amount of this item for sale", option_type=4, required=True),
        create_option(name="item_category", description="The category the item will belong to in /shop", option_type=3, required=True, choices=[
            create_choice(value="gems", name="💎 Titan Gems"),
            create_choice(value="perks", name="💬 Chat Perks"),
            create_choice(value="roles", name="🧻 Chat Roles")
        ]),
        
        create_option(name="show_in_inv", description="If the item will show in the buyer's inventory", option_type=5, required=True),
        create_option(name="availability_duration", description="Duration the item will be in store for (minimum 10 mins)", option_type=3, required=True),
        create_option(name="role_to_receive", description="The role the buyer will receive when buying/using this item", option_type=8, required=False),
        create_option(name="role_to_remove", description="The role the buyer will lose when buying/using this item", option_type=8, required=False),
        create_option(name="min_balance", description="Minimum balance the buyer must have to be able to buy the item", option_type=4, required=False),
        create_option(name="message_when_purchased", description="The message the bot will reply with to the buyer when the item is purchased", option_type=3, required=False)
        ])
    @commands.has_permissions(manage_roles=True)
    @commands.guild_only()
    async def create_item(self, ctx:SlashContext, item_name:str=None, item_description:str=None, price:int=100000, stock_amount:int=1, item_category:str=None, show_in_inv:bool=True, availability_duration:str=None, role_to_receive:discord.Role=None, role_to_remove:discord.Role=None, min_balance:int=0, message_when_purchased:str=None):
        await ctx.defer(hidden=True)
        
        time_in_seconds = int(await self.client.format_duration(availability_duration))
        
        if time_in_seconds < 600:
            return await ctx.send("It should atleast be 10 minutes in the store.", hidden=True)

        if not role_to_receive and item_category == "roles":
            return await ctx.send("You must specify the role_to_receieve parameter if the item category is '💬 Chat Roles'", hidden=True)
            
        new_item = {
            "name": item_name,
            "desc": item_description,
            "price": price,
            "stock": stock_amount,
            "category": item_category,
            "show_in_inv": show_in_inv,
            "best_before": time_in_seconds,
            "role_to_receive": role_to_receive.id if role_to_receive else role_to_receive,
            "role_to_remove": role_to_remove.id if role_to_remove else role_to_remove,
            "min_balance": min_balance,
            "reply_msg": message_when_purchased
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


    # @commands.command(aliases=["item-info"])
    # async def iteminfo(self, ctx, *, name):
    #     if isinstance(name, list):
    #         name = " ".join(name)
    #     found = False
    #     for key in self.shopdata.keys():
    #         if name.lower() in key.lower():
    #             itemdata = self.shopdata[key]
    #             found = True
    #             break

    #     if found is False:
    #         userdata = await self.check_user(ctx.author.id)
    #         for item in userdata["inventory"]:
    #             if name.lower() in item["name"].lower():
    #                 itemdata = item
    #                 found = True
    #                 break

    #     if found is False:
    #         await ctx.send("Was not able to find that item.")
    #         return

    #     embed = discord.Embed(title=f"Item Info", color=0x8b46d3)

    #     embed.add_field(name=f"Name",
    #                     value=f"{itemdata['name']}", inline=True)

    #     embed.add_field(name=f"Price",
    #                     value=f"{itemdata['price']}", inline=True)

    #     embed.add_field(name=f"Description",
    #                     value=f"{itemdata['description']}", inline=True)

    #     embed.add_field(name=f"Show in inventory",
    #                     value=f"{itemdata['show_in_inventory']}", inline=True)

    #     if itemdata['in_store_time'] is not None:
    #         embed.add_field(name=f"Time remaining",
    #                         value=f"<t:{itemdata['in_store_time']}:R>", inline=True)

    #     if itemdata["in_store_time"] is None:
    #         embed.add_field(name=f"Time remaining",
    #                         value=f"Infinite", inline=True)

    #     if itemdata["stock"] is None:
    #         embed.add_field(name=f"Stock remaining",
    #                         value=f"Infinite", inline=True)

    #     if itemdata["stock"] is not None:
    #         embed.add_field(name=f"Stock remaining",
    #                         value=f"{itemdata['stock']}", inline=True)

    #     if itemdata["requiredrole"] is not None:
    #         embed.add_field(name=f"Role required",
    #                         value=f"<@&{itemdata['requiredrole']}>", inline=True)

    #     if itemdata["requiredrole"] is None:
    #         embed.add_field(name=f"Role required",
    #                         value=f"{itemdata['requiredrole']}", inline=True)

    #     if itemdata["rolegiven"] is not None:
    #         embed.add_field(name=f"Role given",
    #                         value=f"<@&{itemdata['rolegiven']}>", inline=True)

    #     if itemdata["rolegiven"] is None:
    #         embed.add_field(name=f"Role given",
    #                         value=f"{itemdata['rolegiven']}", inline=True)

    #     if itemdata["roleremoved"] is not None:
    #         embed.add_field(name=f"Role removed",
    #                         value=f"<@&{itemdata['roleremoved']}>", inline=True)

    #     if itemdata["roleremoved"] is None:
    #         embed.add_field(name=f"Role removed",
    #                         value=f"{itemdata['roleremoved']}", inline=True)

    #     embed.add_field(name=f"Required balance",
    #                     value=f"{itemdata['required_coins_to_use']}", inline=True)

    #     embed.add_field(name=f"Reply message",
    #                     value=f"{itemdata['response_message']}", inline=True)

    #     embed.set_footer(text="TN | Economy",
    #                      icon_url=str(self.client.user.avatar_url_as(static_format='png', size=2048)))
    #     if itemdata["name"] == "🍅 Tomato 🍅":
    #         await ctx.message.delete()
    #         await ctx.send(embed=embed, delete_after=5)
    #     else:
    #         await ctx.send(embed=embed)

    # # noinspection PyUnboundLocalVariable
    # @commands.command(aliases=["buy-item"])
    # async def buyitem(self, ctx, *, name):
    #     if isinstance(name, list):
    #         name = " ".join(name)
    #     found = False
    #     for key in self.shopdata.keys():
    #         if name.lower() in key.lower():
    #             itemdata = self.shopdata[key].copy()
    #             found = True
    #             break
    #     if found is False:
    #         await ctx.send("Was not able to find that item.")
    #         return

    #     userdata = await self.check_user(ctx.author.id)

    #     memrolos = [i.id for i in ctx.author.roles]

    #     if itemdata["requiredrole"] is not None:
    #         if int(itemdata["requiredrole"]) not in memrolos:
    #             embed = discord.Embed(
    #                 description=f"**You need the role <@&{itemdata['requiredrole']}> to buy this item.**",
    #                 color=0x8b46d3)
    #             embed.set_footer(text="TN | Economy",
    #                              icon_url=str(self.client.user.avatar_url_as(static_format='png', size=2048)))
    #             await ctx.send(embed=embed)
    #             return

    #     if itemdata["stock"] is not None:
    #         if int(itemdata["stock"]) <= 0:
    #             await ctx.send(f"This item is out of stock.")
    #             return

    #     if itemdata["show_in_inventory"] is False:
    #         if itemdata["required_coins_to_use"] is not None:
    #             if userdata["wallet"] + userdata["bank"] < itemdata["required_coins_to_use"]:
    #                 await ctx.send(
    #                     f"You need atleast **__{await self.client.formatint(itemdata['required_coins_to_use'])}<a:miasmacoin:902351657361371188>__**")
    #                 return

    #         if itemdata["price"] > 0:
    #             price = int(itemdata["price"])
    #             if userdata["wallet"] - price < 0:
    #                 if (userdata["wallet"] + userdata["bank"]) - price < 0:
    #                     embed = discord.Embed(title="Economy",
    #                                           description=f"You don't got enough money to buy this item!",
    #                                           color=0x8b46d3)
    #                     embed.set_footer(text="TN | Economy",
    #                                      icon_url=str(self.client.user.avatar_url_as(static_format='png', size=2048)))
    #                     await ctx.send(embed=embed)
    #                     return
    #                 else:
    #                     pocketmoneyamount = userdata["wallet"]
    #                     self.client.economydata[str(ctx.author.id)]["wallet"] -= pocketmoneyamount
    #                     self.client.economydata[str(ctx.author.id)]["bank"] -= (price - pocketmoneyamount)

    #             else:
    #                 self.client.economydata[str(ctx.author.id)]["wallet"] -= price

    #         if itemdata["price"] < 0:
    #             self.client.economydata[str(ctx.author.id)]["wallet"] += abs(itemdata["price"])

    #         await self.log_money(ctx.author.mention, -itemdata["price"], f"Bought a {itemdata['name']}")

    #         if itemdata["stock"] is not None:
    #             self.shopdata[key]["stock"] -= 1

    #         guild = ctx.guild
    #         if itemdata["rolegiven"] is not None:
    #             guildrole = guild.get_role(int(itemdata["rolegiven"]))
    #             await ctx.author.add_roles(guildrole)

    #         if itemdata["roleremoved"] is not None:
    #             guildrole = guild.get_role(int(itemdata["roleremoved"]))
    #             await ctx.author.remove_roles(guildrole)

    #         await ctx.send(itemdata["response_message"])

    #     if itemdata["show_in_inventory"]:
    #         if itemdata["price"] > 0:
    #             price = int(itemdata["price"])
    #             if userdata["wallet"] - price < 0:
    #                 if (userdata["wallet"] + userdata["bank"]) - price < 0:
    #                     embed = discord.Embed(title="Economy",
    #                                           description=f"You don't got enough money to buy this item!",
    #                                           color=0x8b46d3)
    #                     embed.set_footer(text="TN | Economy",
    #                                      icon_url=str(self.client.user.avatar_url_as(static_format='png', size=2048)))
    #                     await ctx.send(embed=embed)
    #                     return
    #                 else:
    #                     pocketmoneyamount = userdata["wallet"]
    #                     self.client.economydata[str(ctx.author.id)]["wallet"] -= pocketmoneyamount
    #                     self.client.economydata[str(ctx.author.id)]["bank"] -= (price - pocketmoneyamount)

    #             else:
    #                 self.client.economydata[str(ctx.author.id)]["wallet"] -= price

    #         if itemdata["price"] < 0:
    #             self.client.economydata[str(ctx.author.id)]["wallet"] += abs(itemdata["price"])

    #         if itemdata["stock"] is not None:
    #             self.shopdata[key]["stock"] -= 1

    #         self.client.economydata[str(ctx.author.id)]["inventory"].append(itemdata)
    #         await ctx.send(
    #             f"Added {itemdata['name']} to your inventory do {const.prefix}use to use the item or {const.prefix}inventory to see your items.")
    #         if const.logging["inventory_usage"]:
    #             channel = self.guild.get_channel(const.logchannelid)
    #             embed = discord.Embed(title="User used inventory",
    #                                   description=f"Username: {ctx.author.mention}\nItem received: {itemdata['name']}",
    #                                   color=0x8b46d3)
    #             embed.set_footer(text="TN | Economy",
    #                              icon_url=str(self.client.user.avatar_url_as(static_format='png', size=2048)))
    #             await channel.send(embed=embed)
    #         return

    # @commands.command(aliases=["delete-item"])
    # async def deleteitem(self, ctx, *, name):
    #     memrolos = [i.id for i in ctx.author.roles]
    #     allowed = False
    #     for deleteitemallowed in const.deleitem:
    #         if deleteitemallowed in memrolos:
    #             allowed = True
    #             break

    #     if allowed is False:
    #         await ctx.send("You are not allowed to use that command.😐")
    #         return

    #     if isinstance(name, list):
    #         name = " ".join(name)

    #     for key in self.shopdata.keys():
    #         if name.lower() in key.lower():
    #             del self.shopdata[key]

    #             embed = discord.Embed(description=f"**Deleted {name}**",
    #                                   color=0x8b46d3)
    #             embed.set_footer(text="TN | Economy",
    #                              icon_url=str(self.client.user.avatar_url_as(static_format='png', size=2048)))

    #             await ctx.send(embed=embed)
    #             return
    #     await ctx.send("Was not able to find that item.")
    #     return

    # @commands.command()
    # async def editshop(self, ctx, *, string):
    #     memrolos = [i.id for i in ctx.author.roles]
    #     allowed = False
    #     for edititemallowed in const.editshop:
    #         if edititemallowed in memrolos:
    #             allowed = True
    #             break

    #     if allowed is False:
    #         await ctx.send("You are not allowed to use that command.😐")
    #         return

    #     try:
    #         name, what, new = string.split("|")
    #     except:
    #         await ctx.send("That doesn't appear to be right.")
    #         return

    #     for key in self.shopdata.copy().keys():
    #         if name.lower() in key.lower():
    #             if what == "price":
    #                 try:
    #                     self.shopdata[key]["price"] = int(new)
    #                 except ValueError:
    #                     await ctx.send("That last argument doesn't appear to be a integer")
    #                     return
    #             elif what == "description":
    #                 self.shopdata[key]["description"] = new
    #             elif what == "reply":
    #                 self.shopdata[key]["response_message"] = new
    #             elif what == "reqbalance":
    #                 if new == "none":
    #                     self.shopdata[key]["required_coins_to_use"] = None
    #                 else:
    #                     try:
    #                         self.shopdata[key]["required_coins_to_use"] = int(new)
    #                     except ValueError:
    #                         await ctx.send("That last argument doesn't appear to be a integer")
    #                         return

    #             elif what == "ininv":
    #                 if new.lower() == "yes" or new.lower() == "true":
    #                     new = True
    #                 elif new.lower() == "no" or new.lower() == "false":
    #                     new = False
    #                 else:
    #                     await ctx.send("yes or no pls.")
    #                     return
    #                 self.shopdata[key]["show_in_inventory"] = new

    #             elif what == "name":
    #                 data = self.shopdata.pop(key)
    #                 self.shopdata[new] = data
    #                 self.shopdata[new]["name"] = new
    #                 key = new

    #             elif what == "stock":
    #                 if new == "none" or new == "infinity" or new == "infinite":
    #                     self.shopdata[key]["stock"] = None
    #                 else:
    #                     try:
    #                         self.shopdata[key]["stock"] = int(new)
    #                     except ValueError:
    #                         await ctx.send("That last argument doesn't appear to be a integer")
    #                         return
    #             elif what == "rolegive":
    #                 if new == "none":
    #                     self.shopdata[key]["rolegiven"] = None
    #                 else:
    #                     try:
    #                         role = str(new).replace("<@&", "").replace(">", "")
    #                         ctx.guild.get_role(int(role))
    #                     except:
    #                         await ctx.send(":x: Invalid role given. Please try again or type cancel to exit.")
    #                         return
    #                     self.shopdata[key]["rolegiven"] = int(role)

    #             elif what == "roleremove":
    #                 if new == "none":
    #                     self.shopdata[key]["roleremoved"] = None
    #                 else:
    #                     try:
    #                         role = str(new).replace("<@&", "").replace(">", "")
    #                         ctx.guild.get_role(int(role))
    #                     except:
    #                         await ctx.send(":x: Invalid role given. Please try again or type cancel to exit.")
    #                         return
    #                     self.shopdata[key]["roleremoved"] = int(role)

    #             elif what == "rolerequired":
    #                 if new == "none":
    #                     self.shopdata[key]["requiredrole"] = None
    #                 else:
    #                     try:
    #                         role = str(new).replace("<@&", "").replace(">", "")
    #                         ctx.guild.get_role(int(role))
    #                     except:
    #                         await ctx.send(":x: Invalid role given. Please try again or type cancel to exit.")
    #                         return
    #                     self.shopdata[key]["requiredrole"] = int(role)

    #             elif what == "timeremaining":
    #                 if new == "none":
    #                     self.shopdata[key]["in_store_time"] = None
    #                 else:
    #                     timeinseconds = await self.client.duration_formatting(new)
    #                     if timeinseconds < 600:
    #                         await ctx.send("Should atleast be 10m")
    #                         return
    #                     self.shopdata[key]["in_store_time"] = int(timeinseconds) + int(time.time())
    #             else:
    #                 await ctx.send("Your second argument is wrong.")
    #                 return

    #     await ctx.send(f"Updated {name}'s {what} to {new}")



    # @commands.command(aliases=["inv"])
    # async def inventory(self, ctx, member=None):

    #     if member is None:
    #         member = str(ctx.author.id)

    #     if const.logging["inventory_usage"]:
    #         channel = self.guild.get_channel(const.logchannelid)
    #         embed = discord.Embed(title="User used inventory", description=f"Username: {ctx.author.mention}",
    #                               color=0x8b46d3)
    #         embed.set_footer(text="TN | Economy",
    #                          icon_url=str(self.client.user.avatar_url_as(static_format='png', size=2048)))
    #         await channel.send(embed=embed)

    #     if member == "secret":
    #         userdata = await self.check_user(ctx.author.id)
    #         for item in userdata["inventory"]:
    #             if item["name"] == "🍅 Tomato 🍅":
    #                 await ctx.message.delete()
    #                 embed = discord.Embed(title=f"{ctx.author.name}'s **SECRET** Inventory",
    #                                       description=f"Use an item with the `{const.prefix}use <name>` command.\n"
    #                                                   f"For more information on an item use the `{const.prefix}iteminfo <name>` command.",
    #                                       color=0x8b46d3)

    #                 embed.set_footer(text="TN | Economy",
    #                                  icon_url=str(self.client.user.avatar_url_as(static_format='png', size=2048)))
    #                 embed.add_field(name=item['name'],
    #                                 value=f"{item['description']}", inline=False)
    #                 await ctx.send(embed=embed, delete_after=5)
    #                 return

    #     try:
    #         guild = ctx.guild
    #         discordid = member.replace("<@!", "").replace(">", "").replace("<@", "")
    #         discorduser = guild.get_member(int(discordid))
    #     except ValueError:
    #         await ctx.send("That is not a valid member.")
    #         return

    #     if discorduser is None:
    #         await ctx.send("That is not a valid member.")
    #         return

    #     if self.client.user == discorduser:
    #         await ctx.send("I'm not even a real person <:angrypepe:878257251020849212>")
    #         return

    #     userdata = await self.check_user(discorduser.id)

    #     embed = discord.Embed(title=f"{discorduser.name}'s Inventory",
    #                           description=f"Use an item with the `{const.prefix}use <name>` command.\n"
    #                                       f"For more information on an item use the `{const.prefix}iteminfo <name>` command.",
    #                           color=0x8b46d3)

    #     embed.set_footer(text="TN | Economy",
    #                      icon_url=str(self.client.user.avatar_url_as(static_format='png', size=2048)))

    #     inventory = sorted(userdata["inventory"], key=lambda x: x["price"], reverse=False)
    #     count = 0
    #     gotenbefore = []
    #     for itemdata in inventory:
    #         found = False
    #         for itemdata1 in gotenbefore:
    #             if itemdata["name"] == itemdata1["name"]:
    #                 itemdata1["count"] += 1
    #                 found = True
    #         if found is False:
    #             itemdata["count"] = 1
    #             gotenbefore.append(itemdata)

    #     for itemdata in gotenbefore:
    #         if itemdata['name'] != "🍅 Tomato 🍅":
    #             embed.add_field(
    #                 name=f"{itemdata['count']}x <a:miasmacoin:902351657361371188>{await self.client.formatint(itemdata['price'])} - {itemdata['name']}",
    #                 value=f"{itemdata['description']}", inline=False)
    #             count += 1
    #     await ctx.send(embed=embed)

    # # noinspection PyUnboundLocalVariable
    # @commands.command()
    # async def use(self, ctx, *, name):
    #     if isinstance(name, list):
    #         name = " ".join(name)

    #     found = False
    #     userdata = await self.check_user(ctx.author.id)
    #     for item in userdata["inventory"]:
    #         if name.lower() in item["name"].lower():

    #             if item["required_coins_to_use"] is not None:
    #                 if userdata["wallet"] + userdata["bank"] < item["required_coins_to_use"]:
    #                     await ctx.send(
    #                         f"You need atleast **__{await self.client.formatint(item['required_coins_to_use'])}<a:miasmacoin:902351657361371188>__** to use this item.")
    #                     return

    #             itemdata = self.client.economydata[str(ctx.author.id)]["inventory"].pop(userdata["inventory"].index(item))
    #             found = True
    #             break

    #     if found is False:
    #         await ctx.send("Was not able to find that item.")
    #         return

    #     guild = ctx.guild
    #     if itemdata["rolegiven"] is not None:
    #         guildrole = guild.get_role(int(itemdata["rolegiven"]))
    #         await ctx.author.add_roles(guildrole)

    #     if itemdata["roleremoved"] is not None:
    #         guildrole = guild.get_role(int(itemdata["roleremoved"]))
    #         await ctx.author.remove_roles(guildrole)

    #     await ctx.send(itemdata["response_message"])

    #     if const.logging["inventory_usage"]:
    #         channel = self.guild.get_channel(const.logchannelid)
    #         embed = discord.Embed(title="User used item",
    #                               description=f"Username: {ctx.author.mention}\nItem used: {itemdata['name']}",
    #                               color=0x8b46d3)
    #         embed.set_footer(text="TN | Economy",
    #                          icon_url=str(self.client.user.avatar_url_as(static_format='png', size=2048)))
    #         await channel.send(embed=embed)


    # @commands.command()
    # async def giveitem(self, ctx, member=None, *, itemname=None):
    #     if isinstance(itemname, list):
    #         itemname = " ".join(itemname)

    #     if itemname is None:
    #         await ctx.send("You didn't specify a item.")

    #     if member is None:
    #         await ctx.send("You didn't specify a member.")
    #         return

    #     try:
    #         guild = ctx.guild
    #         discordid = member.replace("<@!", "").replace(">", "").replace("<@", "")
    #         discorduser = guild.get_member(int(discordid))
    #     except ValueError:
    #         await ctx.send("That is not a valid member.")
    #         return

    #     if discorduser is None:
    #         await ctx.send("That is not a valid member.")
    #         return

    #     if self.client.user == discorduser:
    #         await ctx.send("I'm not even a real person <:angrypepe:878257251020849212>")
    #         return

    #     memberdata = await self.check_user(discorduser.id)

    #     userdata = await self.check_user(ctx.author.id)

    #     found = False
    #     for item in userdata["inventory"]:
    #         if itemname.lower() in item["name"].lower():
    #             itemdata = self.client.economydata[str(ctx.author.id)]["inventory"].pop(userdata["inventory"].index(item))
    #             self.client.economydata[str(discorduser.id)]["inventory"].append(itemdata)
    #             found = True
    #             break

    #     if found is False:
    #         await ctx.send("Was not able to find that item.")
    #         return

    #     embed = discord.Embed(description=f"**{ctx.author.mention} Gave {discorduser.mention}:**",
    #                           color=0x8b46d3)

    #     embed.add_field(name=itemdata['name'],
    #                     value=f"{itemdata['description']}", inline=False)

    #     embed.set_footer(text="TN | Economy",
    #                      icon_url=str(self.client.user.avatar_url_as(static_format='png', size=2048)))
    #     await ctx.send(embed=embed)

    #     if const.logging["inventory_usage"]:
    #         channel = self.guild.get_channel(const.logchannelid)
    #         embed = discord.Embed(title="User give item",
    #                               description=f"Username: {ctx.author.mention}\nItem given: {itemdata['name']}\nReceiver: {discorduser.mention}",
    #                               color=0x8b46d3)
    #         embed.set_footer(text="TN | Economy",
    #                          icon_url=str(self.client.user.avatar_url_as(static_format='png', size=2048)))
    #         await channel.send(embed=embed)

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
    
