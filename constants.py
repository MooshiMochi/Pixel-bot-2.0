import os

class Constants:
    def __init__(self):
        self.prefix = "?"
        self.DEBUG = False
        
        self.PIXEL_TEST = 932736074139185292
        self.TITAN_MC = 932413718397083678
        self.TITAN_EVENTS = 734890828698353704

        if os.getlogin() == "Administrator":
            self.guild_id = self.TITAN_MC
        else:
            self.guild_id = self.PIXEL_TEST
        self.emotes_guild_id = self.PIXEL_TEST
        self.slash_guild_ids = [] #self.guild_id,  734890828698353704

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
            'commands.raffle',
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
            'commands.games.riddles',
            'commands.games.coin_flip',
            'commands.games.buried_treasure',
            'commands.games.hidden_cups',
            'commands.games.tic_tac_toe',
            'commands.games.four_corners')

const = Constants()
