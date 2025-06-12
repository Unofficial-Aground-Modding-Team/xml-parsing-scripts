"Extracts all <item> definitions, selecting a subset of their properties and relationships with other types of data"

import json
from lxml import etree
from pathlib import Path

cached = Path("clean/aggregated.xml")
output_folder = Path("output/items")

output_folder.mkdir(parents=True, exist_ok=True)

tree: etree._ElementTree = etree.parse(cached, None)

def show(element):
    'utils function for debugging'
    print(etree.tostring(element, pretty_print=True).decode())  # type: ignore

# Each element in the data list corresponds to one file's root <data> or equivalent
data: list[etree._Element] = tree.findall('./', None)

# NOTE: THE OUTPUT DOES NOT INCLUDES ANYTHING INHERITED FROM EXTENDING

items: list[etree._Element] = [item for root in data for item in root.findall("item", None)]

recipes: list[etree._Element] = [recipe for root in data for recipe in root.findall("recipe", None)]
quests: list[etree._Element] = [quest for root in data for quest in root.findall("quest", None)]
enemies: list[etree._Element] = [enemy for root in data for enemy in root.findall("enemy", None)]

LANG = {}
for root in data:
    for lang in root.findall("lang", None):
        lang_map = LANG.setdefault(lang.get("id", None), {})
        for section in lang.findall("section", None):
            for text in section.findall("text", None):
                text_string = text.text.strip()
                for connector in ['>', '.']:
                    text_id = section.get("id", None) + connector + text.get("id", None)
                    lang_map[text_id] = text_string

# item id -> list of enemies
looted_from: dict[str, list[str]] = {}
for enemy in enemies:
    loot_items: list[etree._Element] = [*enemy.findall("./lootSet/loot", None), *enemy.findall("./loot", None)]
    for item in loot_items:
        if (item_id := item.get("id", None)) is not None:
            looted_from.setdefault(item_id, []).append(enemy.get("id", None))


used_for_quests: dict[str, list[str]] = {}
for quest in quests:
    required_items: list[etree._Element] = quest.findall("./item", None)
    for item in required_items:
        used_for_quests.setdefault(item.get("id", None), []).append(quest.get("id", None))


created_from_recipes: dict[str, list[str]] = {}
used_for_recipes: dict[str, list[str]] = {}
for recipe in recipes:
    required_items: list[etree._Element] = recipe.findall("./item", None)
    creates: str = recipe.get("creates", None)
    created_from_recipes.setdefault(creates, []).append(recipe.get("id", None))
    for item in required_items:
        used_for_recipes.setdefault(item.get("id", None), []).append(recipe.get("id", None))

# item id -> list of familiars that eat it
familiars_eat: dict[str, list[str]] = {}

for item in items:
    familiar = item.find("familiar", None)
    if familiar is not None:
        for food in item.findall("food", None):
            familiars_eat.setdefault(food.get("id", None), []).append(item.get("id", None))


# --------
common_properties = [
    "type",
    "extends",
    "slot",
    "weight",
    "droppable",
    "cost",
    "element",
    "knockback",
    "reflect",
    "melee_range",
    "range",
    "damage",
    "attack",
    "cut",
    "defense",
    "block",
    "mine",
    "breakPower",
    "durability",
    "broken",
    "repair",
    "health",
    "stamina",
    "power",
    "underwater",
    "canJump",
    "with",
    "unequip",
    "equipOn",
    "hpSteal",
    "group",
]
composite_properties = [
    ["flight", "height"],
    ["flight", "speed"],
    ["flight", "cost"],
    ["use", "slot"],
    ["projectile", "speed"],
    ["projectile", "hitEffect", "id"],
    ["projectile", "breakPower"],
    ["hitEffect", "id"],
    ["light", "tile"],
    ["familiar", "id"],
    ["stat", "id"],
    ["stat", "value"],
    ["stat", "time"],
    ["stat", "max"],
    ["equipCost", "health"],
    ["equipCost", "stamina"],
    ["equipCost", "storage"],
    ["equipCost", "cost"],
]

def get_composite(node: etree._Element, path: list[str]) -> list[str]:
    if len(path) > 1:
        results = []
        for child in node.findall(path[0], None):
            results.extend(get_composite(child, path[1:]))
        return results
    else:
        return [node.get(path[0], None)]

for source_data in data:
    item: etree._Element
    for item in source_data.findall("./item", None):
        item_id = item.get("id", None)
        if item.get('name', None):
            try:
                item_name = LANG["en_US"][item.get("name", None)]
            except KeyError:
                item_name = LANG["en_US"][f"item.names>{item.get("name", None)}"]
        else:
            try:
                item_name = LANG["en_US"][f"item.names>{item_id}"]
            except KeyError:
                print(f"Failed to get name for {item_id}")
                item_name = item_id
        assert isinstance(item_id, str)
        # Still missing: effect and alike? not sure tbh
        result = {
            "source": source_data.get("source", None),
            "id": item_id,
            "name": item_name,
            **{prop: item.get(prop, None) for prop in common_properties},
            **{
                '_'.join(composite_path): get_composite(item, composite_path)
                for composite_path in composite_properties
            },
            "special_connections": {
                "looted_from": looted_from.get(item_id),
                "quest_requires": used_for_quests.get(item_id),
                "familiar_food": familiars_eat.get(item_id),
                "recipe_creates": created_from_recipes.get(item_id),
                "ingredient": used_for_recipes.get(item_id),
            },
        }

        for key, val in list(result.items()):
            if isinstance(val, list):
                val = list(filter(None, val))
                if len(val) == 1:
                    val = val[0]
                    result[key] = val

            if isinstance(val, dict):
                for inner_key, inner_val in list(val.items()):
                    if not inner_val:
                        del val[inner_key]
            if not val:
                del result[key]

        with (output_folder / (item_id + '.json')).open('w') as file:
            json.dump(result, file, indent=4)
