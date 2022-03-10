import { CommandInteraction, MessageActionRow, MessageButton, MessageButtonStyleResolvable, MessageEmbed, Snowflake } from "discord.js";
import { generateId, shuffleArray } from "../util";
import chunk from 'chunk';
import UnbelievaboatClient from '../unbelievaboat-api';

/**
 * There are 25 squares on a map and you get 2 tries to click 3 out of the 25.
 * If you find the treasure, then whatever you "bet" on the game example !bt 1000 you would get 4x back.
 * This game is completely random but the stakes are great.
 */

const SQUARES = 25;
const SUCCESS = 3;

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
            embeds: [new MessageEmbed().setColor(process.env.EMBED_COLOR).setTitle(`You need at least **$${bet}** cash to execute this game!`)]
        });
    }

    await UnbelievaboatClient.editUserBalance(process.env.DISCORD_GUILD_ID, interaction.user.id, {
        cash: -bet
    });

    currentPlayers.add(interaction.user.id);

    let attempts = 0;
    let gameEnded = false;
    let gameId = generateId();

    // 0 is hidden AND false
    // 1 is hidden AND true
    // 2 is discovered AND true
    // 3 is discovered AND false
    let buttonStatuses: number[] = [];
    for (let i = 0; i < SQUARES; i++) {
        // add the beginning everything is 0 or 1, with 2 of the 15 buttons true
        buttonStatuses.push(i < SUCCESS ? 1 : 0);
    }
    buttonStatuses = shuffleArray(buttonStatuses);

    const embed = new MessageEmbed()
        .setAuthor(`🏝️ Buried Treasure`)
        .setDescription(`💵 Your bet: **$${bet}**\n\n📜 Game Rules 📜\n\n- You can click on 3 spots in the sand using the buttons below.\n- 3 of these spots contain treasure.\n- If you find one of the spots with treasure, your bet is multiplied by 4!\n- Good luck and have fun!`)
        .setColor(process.env.EMBED_COLOR)
        .setFooter(process.env.EMBED_FOOTER);
    
    const rebuildComponents = () => {
        const components: MessageActionRow[] = [];
        const buttons: MessageButton[] = [];

        buttonStatuses.forEach((status, index) => {
            let label = (status === 0 || status === 1) ? '🏝️' : status === 2 ? '💰' : '🏝️';
            let style: MessageButtonStyleResolvable = (status === 0 || status === 1) ? 'SECONDARY' : status === 2 ? 'SUCCESS' : 'DANGER'
            buttons.push(
                new MessageButton()
                    .setEmoji(label)
                    .setCustomId(`btn_${gameId}_${status}_${index}`)
                    .setStyle(style)
            );
        });

        const actions = chunk(buttons, 5);
        actions.forEach((action) => {
            components.push(
                new MessageActionRow()
                    .addComponents(action)
            )
        });

        return void interaction.editReply({
            content: null,
            embeds: [embed],
            components
        });
    }

    await interaction.followUp({
        content: '⌛ Your game is loading...'
    });

    const collector = interaction.channel?.createMessageComponentCollector({
        filter: (collectedInteraction) => collectedInteraction.customId.startsWith(`btn_${gameId}`),
        time: 60*60_000
    });

    collector?.on('collect', async (collectedInteraction) => {

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

        if (status === 2 || status === 3) {
            return void collectedInteraction.reply({
                ephemeral: true,
                content: 'You have already discovered this part of the island!'
            });
        }

        if (status === 0) {
            attempts++;
            buttonStatuses[index] = 3;
            if (attempts === SUCCESS) {
                embed.setTitle('😢 Game lost...');
                gameEnded = true;
                currentPlayers.delete(interaction.user.id);
            }
            rebuildComponents();
            setTimeout(() => {
                collector.stop();
            }, 10 * 60_000);
            return void collectedInteraction.reply({
                embeds: [new MessageEmbed().setColor(process.env.EMBED_COLOR).setDescription('🏝️ Unfortunately this part of this island did not include a treasure!' + (gameEnded ? '\n🤞 The game is over. Good luck next time!' : `\nYou have **${SUCCESS - attempts}** more attempts to find the treasure!`))]
            });
        }

        if (status === 1) {
            buttonStatuses[index] = 2;
            embed.setTitle('💰 Game won!');
            gameEnded = true;
            currentPlayers.delete(interaction.user.id);
            rebuildComponents();
            setTimeout(() => {
                collector.stop();
            }, 10 * 60_000);
            await UnbelievaboatClient.editUserBalance(process.env.DISCORD_GUILD_ID, interaction.user.id, {
                cash: bet*3
            });
            return void collectedInteraction.reply({
                embeds: [new MessageEmbed().setColor(process.env.EMBED_COLOR).setDescription(`💰 Congrats! This part of the island included a treasure! You won **$${bet*4}**!`)]
            });
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
