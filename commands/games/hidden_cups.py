import { CommandInteraction, MessageActionRow, MessageButton, MessageButtonStyleResolvable, MessageEmbed, Snowflake } from "discord.js";
import { generateId, shuffleArray } from "../util";
import chunk from 'chunk';
import UnbelievaboatClient from '../unbelievaboat-api';

/**
 * @param interaction The Discord interaction which triggered the command
 */
export default async function run (interaction: CommandInteraction, currentPlayers: Set<Snowflake>) {

    const member = await interaction.guild?.members.fetch(interaction.user.id)!;
    if (!member.roles.cache.has(process.env.DISCORD_CASINO_PREMIUM_ROLE_ID)) {
        interaction.followUp({
            embeds: [new MessageEmbed().setColor(process.env.EMBED_COLOR).setDescription(`To play this game you must have Casino Premium! Buy Casino Premium in the shop using !shop and !buy premium`)]
        });
        return;
    }

    const bet = interaction.options.getInteger('bet')!;

    if (bet < 100) {
        interaction.followUp({
            embeds: [new MessageEmbed().setColor(process.env.EMBED_COLOR).setDescription('You need to bet at least $100!')]
        });
        return;
    }

    const currentBalance = await UnbelievaboatClient.getUserBalance(process.env.DISCORD_GUILD_ID, interaction.user.id);
    if (currentBalance.cash < bet) {
        return void interaction.followUp({
            embeds: [new MessageEmbed().setColor(process.env.EMBED_COLOR).setDescription(`You need at least **$${bet}** cash to execute this game!`)]
        });
    }

    await UnbelievaboatClient.editUserBalance(process.env.DISCORD_GUILD_ID, interaction.user.id, {
        cash: -bet
    });

    currentPlayers.add(interaction.user.id);

    let gameEnded = false;
    let gameId = generateId();

    // 0 is 1/2 bet and hidden
    // 1 is 2x bet and hidden
    // 2 is loss and hidden
    // 3 is 1/2 bet and shown
    // 4 is 2x bet and shown
    // 5 is loss and shown
    const cups = shuffleArray([0, 1, 2]);

    const embed = new MessageEmbed()
        .setAuthor(`🏆 Hidden Cups`)
        .setDescription(`💵 Your bet: **$${bet}**\n\n📜 Game Rules 📜\n\nHere are 3 cups. Each cup contains a prize, good, bad, and kinda bad! You can win:\n- **1/2 of your bet**\n- **2x your bet**\n- **nothing**.\nYou have one attempt. Good luck and have fun!`)
        .setColor(process.env.EMBED_COLOR)
        .setFooter(process.env.EMBED_FOOTER);
    
    await interaction.followUp({
        content: '⌛ Your game is loading...'
    });

    const rebuildComponents = () => {
        const components = [
            new MessageActionRow()
                .addComponents(cups.map((cup, index) => {
                    return new MessageButton()
                        .setEmoji(cup === 3 ? '💔' : cup === 4 ? '💰' : cup === 5 ? '☠️' : '901981728221069342')
                        .setCustomId(`btn_${gameId}_${cup}_${index}`)
                        .setStyle('SECONDARY')
                }))
        ];
        interaction.editReply({
            content: null,
            embeds: [embed],
            components
        });
    }

    const collector = interaction.channel?.createMessageComponentCollector({
        filter: (collectedInteraction) => collectedInteraction.customId.startsWith(`btn_${gameId}`),
        time: 60*60_000
    });

    collector?.on('collect', (collectedInteraction) => {

        if (collectedInteraction.user.id !== interaction.user.id) {
            return void collectedInteraction.reply({
                ephemeral: true,
                content: 'You can not interact with this game. Please start your own to do so!'
            });
        }

        const [_btn, _gameId, _status, _index] = collectedInteraction.customId.split('_');
        const status = parseInt(_status);
        const index = parseInt(_index);

        if (gameEnded) {
            return void collectedInteraction.reply({
                ephemeral: true,
                content: 'This game has been ended. Please start a new one!'
            });
        }

        if (status === 0) {
            currentPlayers.delete(interaction.user.id);
            cups[index] = 3;
            gameEnded = true;
            const message = '💔 You have lost half of your bet';
            embed.setTitle(message);
            collectedInteraction.reply({
                embeds: [new MessageEmbed().setColor(process.env.EMBED_COLOR).setDescription(message)]
            });
            rebuildComponents();
            UnbelievaboatClient.editUserBalance(process.env.DISCORD_GUILD_ID, interaction.user.id, {
                cash: Math.ceil(bet/2)
            });
        }

        if (status === 1) {
            currentPlayers.delete(interaction.user.id);
            cups[index] = 4;
            gameEnded = true;
            const message = '💰 You have won 2x your bet!';
            embed.setTitle(message);
            collectedInteraction.reply({
                embeds: [new MessageEmbed().setColor(process.env.EMBED_COLOR).setDescription(message)]
            });
            rebuildComponents();
            UnbelievaboatClient.editUserBalance(process.env.DISCORD_GUILD_ID, interaction.user.id, {
                cash: bet*2
            });
        }

        if (status === 2) {
            currentPlayers.delete(interaction.user.id);
            cups[index] = 5;
            gameEnded = true;
            const message = '☠️ You have lost all your bet...';
            embed.setTitle(message);
            collectedInteraction.reply({
                embeds: [new MessageEmbed().setColor(process.env.EMBED_COLOR).setDescription(message)]
            });
            rebuildComponents();
        }

    });

    collector?.on('end', async (_collected, reason) => {
        if (reason === 'time') {
            embed.setTitle('⏲️ Game ended due to inactivity');
            gameEnded = true;
            currentPlayers.delete(interaction.user.id);
            rebuildComponents();
            await UnbelievaboatClient.editUserBalance(process.env.DISCORD_GUILD_ID, interaction.user.id, {
                cash: bet
            });
        }
    });

    setTimeout(() => {
        rebuildComponents();
    }, 500);

}
