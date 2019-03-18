from mongoengine import EmbeddedDocument, FloatField, DictField, IntField


class Attributes(EmbeddedDocument):
    """Character Attribute Class

    Attributes:
        health (float): Character health. Equals 10 immediately after creating a character.
        stamina (float) Character stamina. Equals 10 immediately after creating a character.
        magicka (float) Character magicka. Equals 10 immediately after creating a character.
        main (dict): The main dynamic attributes of the character.
        resists (dict): Character resistance to magic, elements, poisons and diseases.
        skills (dict): The level of skills of the character.
        armor_rating (int): Total character armor.
        unarmed_damage (int): Unarmed character damage.

    """

    health = FloatField(default=10)
    stamina = FloatField(default=10)
    magicka = FloatField(default=10)
    main = DictField(FloatField())
    resists = DictField(FloatField(min_value=-90, max_value=90))
    skills = DictField(FloatField(min_value=0, max_value=100))
    armor_rating = IntField(default=0)
    unarmed_damage = IntField()

    def __init__(
        self,
        main: dict,
        resists: dict,
        skills: dict,
        unarmed_damage: int,
        *args,
        **kwargs,
    ):
        """Attributes constructor

        Args:
            main (dict): The main dynamic attributes of the character.
            resists (dict): Character resistance to magic, elements, poisons and diseases.
            skills (dict): The level of skills of the character.
            unarmed_damage (int): Unarmed character damage.
        """
        super().__init__(*args, **kwargs)
        self.main = main
        self.resists = resists
        self.skills = skills
        self.unarmed_damage = unarmed_damage

    def get_total_value(self, attribute: str) -> int:
        """Returns the maximum attribute value, including all bonuses.

        Args:
            attribute (str): Attribute name to get.

        Returns:
            int: Maximum attribute value.

        """
        return self.main[f"{attribute}_max"] + self.main[f"{attribute}_buff"]

    def mod_value(self, attribute: str, damage: int):
        """Modifies the attribute value.

        A positive value will increase the value of the attribute by this
        number, a negative value will decrease it.

        Args:
            attribute (str): Attribute name to modify.
            damage (int): The amount by which the attribute will be modified.

        Raises:
            AttributeNotFound: If the attribute is not found.
        """
        if hasattr(self, attribute):
            attr = getattr(self, attribute)
            try:
                total = self.get_total_value(attribute)
                if attr + damage <= total:
                    setattr(self, attribute, attr + damage)
                    attr = getattr(self, attribute)
                    if attr > total:
                        setattr(self, attribute, total)
                    elif attr < 1:
                        setattr(self, attribute, 0)
                else:
                    setattr(self, attribute, total)
            except KeyError:
                setattr(self, attribute, attr + damage)
        elif hasattr(self.main, attribute):
            setattr(self.main, attribute, getattr(self.main, attribute) + damage)
        elif hasattr(self.resists, attribute):
            setattr(self.resists, attribute, getattr(self.resists, attribute) + damage)
        elif hasattr(self.skills, attribute):
            attr = getattr(self.skills, attribute)
            if attr + damage <= 100:
                setattr(self.skills, attribute, attr + damage)
                attr = getattr(self.skills, attribute)
                if attr > 100:
                    setattr(self.skills, attribute, 100)
                elif attr < 1:
                    setattr(self.skills, attribute, 0)
            else:
                setattr(self.skills, attribute, 100)
        else:
            raise AttributeNotFound

    def restore_values(self):
        """ Restores Health, Stamina and Magicka """
        self.health = self.main["health_max"]
        self.stamina = self.main["stamina_max"]
        self.magicka = self.main["magicka_max"]


class AttributeNotFound(Exception):
    """Raises if the attribute is not found."""

    pass
