import random
from enum import Enum, auto
from typing import List, Dict

class Race(Enum):
    HUMAIN = auto()
    VAMPIRE = auto()
    LOUP_GAROU = auto()
    ELFE = auto()

class Classe(Enum):
    GUERRIER = auto()
    MAGE = auto()
    ARCHER = auto()
    VOLEUR = auto()

class ItemType(Enum):
    POTION = auto()
    EQUIPEMENT = auto()
    CLE = auto()
    ARME = auto()

class Success:
    def __init__(self, name: str, description: str, reward: Dict):
        self.name = name
        self.description = description
        self.reward = reward
        self.completed = False

class Item:
    def __init__(self, name: str, type: ItemType, value: int = 0):
        self.name = name
        self.type = type
        self.value = value

class Mob:
    def __init__(self, name: str, life_points: int, attack_points: int, difficulty: int):
        self.name = name
        self.life_points = life_points
        self.attack_points = attack_points
        self.difficulty = difficulty

class Character:
    def __init__(self, name: str, race: Race, classe: Classe):
        self.name = name
        self.race = race
        self.classe = classe
        
        # Caractéristiques de base selon la race et la classe
        self.race_multipliers = {
            Race.HUMAIN: {"life": 1.0, "attack": 1.0, "defense": 1.0},
            Race.VAMPIRE: {"life": 1.2, "attack": 1.1, "defense": 0.9},
            Race.LOUP_GAROU: {"life": 1.3, "attack": 1.2, "defense": 0.8},
            Race.ELFE: {"life": 0.9, "attack": 1.3, "defense": 1.1}
        }
        
        self.classe_multipliers = {
            Classe.GUERRIER: {"life": 1.3, "attack": 1.2, "defense": 1.2},
            Classe.MAGE: {"life": 0.8, "attack": 1.5, "defense": 0.9},
            Classe.ARCHER: {"life": 1.0, "attack": 1.1, "defense": 1.0},
            Classe.VOLEUR: {"life": 0.9, "attack": 1.3, "defense": 0.8}
        }
        
        # Stats de base
        self.max_life = int(100 * self.race_multipliers[race]["life"] * self.classe_multipliers[classe]["life"])
        self.current_life = self.max_life
        self.attack = int(20 * self.race_multipliers[race]["attack"] * self.classe_multipliers[classe]["attack"])
        self.defense = int(10 * self.race_multipliers[race]["defense"] * self.classe_multipliers[classe]["defense"])
        
        # Progression
        self.level = 1
        self.experience = 0
        self.inventory: List[Item] = []
        self.successes: List[Success] = []

    def level_up(self):
        self.level += 1
        # Augmentation des stats
        self.max_life = int(self.max_life * 1.2)
        self.current_life = self.max_life
        self.attack = int(self.attack * 1.15)
        self.defense = int(self.defense * 1.15)

    def gain_experience(self, exp_points: int):
        self.experience += exp_points
        if self.experience >= 100 * self.level:
            self.level_up()
            self.experience = 0

    def add_item(self, item: Item):
        self.inventory.append(item)

    def use_item(self, item: Item):
        if item in self.inventory:
            if item.type == ItemType.POTION:
                self.current_life = min(self.max_life, self.current_life + item.value)
                self.inventory.remove(item)
            elif item.type == ItemType.EQUIPEMENT:
                # Logique d'équipement à implémenter
                pass

    def attack_mob(self, mob: Mob):
        damage = max(0, self.attack - mob.difficulty)
        mob.life_points -= damage
        return damage

    def receive_damage(self, damage: int):
        actual_damage = max(0, damage - self.defense)
        self.current_life -= actual_damage
        return actual_damage

class GameMode:
    def __init__(self, player: Character):
        self.player = player

class VersusMode(GameMode):
    def start_battle(self, opponent: Character):
        # Logique de combat JcJ
        while self.player.current_life > 0 and opponent.current_life > 0:
            damage_to_opponent = self.player.attack_mob(opponent)
            damage_to_player = opponent.attack_mob(self.player)
            
            print(f"{self.player.name} inflige {damage_to_opponent} dégâts à {opponent.name}")
            print(f"{opponent.name} inflige {damage_to_player} dégâts à {self.player.name}")

class QuestMode(GameMode):
    def __init__(self, player: Character):
        super().__init__(player)
        self.current_quest_level = 1
        self.mobs = self.generate_mobs()

    def generate_mobs(self):
        return [
            Mob(f"Monstre Niveau {i}", 50 * i, 10 * i, i) 
            for i in range(1, self.current_quest_level + 5)
        ]

    def start_quest(self):
        for mob in self.mobs:
            while mob.life_points > 0 and self.player.current_life > 0:
                damage_to_mob = self.player.attack_mob(mob)
                damage_to_player = mob.attack_points
                
                self.player.receive_damage(damage_to_player)
                
                if mob.life_points <= 0:
                    self.player.gain_experience(mob.difficulty * 10)
                    print(f"Vous avez vaincu {mob.name} !")
                
                if self.player.current_life <= 0:
                    print("Game Over!")
                    break

class BoardMode(GameMode):
    def __init__(self, player: Character, board_size: int = 10):
        super().__init__(player)
        self.board_size = board_size
        self.board = self.generate_board()
        self.player_position = 0

    def generate_board(self):
        board = []
        for _ in range(self.board_size):
            case_type = random.choice(['combat', 'objet', 'vie', 'piege'])
            board.append(case_type)
        return board

    def move_player(self):
        dice_roll = random.randint(1, 6)
        self.player_position = min(self.player_position + dice_roll, self.board_size - 1)
        
        current_case = self.board[self.player_position]
        
        if current_case == 'combat':
            mob = Mob("Gardien", 50, 10, 2)
            print(f"Combat contre {mob.name} !")
            self.player.attack_mob(mob)
        
        elif current_case == 'objet':
            item = Item("Potion de Vie", ItemType.POTION, 20)
            self.player.add_item(item)
            print(f"Vous avez trouvé {item.name} !")
        
        elif current_case == 'vie':
            heal_amount = random.randint(10, 30)
            self.player.current_life = min(self.player.max_life, self.player.current_life + heal_amount)
            print(f"Vous regagnez {heal_amount} points de vie !")
        
        elif current_case == 'piege':
            damage = random.randint(5, 15)
            self.player.receive_damage(damage)
            print(f"Piège ! Vous perdez {damage} points de vie !")

# Exemple d'utilisation
def main():
    # Création d'un personnage
    hero = Character("Héros Adventurier", Race.LOUP_GAROU, Classe.GUERRIER)
    
    # Mode Versus
    versus = VersusMode(hero)
    
    # Mode Quête
    quest = QuestMode(hero)
    quest.start_quest()
    
    # Mode Plateau
    board = BoardMode(hero)
    board.move_player()

if __name__ == "__main__":
    main()