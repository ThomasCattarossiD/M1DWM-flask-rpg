from enum import Enum

from init_db import get_db_connection


class Race(Enum):
    HUMAN = "Humain"
    VAMPIRE = "Vampire"
    WEREWOLF = "Loup-Garou"

class Character:
    def __init__(self, id, name, race, character_type, health, attack, defense, level=1):
        self.id = id
        self.name = name
        self.race = race
        self.type = character_type
        self.health = health
        self.attack = attack
        self.defense = defense
        self.level = level

    @staticmethod
    def get_all_by_user(user_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM characters WHERE user_id = ?', (user_id,))
        characters = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return [Character(
            id=char['id'],
            name=char['name'],
            race=Race[char['race']],
            character_type=char['class'],
            health=char['health'],
            attack=char['attack'],
            defense=char['defense'],
            level=char['level']
        ) for char in characters]

    @staticmethod
    def get_by_id(character_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM characters WHERE id = ?', (character_id,))
        char = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if char:
            return Character(
                id=char['id'],
                name=char['name'],
                race=Race[char['race']],
                character_type=char['class'],
                health=char['health'],
                attack=char['attack'],
                defense=char['defense'],
                level=char['level']
            )
        return None

class Warrior(Character):
    def __init__(self, name, race, id=None):
        super().__init__(
            id=id,
            name=name,
            race=race,
            character_type='warrior',
            health=100,
            attack=15,
            defense=10
        )

class Mage(Character):
    def __init__(self, name, race, id=None):
        super().__init__(
            id=id,
            name=name,
            race=race,
            character_type='mage',
            health=80,
            attack=20,
            defense=5
        )

class Item:
    def __init__(self, name, item_type, effect=None):
        self.name = name
        self.type = item_type
        self.effect = effect

    @staticmethod
    def get_by_character(character_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM character_items WHERE character_id = ?', (character_id,))
        items = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return [Item(
            name=item['name'],
            item_type=item['type'],
            effect=item['effect']
        ) for item in items]

class Monster:
    def __init__(self, name, health, attack):
        self.name = name
        self.health = health
        self.attack = attack