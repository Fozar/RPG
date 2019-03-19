from mongoengine import EmbeddedDocumentField, EmbeddedDocument

from ...item.item import Item
from .inventory import ItemNotFoundInInventory
from .item import ItemInstance, InventoryItem, inv_item_to_instance


class Equipment(EmbeddedDocument):
    """Equipment Class

    Attributes:
        right_hand (ItemInstance): The right hand of the character. It can take any
            type of weapon. If the weapon uses two hands, it will occupy the
            right hand.
        left_hand (ItemInstance): The left hand of the character. A second one-handed
            weapon or shield can be taken in the left hand.
        helmet (ItemInstance): Head slot character. For hats.
        cuirass (ItemInstance): Body slot character.
        gauntlets (ItemInstance): Hands slot character.
        boots (ItemInstance): Foot slot character.

    """

    right_hand = EmbeddedDocumentField(ItemInstance, default=None)
    left_hand = EmbeddedDocumentField(ItemInstance, default=None)
    helmet = EmbeddedDocumentField(ItemInstance, default=None)
    cuirass = EmbeddedDocumentField(ItemInstance, default=None)
    gauntlets = EmbeddedDocumentField(ItemInstance, default=None)
    boots = EmbeddedDocumentField(ItemInstance, default=None)

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
            right_hand (ItemInstance): The right hand of the character. It can take any
            type of weapon. If the weapon uses two hands, it will occupy the
            right hand.
            left_hand (ItemInstance): The left hand of the character. A second one-handed
                weapon or shield can be taken in the left hand.
            helmet (ItemInstance): Head slot character. For hats.
            cuirass (ItemInstance): Body slot character.
            gauntlets (ItemInstance): Hands slot character.
            boots (ItemInstance): Foot slot character.
        """
        super().__init__(*args, **kwargs)
        self.right_hand = right_hand
        self.left_hand = left_hand
        self.helmet = helmet
        self.cuirass = cuirass
        self.gauntlets = gauntlets
        self.boots = boots

    def to_dict(self) -> dict:
        slots = list(dict(self.to_mongo()).keys())
        items = [getattr(self, slot) for slot in slots]
        return dict(zip(slots, items))

    def unequip_item(self, item: Item):
        """Unequips the item.

        The method finds the item in the equipment and removes it, if it exists.

        Args:
            item (str): Item to be unequipped.

        """
        eqpt = self.to_dict()
        slots = list(eqpt.keys())
        items = list(eqpt.values())
        print(items)
        item = next((_item for _item in items if _item.item == item), False)
        if not item:
            raise ItemNotFoundInEquipment
        else:
            index = items.index(item)
            self.unequip_slot(slots[index])

    def unequip_slot(self, slot: str):
        """Unequips the item from slot.

        The method removes the item from the equipment, adds it to the inventory
        and changes the attributes of the character, if necessary.

        Args:
            slot (str): Item slot from which there is a need to remove the item.
        """

        instance = getattr(self, "_instance")
        inventory = instance.inventory
        attributes = instance.attributes
        item = getattr(self, slot)
        if item:
            inventory.add_item(item.item, 1, item.maker, item.temper)
            if hasattr(item.item, "armor"):
                attributes.mod_value("armor_rating", item.item.armor)
            setattr(self, slot, None)

    def equip_item(self, item: InventoryItem):
        """Equips the item.

        Args:
            item (InventoryItem): Sample item from inventory.

        Raises:
            ItemNotFoundInInventory: If the item is not found in the inventory.
            ItemIsNotEquippable: If the item cannot be equipped.

        """
        instance = getattr(self, "_instance")
        inventory = instance.inventory
        attributes = instance.attributes
        item_instance = inv_item_to_instance(item)
        category = item_instance.item.category
        if item in getattr(inventory, category.lower()):
            if category == "Weapon":
                right_hand = self.right_hand
                if right_hand:
                    weapon_right = right_hand.item
                    left_hand = self.left_hand
                    if left_hand:
                        self.unequip_slot("left_hand")
                    if item_instance.item.hands == 2:
                        self.unequip_slot("right_hand")
                    else:
                        if weapon_right.hands == 1:
                            self.left_hand = right_hand
                        else:
                            self.unequip_slot("right_hand")
                self.right_hand = item_instance
            elif category == "Armor":
                slot = item_instance.item.slot
                if getattr(self, slot):
                    self.unequip_slot(slot)
                setattr(self, slot, item_instance)
                attributes.mod_value("armor_rating", item_instance.item.armor)
            else:
                raise ItemIsNotEquippable
            inventory.remove_item(
                item_instance.item, 1, item_instance.maker, item_instance.temper
            )
        else:
            raise ItemNotFoundInInventory


class ItemNotFoundInEquipment(Exception):
    """Raises if the item is not found in the equipment."""

    pass


class ItemIsNotEquippable(Exception):
    """Raises if the item is not equippable."""

    pass
