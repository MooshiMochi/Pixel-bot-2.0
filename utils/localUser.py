from typing import Union

from discord import TextChannel, VoiceChannel

class LocalUser:
    def __init__(self, _id: int) -> None:
        self.__id = _id

    @property
    def avatar(self):
        self.avatar_url

    @property
    def avatar_url(self):
        return f"https://cdn.discordapp.com/attachments/934371943614914610/951187348245327932/unknown.png?size=1024"

    @property
    def bot(self):
        return False

    @property
    def color(self):
        return self.colour

    @property
    def colour(self):
        return 0xff0000

    @property
    def created_at(self):
        return "Unknown"

    @property
    def default_avatar(self):
        return None

    @property
    def default_avatar_url(self):
        return self.default_avatar

    @property
    def discriminator(self):
        return "????"

    @property
    def display_name(self):
        return self.name

    @property
    def dm_channel(self):
        return None

    @property
    def id(self):
        return self.__id

    @property
    def mention(self):
        return f"<@!{self.__id}>"

    @property
    def mutual_guilds(self):
        return None

    @property
    def name(self):
        return f"~~{self.__id}~~"

    @property
    def public_flags(self):
        return None

    @property
    def relationship(self):
        return None

    @property
    def system(self):
        return None

    def avatar_url_as(self, static_format:str="png", size:int=1024):
        return f"https://cdn.discordapp.com/attachments/934371943614914610/951187348245327932/unknown.{static_format}?size={size}"

    async def block(self):
        return None

    async def create_dm(self):
        return None

    async def fetch_message(self):
        return None

    def history(self):
        return None

    def is_avatar_animated(self):
        return False

    def is_blocked(self):
        return False

    def is_friend(self):
        return False

    def mentioned_in(self):
        return None

    async def mutual_friends(self):
        return None

    async def permissions_in(channel: Union[TextChannel, VoiceChannel]):
        return None

    async def pins(self):
        return None

    async def profile(self):
        return None

    async def remove_friend(self):
        return False

    async def trigger_typing(self):
        return False

    def typing(self):
        return False

    async def unblock(self):
        return False

    @property
    def roles(self):
        return []

    @property
    def status(self):
        return "offline"
    
    @property
    def raw_status(self):
        return self.status

    @property
    def mobile_status(self):
        return self.status

    @property
    def desktop_status(self):
        return self.status

    @property
    def web_status(self):
        return self.status

    @property
    def is_on_mobile(self):
        return False

    @property
    def activity(self):
        return None

    @property
    def top_role(self):
        return None

    @property
    def joined_at(self):
        return "Unknown"
