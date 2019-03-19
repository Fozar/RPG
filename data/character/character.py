from mongoengine import (
    Document,
    StringField,
    IntField,
    FloatField,
    URLField,
    EmbeddedDocumentField,
)

from .inventory.equipment import Equipment
from .attributes import Attributes
from .inventory.inventory import Inventory
from ...config import config


class Character(Document):
    """Character class

    Attributes:
        member_id (str): Member ID.
        name (str): Character name.
        race (str): Character race.
        sex (str): Character sex.
        desc (str): Character description. Maximum length is 1500.
        lvl (int): The current level of the character. Defaults to 1. Minimum
            value is 1.
        xp (int): The current experience of the character. Defaults to 0.
            Minimum value is 0.
        xp_factor (float): Multiplier experience for the character. Defaults
            to 1.0.
        avatar (str): Link to character avatar. Defaults to None.
        inventory (Inventory): Character inventory.
        attributes (Attributes): Character attributes.
        equipment (Equipment): Character equipment.
    """

    member_id = StringField(primary_key=True)
    name = StringField(max_length=25)
    race = StringField(choices=config.humanize.races.keys())
    sex = StringField(choices=config.humanize.genders.keys())
    desc = StringField(max_length=1500)
    lvl = IntField(default=1, min_value=1)
    xp = IntField(default=0, min_value=0)
    xp_factor = FloatField(default=1.0)
    avatar = URLField(default=None)
    inventory = EmbeddedDocumentField(Inventory)
    attributes = EmbeddedDocumentField(Attributes)
    equipment = EmbeddedDocumentField(Equipment)

    def __init__(
        self,
        member_id: str,
        name: str,
        race: str,
        sex: str,
        desc: str,
        inventory: Inventory,
        attributes: Attributes,
        equipment: Equipment,
        *args,
        **values,
    ):
        """Character constructor

        Args:
            member_id: Member ID.
            name: Character name. Maximum length is 25.
            race: Character race.
            sex: Character sex.
            description: Character description. Maximum length is 1500.
            attributes: Character attributes.
            equipment: Character equipment.
        """
        super().__init__(*args, **values)
        self.member_id = member_id
        self.name = name
        self.race = race
        self.sex = sex
        self.desc = desc
        self.inventory = inventory
        self.attributes = attributes
        self.equipment = equipment

    @classmethod
    def is_member_registered(cls, member_id: str) -> bool:
        """Returns whether the member has a character.

        Args:
            member_id: Member ID to check.

        Returns:
            bool: Character registered or not.

        """
        if cls.objects(member_id=member_id):
            return True
        else:
            return False

    @classmethod
    def get_char_by_id(cls, member_id: str):
        """Returns character object.

        Args:
            member_id: Member ID to get.

        Returns:
            Character: Character object.

        Raises:
            CharacterNotFound: If the member is not registered.

        """
        chars = cls.objects(member_id=member_id)
        if not chars:
            raise CharacterNotFound
        return chars.first()


class CharacterNotFound(Exception):
    """Raises if the member is not registered."""

    pass
