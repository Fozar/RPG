from mongoengine import EmbeddedDocument, DictField


class Equipment(EmbeddedDocument):
    """Equipment Class

    Attributes:
        right_hand (dict): The right hand of the character. It can take any
            type of weapon. If the weapon uses two hands, it will occupy the
            right hand.
        left_hand (dict): The left hand of the character. A second one-handed
            weapon or shield can be taken in the left hand.
        helmet (dict): Head slot character. For hats.
        cuirass (dict): Body slot character.
        gauntlets (dict): Hands slot character.
        boots (dict): Foot slot character.

    """

    right_hand = DictField()
    left_hand = DictField()
    helmet = DictField()
    cuirass = DictField()
    gauntlets = DictField()
    boots = DictField()

    def __init__(
        self,
        right_hand=None,
        left_hand=None,
        helmet=None,
        cuirass=None,
        gauntlets=None,
        boots=None,
        *args,
        **kwargs,
    ):
        """Equipment constructor

        Args:
            right_hand (dict): The right hand of the character. It can take any
            type of weapon. If the weapon uses two hands, it will occupy the
            right hand.
            left_hand (dict): The left hand of the character. A second one-handed
                weapon or shield can be taken in the left hand.
            helmet (dict): Head slot character. For hats.
            cuirass (dict): Body slot character.
            gauntlets (dict): Hands slot character.
            boots (dict): Foot slot character.
        """
        super().__init__(*args, **kwargs)
        self.right_hand = right_hand
        self.left_hand = left_hand
        self.helmet = helmet
        self.cuirass = cuirass
        self.gauntlets = gauntlets
        self.boots = boots


class ItemNotFoundInEquipment(Exception):
    """Raises if the item is not found in the equipment."""

    pass


class ItemIsNotEquippable(Exception):
    """Raises if the item is not equippable."""

    pass
