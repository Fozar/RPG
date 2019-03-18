import asyncio
import inspect
import random
import re
from itertools import cycle
from operator import itemgetter
from typing import Union

import discord
from mongoengine import Document, connect
from redbot.core import checks
from redbot.core.bot import Red
from redbot.core.commands import commands
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS, close_menu
from redbot.core.utils.predicates import MessagePredicate

from .data.character.attributes import Attributes
from .data.character.character import Character, CharacterNotFound
from .data.character.equipment import Equipment, ItemIsNotEquippable, ItemNotFoundInEquipment
from .data.character.inventory import Inventory, ItemNotFoundInInventory
from .data.item.item import Item, ItemNotFound
from .config import config
from .data.session.register_char_session import RegisterSession

Cog = getattr(commands, "Cog", object)


class RPG(Cog):
    """RPG Cog"""

    def __init__(self, bot: Red):
        self.Red = bot
        self.ItemClass = Item
        self.CharacterClass = Character
        self.InventoryClass = Inventory
        self.AttributesClass = Attributes
        self.EquipmentClass = Equipment
        self.register_sessions = []
        self.Red.loop.create_task(self.setup())
        self.Red.loop.create_task(self.change_status())

    async def setup(self):
        await self.Red.wait_until_ready()

        connect(
            db=config.database.db,
            host=config.database.host,
            port=config.database.port,
            username=config.database.user,
            password=config.database.password,
        )

    async def change_status(self):
        """Changes the bot status through random time.

        The time can be changed in the config in the `bot` section.
        status_change_min in minimum time. status_change_max - maximum.

        """
        await self.Red.wait_until_ready()
        _config = config.bot
        status = _config.statuses[:]
        random.shuffle(status)
        statuses = cycle(status)

        while not self.Red.is_closed():
            status = (
                self.Red.guilds[0].me.status
                if len(self.Red.guilds) > 0
                else discord.Status.online
            )
            activity = discord.Activity(
                name=next(statuses), type=discord.ActivityType.watching
            )
            await self.Red.change_presence(status=status, activity=activity)
            await asyncio.sleep(
                random.randint(_config.status_change_min, _config.status_change_max)
            )

    async def update_chars(self):
        await self.Red.wait_until_ready()
        timer = 5
        while not self.Red.is_closed():
            # Attributes regeneration
            chars = self.CharacterClass.objects
            for char in chars:
                char.attributes.mod_value(
                    "health",
                    char.attributes.main["health_max"]
                    * char.attributes.main["health_regen"]
                    * timer
                    / 100,
                )
                char.attributes.mod_value(
                    "stamina",
                    char.attributes.main["stamina_max"]
                    * char.attributes.main["stamina_regen"]
                    * timer
                    / 100,
                )
                char.attributes.mod_value(
                    "magicka",
                    char.attributes.main["magicka_max"]
                    * char.attributes.main["magicka_regen"]
                    * timer
                    / 100,
                )
                char.save()
            await asyncio.sleep(timer)

    @commands.group(invoke_without_command=True, aliases=["char", "персонаж", "перс"])
    async def character(self, ctx, member: Union[discord.Member, discord.User] = None):
        """Информация о персонаже"""

        author = ctx.author
        if member is None:
            member = author
        member_id = str(member.id)
        try:
            char = self.get_char_by_id(member_id)
        except CharacterNotFound:
            await ctx.send(f"{author.mention}, персонаж не найден.")
            await ctx.send_help()
            return

        embed = discord.Embed(
            title=f"{char.name}",
            colour=discord.Colour(0xF5A623),
            description=f"{char.desc}",
        )
        embed.set_author(name=config.bot.name, icon_url=config.bot.icon_url)
        if char.avatar:
            embed.set_thumbnail(url=char.avatar)
        embed.set_footer(text="Информация о персонаже")

        embed.add_field(name="Раса", value=config.humanize.races[char.race].title())
        embed.add_field(name="Пол", value=config.humanize.genders[char.sex].title())
        embed.add_field(
            name="Здоровье",
            value=f"{int(char.attributes.health)}/{int(char.attributes.get_total_value('health'))}",
        )
        embed.add_field(name="Уровень", value=char.lvl)
        embed.add_field(name="Опыт", value=char.xp)
        embed.add_field(name="Множитель опыта", value=char.xp_factor)

        await ctx.send(embed=embed)

    @character.command(name="new", aliases=["новый"])
    async def char_new(self, ctx):
        """Создать персонажа"""

        author = ctx.author

        if self.CharacterClass.is_member_registered(str(author.id)):
            await ctx.send(
                f"{author.mention}, у вас уже есть персонаж. "
                f"Введите `{ctx.prefix}char delete`, чтобы удалить его."
            )
            return
        session = self._get_register_session(ctx.author)
        if session is not None:
            return
        session = RegisterSession.start(ctx)
        self.register_sessions.append(session)

    @character.command(name="cancel", aliases=["отмена"])
    async def char_cancel(self, ctx):
        """Отменить регистрацию персонажа"""
        session = self._get_register_session(ctx.author)
        if session is None:
            return
        author = ctx.author
        if author == session.ctx.author:
            await session.cancel()
            session.force_stop()

    @character.command(name="delete", aliases=["del", "удалить"])
    async def char_delete(self, ctx):
        """Удалить персонажа"""

        author = ctx.author
        member_id = str(author.id)

        if not self.CharacterClass.is_member_registered(member_id):
            await ctx.send(
                f"{author.mention}, у вас нет персонажа. "
                f"Введите `{ctx.prefix}char new`, чтобы создать"
            )
            return

        await ctx.send(
            f"{author.mention}, вы уверены, что хотите удалить своего персонажа?\n"
            "\n"
            "ВНИМАНИЕ: Это действие нельзя отменить. Все ваши предметы, уровень и достижения будут "
            "потеряны безвозвратно."
        )

        try:
            msg = await self.Red.wait_for(
                "message", timeout=30.0, check=MessagePredicate.same_context(ctx)
            )
        except asyncio.TimeoutError:
            await ctx.send(f"{author.mention}, удаление персонажа отменено.")
            return
        if msg.content.lower() in ["да", "д", "yes", "y"]:
            self.CharacterClass.objects(member_id=member_id).delete()
            await ctx.send(
                f"{author.mention}, ваш персонаж удален. "
                f"Введите `{ctx.prefix}char new`, чтобы создать нового."
            )
        else:
            await ctx.send(f"{author.mention}, удаление персонажа отменено.")

    @commands.group(aliases=["inv", "инвентарь", "инв"], invoke_without_command=True)
    async def inventory(self, ctx, member: Union[discord.Member, discord.User] = None):
        """Инвентарь персонажа"""

        author = ctx.author
        if member is None:
            member = author

        try:
            char = self.get_char_by_id(str(member.id))
        except CharacterNotFound:
            await ctx.send(f"{author.mention}, персонаж не найден.")
            return

        if char.inventory.is_inventory_empty():
            _embed = discord.Embed(
                title=f"Инвентарь персонажа {char.name}",
                colour=discord.Colour(0x8B572A),
                description=f"Инвентарь пуст.",
            )
            await ctx.send(embed=_embed)
            return

        pages = []
        for category, name in config.humanize.inventory.inv_categories.items():
            items = char.inventory.items[category]
            if not items:
                continue
            item_stats = []
            for item in items:
                count = item["count"]
                if item and count > 0:
                    try:
                        _item = self.get_item_by_id(item["item_id"])
                        stats = {**{"count": count}, **dict(_item.to_mongo())}
                        if item["maker"]:
                            stats["maker"] = item["maker"]
                        if item["temper"]:
                            stats["temper"] = item["temper"]
                        item_stats.append(stats)
                    except ItemNotFound:
                        print(
                            f"Item ID: {item['item_id']} not found. Member ID: {member.id}"
                        )
                else:
                    break
            else:
                item_stats[:] = sorted(item_stats, key=itemgetter("name"))
                embed = discord.Embed(
                    title=f"Инвентарь персонажа {char.name}",
                    colour=discord.Colour(0x8B572A),
                    description=f"**```fix\n[{name.upper()}] ({len(item_stats)})\n```**",
                )
                embed.set_author(name=config.bot.name, icon_url=config.bot.icon_url)
                embed.set_footer(text="Инвентарь персонажа")
                for stats in item_stats:
                    text = "```autohotkey\n"
                    for stat, _name in config.humanize.inventory.inv_stats.items():
                        if stat in stats:
                            text += f"{_name.title()}: {stats[stat]}\n"
                    text += "```"
                    embed.add_field(
                        name=f"{stats['name']} ({stats['count']})",
                        value=text,
                        inline=True,
                    )
                pages.append(embed)
        if len(pages) > 1:
            await menu(ctx, pages, DEFAULT_CONTROLS)
        elif len(pages) == 1:
            await menu(ctx, pages, {"❌": close_menu})

    @checks.admin_or_permissions()
    @inventory.command(name="add", pass_context=True, aliases=["выдать"])
    async def inventory_add(
        self,
        ctx,
        member: Union[discord.Member, discord.User],
        count,
        item_name,
        maker=None,
        temper=None,
    ):
        """Выдать предмет персонажу"""

        author = ctx.author
        member_id = str(member.id)

        try:
            char = self.get_char_by_id(member_id)
        except CharacterNotFound:
            await ctx.send(f"{author.mention}, персонаж не найден.")
            return

        try:
            _item = await self.get_item_by_name(ctx, item_name)
        except ItemNotFound:
            await ctx.send(f"{author.mention}, предмет не найден.")
            return

        if temper:
            temper = int(temper)
        char.inventory.add_item(_item, int(count), maker, temper)
        char.save()
        await ctx.send(f"{author.mention}, предмет(ы) добавлен(ы).")

    @checks.admin_or_permissions()
    @inventory.command(name="remove", pass_context=True, aliases=["забрать"])
    async def inventory_remove(
        self, ctx, member: Union[discord.Member, discord.User], count, item_name
    ):
        """Удалить предмет у персонажа"""

        author = ctx.author

        try:
            char = self.get_char_by_id(str(member.id))
        except CharacterNotFound:
            await ctx.send(f"{author.mention}, персонаж не найден.")
            return

        try:
            _item = await self.get_item_by_name(ctx, item_name)
        except ItemNotFound:
            await ctx.send(f"{author.mention}, предмет не найден.")
            return

        try:
            items = char.inventory.get_items(_item)
            if len(items) > 1:
                item = await self.item_select(ctx, _item, items)
            elif len(items) == 1:
                item = items[0]
            else:
                raise ItemNotFoundInInventory
            char.inventory.remove_item(_item, int(count), item["maker"], item["temper"])
            char.save()
            await ctx.send(f"{author.mention}, предмет(ы) удален(ы).")
        except ItemNotFoundInInventory:
            await ctx.send(f"{author.mention}, предмет не найден в инвентаре.")

    @inventory.command(name="equipment", aliases=["eqpt", "снаряжение"])
    async def inventory_equipment(
        self, ctx, member: Union[discord.Member, discord.User] = None
    ):
        """Снаряжение персонажа"""

        author = ctx.author
        if member is None:
            member = author
        try:
            char = self.get_char_by_id(str(member.id))
        except CharacterNotFound:
            await ctx.send(f"{author.mention}, персонаж не найден.")
            return
        embed = discord.Embed(
            title=f"Снаряжение персонажа {char.name}", colour=discord.Colour(0x8B572A)
        )

        embed.set_author(name=config.bot.name, icon_url=config.bot.icon_url)
        embed.set_footer(text="Снаряжение персонажа")

        for slot, item in char.equipment.to_mongo().items():
            if not item:
                value = "Пусто"
            else:
                value = self.get_item_by_id(item["item_id"]).name
            embed.add_field(
                name=config.humanize.inventory.equipment[slot].capitalize(),
                value=value,
                inline=True,
            )

        await ctx.send(embed=embed)

    @inventory.command(name="equip", aliases=["экипировать", "надеть"])
    async def inventory_equip(self, ctx, item_name: str):
        """Экипировать предмет"""

        author = ctx.author
        try:
            char = self.get_char_by_id(str(author.id))
        except CharacterNotFound:
            await ctx.send(f"{author.mention}, персонаж не найден.")
            return

        try:
            _item = await self.get_item_by_name(ctx, item_name)
        except ItemNotFound:
            await ctx.send(f"{author.mention}, предмет не найден.")
            return

        try:
            items = char.inventory.get_items(_item)
            if len(items) > 1:
                item = await self.item_select(ctx, _item, items)
            elif len(items) == 1:
                item = items[0]
            else:
                raise ItemNotFoundInInventory
            self.equip_item(char, item)
            char.save()
            await ctx.send(f"{author.mention}, предмет экипирован.")
        except ItemNotFoundInInventory:
            await ctx.send(f"{author.mention}, предмет не найден в инвентаре.")
        except ItemIsNotEquippable:
            await ctx.send(f"{author.mention}, предмет не может быть экипирован.")

    @inventory.command(name="unequip", aliases=["снять"])
    async def inventory_unequip(self, ctx, item_name: str):
        """Снять предмет"""

        author = ctx.author

        try:
            char = self.get_char_by_id(str(author.id))
        except CharacterNotFound:
            await ctx.send(f"{author.mention}, персонаж не найден.")
            return

        try:
            _item = await self.get_item_by_name(ctx, item_name)
        except ItemNotFound:
            await ctx.send(f"{author.mention}, предмет не найден.")
            return

        try:
            self.unequip_item(char, _item)
            char.save()
            await ctx.send(f"{author.mention}, предмет снят.")
        except ItemNotFoundInEquipment:
            await ctx.send(f"{author.mention}, предмет не найден в снаряжении.")

    @commands.group(invoke_without_command=True, aliases=["i", "предмет"])
    async def item(self, ctx, item_name):
        """Информация о предмете"""

        author = ctx.author
        try:
            _item = await self.get_item_by_name(ctx, item_name)
        except ItemNotFound:
            await ctx.send(f"{author.mention}, предмет не найден.")
            return

        color = discord.Colour(
            int(getattr(config.game.item_settings.colors, _item.rarity.lower()), 0)
        )
        embed = discord.Embed(
            title=f"{_item.name}", colour=color, description=f"*{_item.desc}*"
        )

        embed.set_author(name=config.bot.name, icon_url=config.bot.icon_url)
        embed.set_footer(text="Информация о предмете")
        for stat, name in config.humanize.inventory.inv_stats.items():
            if stat in _item:
                embed.add_field(
                    name=name.title(), value=f"{getattr(_item, stat)}", inline=True
                )

        await ctx.send(embed=embed)

    @checks.is_owner()
    @item.command(name="new", invoke_without_command=True, aliases=["новый"])
    async def item_new(
        self, ctx, item_type, item_name, description, price, rarity, *args
    ):
        """Добавить новый предмет

        *- item_type:* Тип предмета. Возможные значения: item/weapon/armor
        *- item_name:* Название предмета
        *- description:* Описание предмета
        *- price:* Стоимость предмета
        *- rarity:* Редкость предмета
        *- args:* Дополнительные аргументы для разных типов предметов.
            *-- Оружие:*
                *--- attack_type:* Тип атаки
                *--- hands:* Количество рук
                *--- type:* Тип оружия
                *--- material:* Материал оружия
                *--- damage:* Наносимый урон
            *-- Броня:*
                *--- slot:* Слот брони
                *--- kind:* Тип брони
                *--- material:* Материал оружия
                *--- armor:* Класс брони
        """

        item_id = self.ItemClass.get_next_id()

        new_item = globals()[item_type.title()](
            item_id=item_id,
            name=item_name,
            desc=description,
            price=price,
            rarity=rarity,
        )
        signature = list(inspect.getfullargspec(new_item.__init__).args)
        if args:
            args_len = len(signature) - len(args)
            for arg, value in zip(signature[args_len:], list(args)):
                setattr(new_item, arg, value)

        new_item.save()
        await ctx.send(f"{ctx.author.mention}, предмет создан!")

    @commands.command(aliases=["stats", "статы"])
    async def statistics(self, ctx, member: Union[discord.Member, discord.User] = None):
        """ Характеристики персонажа """

        author = ctx.author
        if member is None:
            member = author

        try:
            char = self.get_char_by_id(str(member.id))
        except CharacterNotFound:
            await ctx.send(f"{author.mention}, персонаж не найден.")
            return

        pages = []
        _config = config.humanize.attributes
        for category, name in _config.categories.items():
            embed = discord.Embed(
                title=f"Характеристики персонажа {char.name}",
                colour=discord.Colour(0xC7C300),
                description=f"```{name.upper()}```",
            )
            embed.set_author(name=config.bot.name, icon_url=config.bot.icon_url)
            embed.set_footer(text="Характеристики персонажа")
            if category == "main":
                for stat in ["magicka", "health", "stamina"]:
                    value = f"{int(getattr(char.attributes, stat))}/{int(char.attributes.get_total_value(stat))}"
                    embed.add_field(name=_config.stats[stat], value=value, inline=True)
                embed.add_field(
                    name="Класс брони",
                    value=f"{int(char.attributes.armor_rating)}",
                    inline=False,
                )
                embed.add_field(
                    name="Урон без оружия",
                    value=f"{int(char.attributes.unarmed_damage)}",
                    inline=False,
                )
            elif category == "resists":
                for resist in char.attributes.resists:
                    value = f"{int(-(char.attributes.resists[resist] - 1) * 100)}%"
                    embed.add_field(
                        name=_config.stats[resist], value=value, inline=True
                    )
            else:
                for skill in char.attributes.skills:
                    value = char.attributes.skills[skill]
                    embed.add_field(name=_config.stats[skill], value=value, inline=True)
            pages.append(embed)

        await menu(ctx, pages, DEFAULT_CONTROLS)

    async def on_register_end(self, session: RegisterSession):
        """Event for a registration session ending.

        This method removes the session from this cog's sessions, cancels
        any tasks which it was running, receives registration information
        and sends it to the database.

        Args:
            session (RegisterSession): The session which has just ended.
        """
        if session in self.register_sessions:
            self.register_sessions.remove(session)
        if session.complete:
            inventory = self.InventoryClass({"Weapon": [], "Armor": [], "Item": []})
            race_attrs = config.game.races[session.char["race"]]
            attributes = self.AttributesClass(
                race_attrs.main,
                race_attrs.resists,
                race_attrs.skills,
                race_attrs.unarmed_damage,
            )
            attributes.restore_values()
            equipment = self.EquipmentClass()
            char = self.CharacterClass(
                member_id=session.char["member_id"],
                name=session.char["name"],
                race=session.char["race"],
                sex=session.char["sex"],
                desc=session.char["desc"],
                inventory=inventory,
                attributes=attributes,
                equipment=equipment,
            )
            char.save()

    def _get_register_session(
        self, author: Union[discord.Member, discord.User]
    ) -> RegisterSession:
        """Returns the session registration of the member, if it exists.

        Args:
            author (Union[discord.Member, discord.User]): Member object

        Returns:
            RegisterSession: Registration session

        """
        return next(
            (
                session
                for session in self.register_sessions
                if session.ctx.author == author
            ),
            None,
        )

    async def get_item_by_name(self, ctx, name: str) -> Item:
        """Returns the item by the given name.

        Args:
            ctx (commands.Context):
            name (str): Item name.

        Returns:
            Document: Item object.

        Raises:
            ItemNotFound: If the item is not found.

        """
        items = self.ItemClass.objects(name=name)
        if not items:
            raise ItemNotFound
        if len(items) > 1:
            i = 1
            text = "**Найдено несколько совпадений:**```\n"
            for item in items:
                text += f"[{i}] {item.name}: {item.desc}\n"
                i += 1
            text += "```**Введите индекс необходимого предмета.**"
            msg = await ctx.send(text)
            try:
                answer = await self.Red.wait_for(
                    "message",
                    timeout=30.0,
                    check=lambda m: re.match(r"\d", m.content)
                    and MessagePredicate.same_context(ctx)
                    and int(m.content) < i,
                )
                item = items[int(answer.content) - 1]
            except asyncio.TimeoutError:
                raise ItemNotFound
            finally:
                await msg.delete()
            return item
        return items.first()

    def get_item_by_id(self, item_id: int) -> Item:
        """Returns the item by the given id.

        Args:
            item_id (int): Item ID.

        Returns:
            Document: Item object.

        Raises:
            ItemNotFound: If the item is not found.

        """
        items = self.ItemClass.objects(item_id=item_id)
        if not items:
            raise ItemNotFound
        return items.first()

    def get_char_by_id(self, member_id: str) -> Character:
        """Returns character object.

        Args:
            member_id: Member ID to get.

        Returns:
            Document: Character object.

        Raises:
            CharacterNotFound: If the member is not registered.

        """
        chars = self.CharacterClass.objects(member_id=member_id)
        if not chars:
            raise CharacterNotFound
        return chars.first()

    def unequip_item(self, char: Character, item: Item):
        """Unequips the item.

        The method finds the item in the equipment and removes it, if it exists.

        Args:
            char (Character): Character on which the item is unequipped.
            item (str): Item to be unequipped.

        """
        items = list(char.equipment.to_mongo().values())
        slots = list(char.equipment.to_mongo().keys())
        item = next(
            (_item for _item in items if int(_item["item_id"]) == (item["item_id"])),
            False,
        )
        if not item:
            raise ItemNotFoundInEquipment
        else:
            index = items.index(item)
            self.unequip_slot(char, slots[index])

    def unequip_slot(self, char: Character, slot: str):
        """Unequips the item from slot.

        The method removes the item from the equipment, adds it to the inventory
        and changes the attributes of the character, if necessary.

        Args:
            char (Character): Character on which the item is unequipped.
            slot (str): Item slot from which there is a need to remove the item.
        """
        equipment = char.equipment
        inventory = char.inventory
        attributes = char.attributes
        _item = getattr(equipment, slot)
        if _item:
            setattr(equipment, slot, None)
            item = self.get_item_by_id(_item["item_id"])
            inventory.add_item(item, 1, _item["maker"], _item["temper"])
            if hasattr(inventory.items, "armor"):
                attributes.armor_rating -= item["armor"]

    def equip_item(self, char: Character, item: dict):
        """Equips the item.

        Args:
            char (Character): Character on which the item is equipped.
            item (dict): Sample item from inventory.

        Raises:
            ItemNotFoundInInventory: If the item is not found in the inventory.
            ItemIsNotEquippable: If the item cannot be equipped.

        """
        equipment = char.equipment
        inventory = char.inventory
        attributes = char.attributes
        item_instance = item.copy()
        item_instance.pop("count")
        _item = self.get_item_by_id(item_instance["item_id"])
        category = inventory.get_item_category(_item)
        if item in inventory.items[category]:
            if category == "Weapon":
                right_hand = equipment.right_hand
                if right_hand:
                    weapon_right = self.get_item_by_id(right_hand["item_id"])
                    left_hand = equipment.left_hand
                    if left_hand:
                        self.unequip_slot(char, "left_hand")
                    if _item["hands"] == 2:
                        self.unequip_slot(char, "right_hand")
                    else:
                        if weapon_right["hands"] == 1:
                            equipment.left_hand = right_hand
                        else:
                            self.unequip_slot(char, "right_hand")
                equipment.right_hand = item_instance
            elif category == "Armor":
                slot = _item["slot"]
                if getattr(equipment, slot):
                    self.unequip_slot(char, slot)
                setattr(equipment, slot, item_instance)
                attributes.armor_rating += _item["armor"]
            else:
                raise ItemIsNotEquippable
            inventory.remove_item(_item, 1, item["maker"], item["temper"])
        else:
            raise ItemNotFoundInInventory

    async def item_select(self, ctx, item, items):
        """

        Args:
            ctx (Context):
            item (Item): Item object
            items (list): List of items to select.

        Returns:
            dict:
        """

        i = 1
        text = "**Найдено несколько совпадений:**```\n"
        for _item in items:
            text += f"[{i}] {item.name}"
            if _item["maker"]:
                text += f". Создатель: {_item['maker']}"
            if _item["temper"]:
                text += f". Улучшение: {_item['temper']}"
            text += "\n"
            i += 1
        text += "```**Введите индекс необходимого предмета.**"
        msg = await ctx.send(text)
        try:
            answer = await self.Red.wait_for(
                "message",
                timeout=30.0,
                check=lambda m: re.match(r"\d", m.content)
                and MessagePredicate.same_context(ctx)
                and int(m.content) < i,
            )
            await answer.delete()
        except asyncio.TimeoutError:
            raise ItemNotFoundInInventory
        finally:
            await msg.delete()
        return items[int(answer.content) - 1]
