from typing import Union

import discord
from discord.ext import commands

from ...config import config
from ..character.character import Character


class FightSession:
    def __init__(
        self,
        ctx: commands.Context,
        initiator_char: Character,
        opponent: Union[discord.Member, discord.User],
        opponent_char: Character,
    ):
        self.ctx = ctx
        self.initiator = ctx.author
        self.initiator_char = initiator_char
        self.opponent = opponent
        self.opponent_char = opponent_char
        self._task = None
        self.embed = discord.Embed(
            title="Бой", colour=discord.Colour(0xC20000)
        )
        self.embed.set_author(name=config.bot.name, icon_url=config.bot.icon_url)
        self.embed.set_footer(text="Создание персонажа")
        self.message = None

    @classmethod
    def start(
        cls,
        ctx: commands.Context,
        initiator_char: Character,
        opponent: Union[discord.Member, discord.User],
        opponent_char: Character,
    ):
        """Creates and starts fight session.

        This allows the session to manage the running and cancellation of its
        own tasks.

        Args:
            ctx (commands.Context): Same as `FightSession.ctx`
            initiator_char (Character): Initiator's character
            opponent (Union[discord.Member, discord.User]): Opponent member object
            opponent_char (Character): Opponent's character

        Returns:
            FightSession: The new fight session being run.

        """
        fight = cls(ctx, initiator_char, opponent, opponent_char)
        return fight
