from mongoengine import EmbeddedDocument, EmbeddedDocumentListField, DoesNotExist
from mongoengine.queryset.base import BaseQuerySet

from .item import InventoryItem
from ...item.item import Item


class Inventory(EmbeddedDocument):
    """Inventory class"""

    weapon = EmbeddedDocumentListField(InventoryItem)
    armor = EmbeddedDocumentListField(InventoryItem)
    item = EmbeddedDocumentListField(InventoryItem)

    def get_items(self, item: Item) -> BaseQuerySet:
        """Returns a list of items that match this item object from inventory.

        Args:
            item (Item): Item object.

        Returns:
            list: List of items.

        Raises:
            ItemNotFoundInInventory: If no match is found.

        """

        category = item.category.lower()
        items = getattr(self, category, None).filter(item=item)
        if not bool(items):
            raise ItemNotFoundInInventory
        return items

    def get_item(self, item: Item, maker: str, temper: int) -> InventoryItem:
        """Returns an instance of an object from inventory.

        Args:
            item (Item): The item to get from inventory.
            maker (str): Name of the maker of the item.
            temper (int): Item tempering.

        Returns:
            dict: Inventory item object.

        Raises:
            ItemNotFoundInInventory: If the item is not found in inventory.

        """

        category = item.category.lower()
        items = getattr(self, category, None)
        try:
            item = items.get(item=item, maker=maker, temper=temper)
        except DoesNotExist:
            raise ItemNotFoundInInventory
        return item

    def add_item(self, item: Item, count: int, maker: str = None, temper: int = None):
        """Adds item to inventory.

        The method tries to find an instance of the item in the inventory, if it
        succeeds, then it simply increases the number of items. Otherwise, it
        creates a new instance of the item in this inventory.

        Args:
            item (Item): The item to add to inventory.
            count (int): The number of items to add.
            maker (:obj:`str`, optional): Name of the maker of the item. Defaults
                to None.
            temper (:obj:`int`, optional): Item tempering. Defaults to None.
        """
        try:
            _item = self.get_item(item, maker, temper)
            _item.count += count
        except ItemNotFoundInInventory:
            category = item.category.lower()
            getattr(self, category).create(
                item=item, count=count, maker=maker, temper=temper
            )

    def remove_item(
        self, item: Item, count: int, maker: str = None, temper: int = None
    ):
        """Removes item from inventory.

        The method reduces the number of items. If after this, the number of
        this item is less than 1, then it will be deleted.

        Args:
            item (Item): The item to remove from inventory.
            count (int): The number of items to remove.
            maker (:obj:`str`, optional): Name of the maker of the item. Defaults
                to None.
            temper (:obj:`int`, optional): Item tempering. Defaults to None.

        """

        _item = self.get_item(item, maker, temper)
        _item.count -= count
        if _item.count < 1:
            getattr(self, item.category.lower()).filter(
                item=item, maker=maker, temper=temper
            ).delete()

    def is_inventory_empty(self) -> bool:
        """Returns whether there are items in the inventory.

        Returns:
            bool: The inventory is empty or not.

        """
        for category in list(self.to_mongo().values()):
            if len(category) > 0:
                return False
        else:
            return True


class ItemNotFoundInInventory(Exception):
    """Raises if the item is not found in the inventory."""

    pass
