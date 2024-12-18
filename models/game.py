from enum import Enum
import random

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


class Tableau:
    def __init__(self, hero, length=20):
        """
        Initiali    ze the tableau game
        :param hero: The hero playing the game
        :param length: Length of the tableau (default 20)
        """
        self.hero = hero
        self.length = length
        self.board = self._generate_board()
        self.current_position = 0
        self.is_completed = False
        self.is_game_over = False

    def _generate_board(self):
        """
        Generate a board with random elements
        Possible elements:
        - None (empty space)
        - Item
        - Enemy
        """
        board = []
        for _ in range(self.length):
            element_type = random.choices(
                ['empty', 'item', 'enemy'],
                weights=[0.5, 0.25, 0.25]
            )[0]

            if element_type == 'empty':
                board.append(None)
            elif element_type == 'item':
                # Generate a random item from hero's possible items
                potion = Item("potion", "healing", "+10 hp")
                sword = Item("sword", "weapon", "+10 atk")
                shield = Item("shield", "armor", "+10 def")
                possible_items = [potion, sword, shield]  # Add more item types as needed
                board.append(random.choice(possible_items))
            elif element_type == 'enemy':
                # Generate a random enemy
                enemy_races = ["orc", "creature", "undead"]
                enemy = Monster(
                    random.choice(enemy_races) + 'at pos' + str(len(board)),
                    random.randint(0, 10),
                    random.randint(0, 10)
                )
                board.append(enemy)

        return board

    def play_turn(self):
        """
        Play a single turn in the tableau
        Returns output of the turn
        """
        output = ""
        dice_roll = random.randint(1, 6)
        output += f"{self.hero.name} rolls {dice_roll}\n"

        # Move hero
        self.current_position += dice_roll
        output += f"{self.hero.name} moves to position {self.current_position}\n"

        # Check if hero has gone past the board
        if self.current_position >= self.length:
            output += f"{self.hero.name} completed the tableau!\n"
            self.is_completed = True
            # Add XP or other completion logic here
            return output

        # Check current board element
        current_element = self.board[self.current_position]

        if current_element is None:
            output += "Nothing happened. The space is empty.\n"
        elif isinstance(current_element, Item):
            output += f"{self.hero.name} found an item: {current_element.name}\n"
            # Assuming hero has a method to add items
            self.board[self.current_position] = None  # Remove item after picking up
        elif isinstance(current_element, Monster):
            output += f"Enemy encountered: {current_element.name}\n"
            # Implement battle logic
            battle_result = self.battle(current_element)
            output += battle_result

        # Check if hero died in battle
        if self.hero.health <= 0:
            output += f"{self.hero.name} died. Game Over!\n"
            self.is_game_over = True

        return output

    def battle(self, monster):
        """
        Simulate a battle between the hero and a monster
        """
        output = f"Battle between {self.hero.name} and {monster.name}\n"

        # Simple battle mechanics without defense
        hero_damage = self.hero.attack
        monster_damage = monster.attack

        # Round-based battle
        while self.hero.health > 0 and monster.health > 0:
            # Hero attacks monster
            monster.health -= hero_damage
            output += f"{self.hero.name} deals {hero_damage} damage to {monster.name}\n"

            if monster.health <= 0:
                output += f"{monster.name} is defeated!\n"
                break

            # Monster attacks hero
            self.hero.health -= monster_damage
            output += f"{monster.name} deals {monster_damage} damage to {self.hero.name}\n"

            if self.hero.health <= 0:
                output += f"{self.hero.name} is defeated!\n"
                break

        return output
