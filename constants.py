class Constants:
    def __init__(self):
        self.prefix = "?"
        self.token = "OTMyNzM1NzQ0MTczMzAxODYx.YeXT2g.5ldJ5PxhZ0w-r0DEiUrOWjW31P8"
        self.unbelievaboattoken = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcHBfaWQiOiI4OTYxMDM2Nzg1ODU0NzMzMDYiLCJpYXQiOjE2MzM3MTg0MzB9.X4awbXMBOgUJW31WC5tq5wwMmPZviEe3hjDawuDknuM"
        
        self.guild_id = 932413718397083678
        self.emotes_guild_id = 932736074139185292
        self.slash_guild_ids = [self.guild_id, 892877446284738610, 932736074139185292]

        self.log_channel_id = 934079085137764474

        self.giveaway_ch_id = 932426258816565330

        self.rr_type_config = {
            0: "Remove and add roles (default).", 
            1: "Remove role only", 
            2: "Add role only", 
            3: "Can obtain only 1 role."
            }

        self.command_exts = (
            'commands.experimental',
            'commands.events_and_updates',
            'commands.counter',
            'commands.giveaways',
            'commands.reaction_roles',
            'commands.restricted',
            'commands.verification',
            'commands.level_system',
            'commands.leaderboards',
            'commands.misc',
            'commands.economy',
            'commands.suggestions',
            'commands.games.whack_a_brick',
            'commands.games.mc_madness',
            'commands.games.riddles')

const = Constants()
