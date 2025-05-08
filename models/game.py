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
        # Stats de base
        base_health = 100
        base_attack = 10
        base_defense = 10
        
        # Modificateurs de race
        if race == Race.HUMAN:
            base_health += 10
            base_attack += 5
            base_defense += 5
        elif race == Race.VAMPIRE:
            base_health -= 10
            base_attack += 15
            base_defense -= 5
        elif race == Race.WEREWOLF:
            base_health += 20
            base_attack -= 5
            base_defense += 10
            
        # Modificateurs de classe
        base_health += 15
        base_attack += 5
        base_defense += 10
        
        # Assurer les minimums
        base_health = max(base_health, 50)
        base_attack = max(base_attack, 5)
        base_defense = max(base_defense, 0)
        
        # Limiter les PV à 100 maximum
        base_health = min(base_health, 100)
        
        super().__init__(
            id=id,
            name=name,
            race=race,
            character_type='warrior',
            health=base_health,
            attack=base_attack,
            defense=base_defense
        )


class Mage(Character):
    def __init__(self, name, race, id=None):
        # Stats de base
        base_health = 100
        base_attack = 10
        base_defense = 10
        
        # Modificateurs de race
        if race == Race.HUMAN:
            base_health += 10
            base_attack += 5
            base_defense += 5
        elif race == Race.VAMPIRE:
            base_health -= 10
            base_attack += 15
            base_defense -= 5
        elif race == Race.WEREWOLF:
            base_health += 20
            base_attack -= 5
            base_defense += 10
            
        # Modificateurs de classe
        base_health -= 15
        base_attack += 15
        base_defense -= 5
        
        # Assurer les minimums
        base_health = max(base_health, 50)
        base_attack = max(base_attack, 5)
        base_defense = max(base_defense, 0)
        
        # Limiter les PV à 100 maximum
        base_health = min(base_health, 100)
        
        super().__init__(
            id=id,
            name=name,
            race=race,
            character_type='mage',
            health=base_health,
            attack=base_attack,
            defense=base_defense
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
        Initialise le jeu de plateau
        :param hero: Le héros qui joue
        :param length: Longueur du plateau (par défaut 20)
        """
        self.hero = hero
        self.length = length
        self.board = self._generate_board()
        self.current_position = 1
        self.is_completed = False
        self.is_game_over = False

    def _generate_board(self):
        """
        Génère un plateau avec des éléments aléatoires
        Éléments possibles:
        - None (case vide)
        - Item (objet)
        - Enemy (ennemi)
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
                # Générer un objet aléatoire
                potion = Item("Potion de soins", "healing", "+10 pv")
                epee = Item("Épée rouillée", "weapon", "+5 att")
                bouclier = Item("Bouclier en bois", "armor", "+5 def")
                possible_items = [potion, epee, bouclier]
                board.append(random.choice(possible_items))
            elif element_type == 'enemy':
                # Générer un ennemi aléatoire
                enemy_races = ["Gobelin", "Squelette", "Zombie", "Bandit"]
                enemy = Monster(
                    random.choice(enemy_races),
                    random.randint(30, 50),
                    random.randint(5, 15)
                )
                board.append(enemy)

        return board

    def play_turn(self):
        """Joue un tour sur le plateau"""
        output = ""
        dice_roll = random.randint(1, 6)
        output += f"{self.hero.name} lance {dice_roll}\n"

        # Déplacer le héros sans dépasser la longueur du plateau
        new_position = min(self.current_position + dice_roll, self.length)
        output += f"{self.hero.name} se déplace à la position {new_position}\n"
        self.current_position = new_position

        # Vérifier si le héros a atteint la fin du plateau
        if self.current_position >= self.length:
            output += f"{self.hero.name} a complété le plateau !\n"
            self.is_completed = True
            return output

        # Vérifier l'élément actuel du plateau
        current_element = self.board[self.current_position]

        if current_element is None:
            output += "Rien ne s'est passé. La case est vide.\n"
        elif isinstance(current_element, Item):
            output += f"{self.hero.name} a trouvé un objet : {current_element.name}\n"
            # Ajouter l'objet à l'inventaire du personnage
            try:
                self._add_item_to_inventory(current_element)
                output += f"L'objet {current_element.name} a été ajouté à votre inventaire.\n"
            except Exception as e:
                output += f"Impossible d'ajouter l'objet à l'inventaire : {str(e)}\n"
            
            # Supprimer l'objet du plateau après l'avoir ramassé
            self.board[self.current_position] = None
        elif isinstance(current_element, Monster):
            output += f"Ennemi rencontré : {current_element.name}\n"
            # Logique de combat
            battle_result = self.battle(current_element)
            output += battle_result

        # Vérifier si le héros est mort au combat
        if self.hero.health <= 0:
            output += f"{self.hero.name} est mort. Fin de partie !\n"
            self.is_game_over = True

        return output
    
    def _add_item_to_inventory(self, item):
        """
        Ajoute un objet à l'inventaire du personnage
        """
        from init_db import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Déterminer le type_id basé sur le type d'objet
        type_mapping = {
            "healing": 1,  # Potion
            "weapon": 3,   # Arme
            "armor": 5,    # Armure
        }
        
        type_id = type_mapping.get(item.type, 1)
        
        # Vérifier si l'objet existe déjà dans l'inventaire
        cursor.execute('''
            SELECT * FROM inventory 
            WHERE character_id = ? AND name = ? AND type_id = ?
        ''', (self.hero.id, item.name, type_id))
        
        existing_item = cursor.fetchone()
        
        if existing_item:
            # Mettre à jour la quantité
            cursor.execute('''
                UPDATE inventory 
                SET quantity = quantity + 1 
                WHERE id = ?
            ''', (existing_item['id'],))
        else:
            # Ajouter un nouvel objet
            cursor.execute('''
                INSERT INTO inventory (character_id, name, type_id, quantity) 
                VALUES (?, ?, ?, ?)
            ''', (self.hero.id, item.name, type_id, 1))
        
        conn.commit()
        cursor.close()
        conn.close()

    def battle(self, monster):
        """
        Simule un combat entre le héros et un monstre
        """
        output = f"Combat entre {self.hero.name} et {monster.name}\n"

        # Stocker la santé originale du héros pour la restaurer plus tard
        original_hero_health = self.hero.health
        monster_health = monster.health  # C'est une copie locale, donc c'est ok de la modifier

        # Mécaniques de combat simples
        hero_damage = self.hero.attack
        monster_damage = monster.attack

        # Combat par tour
        while self.hero.health > 0 and monster_health > 0:
            # Le héros attaque le monstre
            monster_health -= hero_damage
            output += f"{self.hero.name} inflige {hero_damage} points de dégâts à {monster.name}\n"

            if monster_health <= 0:
                output += f"{monster.name} est vaincu !\n"
                break

            # Le monstre attaque le héros
            self.hero.health -= monster_damage
            output += f"{monster.name} inflige {monster_damage} points de dégâts à {self.hero.name}\n"

            if self.hero.health <= 0:
                output += f"{self.hero.name} est vaincu !\n"
                break

        # Mettre à jour la santé du héros dans la base de données si le héros survit
        if self.hero.health > 0:
            self._update_hero_health()
        else:
            # Si le héros meurt, mettre à jour le statut de game over
            self.is_game_over = True
            # Aussi mettre à jour la santé dans la BD
            self._update_hero_health()

        return output
    
    def _update_hero_health(self):
        """
        Met à jour la santé du héros dans la base de données
        """
        from init_db import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE characters 
            SET health = ? 
            WHERE id = ?
        ''', (self.hero.health, self.hero.id))
        
        conn.commit()
        cursor.close()
        conn.close()
