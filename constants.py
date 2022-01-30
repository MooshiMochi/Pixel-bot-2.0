class Constants:
    def __init__(self):
        self.prefix = "?"
        self.token = "OTMyNzM1NzQ0MTczMzAxODYx.YeXT2g.5ldJ5PxhZ0w-r0DEiUrOWjW31P8"
        
        self.guild_id = 932736074139185292

        self.log_channel_id = 934079085137764474

        self.rr_type_config = {
            0: "Remove and add roles (default).", 
            1: "Remove role only", 
            2: "Add role only", 
            3: "Can obtain only 1 role."
            }

        self.command_exts = (
            'commands.reaction_roles',
            'commands.restricted',
            'commands.verification',
            'commands.whack_a_steve',
            'commands.level_system',
            'commands.leaderboards')

const = Constants()
