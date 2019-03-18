import re

from mongoengine import EmbeddedDocument, DictField, ListField

from ..item.item import Item


class Inventory(EmbeddedDocument):
    """Inventory class

    All items are dictionaries that contain information about the item ID,
    maker of the item and its tempering. These dictionaries are stored in
    lists, which are the values of the keys of the `items` dictionary. The keys
    of this dictionary are categories of inventory items.
    """

    items = DictField(
        ListField(DictField()), default={"Weapon": [], "Armor": [], "Item": []}
    )

    @staticmethod
    def get_item_category(item: Item) -> str:
        """Returns the item category.

        The method deletes the substring "Item.", if present.

        Args:
            item (Item): The item to get category.

        Returns:
            str: Category name.

        """
        return re.sub(r"Item.", "", item["_cls"])

    def get_items(self, item: Item) -> list:
        """Returns a list of items that match this item object from inventory,
        , if it exists in it, otherwise it raises the exception
        ItemNotFoundInInventory.

        Args:
            item (Item): Item object

        Returns:
            list: List of items that match item object

        Raises:
            ItemNotFoundInInventory: If the item is not found in inventory.

        """
        category = self.get_item_category(item)
        items = [
            _item for _item in self.items[category] if _item["item_id"] == item.item_id
        ]
        if not bool(items):
            raise ItemNotFoundInInventory
        return items

    def get_item(self, item: Item, maker: str, temper: int) -> dict:
        """Returns a dictionary of an item from the inventory, if it exists
        in it, otherwise it raises the exception ItemNotFoundInInventory.

        Args:
            item (Item): The item to get from inventory.
            maker (str: Name of the maker of the item.
            temper (int): Item tempering.

        Returns:
            dict: Inventory item dictionary.

        Raises:
            ItemNotFoundInInventory: If the item is not found in inventory.

        """
        category = self.get_item_category(item)
        found_item = next(
            (
                _item
                for _item in self.items[category]
                if _item["item_id"] == item.item_id
                and _item["maker"] == maker
                and _item["temper"] == temper
            ),
            False,
        )
        if not bool(found_item):
            raise ItemNotFoundInInventory
        return found_item

    def add_item(self, item: Item, count: int, maker: str = None, temper: int = None):
        """Adds item to inventory.

        The method tries to find an instance of the item in the inventory, if it
        succeeds, then it simply increases the number of items. Otherwise, it
        creates a new instance of the item in this inventory and cleans it from
        blank items.

        Args:
            item (Item): The item to add to inventory.
            count (int): The number of items to add.
            maker (:obj:`str`, optional): Name of the maker of the item. Defaults
                to None.
            temper (:obj:`int`, optional): Item tempering. Defaults to None.
        """
        try:
            _item = self.get_item(item, maker, temper)
            _item["count"] += count
        except ItemNotFoundInInventory:
            category = self.get_item_category(item)
            new_item = {
                "item_id": item.id,
                "count": count,
                "maker": maker,
                "temper": temper,
            }
            self.items[category].append(new_item)
            self.items[category][:] = [
                item for item in self.items[category] if item.get("count") > 0
            ]

    def remove_item(
        self, item: Item, count: int, maker: str = None, temper: int = None
    ):
        """Removes item from inventory.

        The method reduces the number of items. If after this operation the
        number of items has become less than 1, then all items that are less
        than 1 are removed from the inventory.

        If there are no items left after deleting an item in this section of
        the inventory, an blank item will be created to prevent the list from
        being deleted, due to the characteristics of mongoengine.

        Args:
            item (Item): The item to remove from inventory.
            count (int): The number of items to remove.
            maker (:obj:`str`, optional): Name of the maker of the item. Defaults
                to None.
            temper (:obj:`int`, optional): Item tempering. Defaults to None.
        """
        _item = self.get_item(item, maker, temper)
        category = self.get_item_category(item)
        if _item:
            _item["count"] -= count
            if _item["count"] < 1:
                self.items[category][:] = [
                    item for item in self.items[category] if item.get("count") > 0
                ]
                if len(self.items[category]) < 1:
                    blank_item = {"item_id": "", "count": 0}
                    self.items[category].append(blank_item)

    def is_inventory_empty(self) -> bool:
        """Returns whether there are items in the inventory.

        Returns:
            bool: The inventory is empty or not.

        """
        inv = self.items
        for category, items in inv.items():
            try:
                if items[0]["count"] > 0:
                    return False
            except IndexError:
                pass
        else:
            return True


class ItemNotFoundInInventory(Exception):
    """Raises if the item is not found in the inventory."""

    pass
