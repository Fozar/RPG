import re

from mongoengine import Document, IntField, StringField


class Item(Document):
    """Item class

    Attributes:
        item_id (int): Item ID.
        name (str): Item name.
        desc (str): Item description.
        price (int): Item price.
        rarity (str): Item rarity.

    """

    rarity_rates = {
        "legendary": "легендарн.",
        "epic": "эпическ.",
        "rare": "редк.",
        "common": "обычн.",
    }
    item_id = IntField(primary_key=True, required=True, min_value=0)
    name = StringField()
    desc = StringField()
    price = IntField(min_value=0)
    rarity = StringField(choices=rarity_rates.keys())

    def __init__(
        self,
        item_id: int,
        name: str,
        desc: str,
        price: int,
        rarity: str,
        *args,
        **values,
    ):
        """Item constructor

        Args:
            item_id (int): Unique item ID.
            name (str): Item name.
            desc (str): Item description.
            price (int): Item price.
            rarity (str): Item rarity.
        """
        super().__init__(*args, **values)
        self.item_id = item_id
        self.name = name
        self.desc = desc
        self.price = price
        self.rarity = rarity

    @property
    def rarity_text(self) -> str:
        """Returns item rarity in human form.

        Returns:
            str: Item rarity.

        """
        return self.rarity_rates[self.rarity].title()

    @property
    def category(self) -> str:
        """Returns the item category.

        Returns:
            str: Category name.

        """
        return re.sub(r"Item.", "", self["_cls"])

    @classmethod
    def get_items(cls, name: str = None, item_id: int = None):
        """Returns a list of items matching id or name.

        Args:
            name (:obj:`str`, optional): Item name.
            item_id (:obj:`int`, optional): Item ID.

        Returns:
            BaseQuerySet: List of items.

        """
        if not name and not item_id:
            raise AttributeError
        elif item_id:
            items = cls.objects(item_id=item_id)
        else:
            items = cls.objects(name=name)

        return items

    @classmethod
    def get_item_by_id(cls, item_id: int):
        """Returns the item by the given id.

        Args:
            item_id (int): Item ID.

        Returns:
            Item: Item object.

        Raises:
            ItemNotFound: If the item is not found.

        """
        items = cls.get_items(item_id=item_id)
        if not items:
            raise ItemNotFound
        return items.first()

    @classmethod
    def get_next_id(cls) -> int:
        """Returns the next free id.

        Returns:
            int: Next free id.

        """
        try:
            item_id = int(cls.objects.order_by("-_id").first().item_id) + 1
        except AttributeError:
            item_id = 0
        return item_id

    meta = {"allow_inheritance": True}


class Armor(Item):
    """Armor class

    Attributes:
        item_id (int): Unique armor ID.
        name (str): Armor name.
        desc (str): Armor description.
        price (int): Armor price.
        rarity (str): Armor rarity.
        slot (str): Armor slot.
        kind (str): Armor kind.
        material (str): Armor material.
        armor (int): Armor rating.

    """

    slots = {
        "helmet": "шлем",
        "cuirass": "броня",
        "boots": "сапоги",
        "gauntlets": "перчатки",
        "shield": "шит",
    }
    armor_kinds = {
        "heavy": "тяжелая броня",
        "light": "легкая броня",
        "clothing": "одежда",
    }
    materials = {
        "iron": "железн.",
        "steel": "стальн.",
        "orcish": "ороч.",
        "glass": "стеклянн.",
        "elven": "эльфийск.",
        "ebony": "эбонитов.",
        "dwarven": "двемерск.",
        "daedric": "даэдрическ.",
        "cloth": "ткань",
        "leather": "кожан.",
    }

    slot = StringField(choices=slots.keys())
    kind = StringField(choices=armor_kinds.keys())
    material = StringField(choices=materials.keys())
    armor = IntField(min_value=0)

    def __init__(
        self,
        item_id: int,
        name: str,
        desc: str,
        price: int,
        rarity: str,
        slot: str = None,
        kind: str = None,
        material: str = None,
        armor: int = 0,
        *args,
        **values,
    ):
        """Armor constructor

        Args:
            item_id (int): Unique armor ID.
            name (str): Armor name.
            desc (str): Armor description.
            price (int): Armor price.
            rarity (str): Armor rarity.
            slot (str): Armor slot. Possible values: helmet, cuirass, boots, gauntlets.
            kind (str): Armor kind. Possible values: heavy, light, clothing.
            material (str): Armor material.
            armor (int): Armor rating. It can not be negative.
        """
        super().__init__(item_id, name, desc, price, rarity, *args, **values)
        self.slot = slot
        self.kind = kind
        self.material = material
        self.armor = armor

    @property
    def slot_text(self):
        return self.slots[self.slot].title()

    @property
    def kind_text(self):
        return self.armor_kinds[self.kind].title()


class Weapon(Item):
    """Weapon Class

    Attributes:
        item_id (int): Unique weapon ID.
        name (str): Weapon name.
        desc (str): Weapon description.
        price (int): Weapon price.
        rarity (str): Weapon rarity.
        attack_type (str): Attack type.
        hands (int): The number of used hands.
        weapon_type (str): Weapon type.
        material (str): Weapon material.
        damage (int): Weapon damage.

    """

    attack_types = {"melee": "ближний бой", "range": "дальний бой"}
    weapon_types = {
        "crossbow": "арбалет",
        "bow": "лук",
        "greatsword": "двуручный меч",
        "battleaxe": "секира",
        "warhammer": "боевой молот",
        "sword": "меч",
        "war_axe": "боевой топор",
        "mace": "булава",
        "dagger": "кинжал",
    }
    materials = {
        "iron": "железн.",
        "steel": "стальн.",
        "wood": "деревянн.",
        "silver": "серебрянн.",
        "orcish": "ороч.",
        "glass": "стеклянн.",
        "elven": "эльфийск.",
        "ebony": "эбонитов.",
        "dwarven": "двемерск.",
        "daedric": "даэдрическ.",
    }

    attack_type = StringField(choices=attack_types.keys())
    hands = IntField(min_value=1, max_value=2)
    weapon_type = StringField(choices=weapon_types.keys())
    material = StringField(choices=materials.keys())
    damage = IntField(min_value=0)

    def __init__(
        self,
        item_id: int,
        name: str,
        desc: str,
        price: int,
        rarity: str,
        attack_type: str = None,
        hands: int = 0,
        weapon_type: str = None,
        material: str = None,
        damage: int = 0,
        *args,
        **values,
    ):
        """Weapon constructor

        Args:
            item_id (int): Unique weapon ID.
            name (str): Weapon name.
            desc (str): Weapon description.
            price (int): Weapon price.
            rarity (str): Weapon rarity.
            attack_type (str): Attack type. May be melee or range.
            hands (int): The number of used hands. May be 1 or 2.
            weapon_type (str): Weapon type. Possible values: crossbow, bow,
                greatsword, battleaxe, warhammer, sword, war_axe, mace, dagger.
            material (str): Weapon material.
            damage (int): Weapon damage. It can not be negative.
        """
        super().__init__(item_id, name, desc, price, rarity, *args, **values)
        self.attack_type = attack_type
        self.hands = hands
        self.weapon_type = weapon_type
        self.material = material
        self.damage = damage

    @property
    def weapon_type_text(self):
        return self.weapon_types[self.weapon_type].title()


class ItemNotFound(Exception):
    """Raises if the item is not found in the database."""

    pass
