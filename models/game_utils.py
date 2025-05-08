import json
import random
from enum import Enum
from init_db import get_db_connection

class GameStatus(Enum):
    """Statut possible pour une session de jeu"""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    GAME_OVER = "game_over"

class LevelManager:
    """Gère les calculs liés aux niveaux, à l'expérience et aux statistiques des personnages"""
    
    @staticmethod
    def xp_for_level(level):
        """Calcule l'XP nécessaire pour atteindre un niveau donné"""
        return level * 100
    
    @staticmethod
    def level_from_xp(xp):
        """Calcule le niveau correspondant à une quantité d'XP"""
        return 1 + (xp // 100)
    
    @staticmethod
    def stats_increase_for_level(character_type, levels_gained=1):
        """Calcule l'augmentation de statistiques pour une montée de niveau"""
        if character_type == 'warrior':
            return {
                'attack': 3 * levels_gained,
                'defense': 2 * levels_gained,
                'health': 10 * levels_gained
            }
        elif character_type == 'mage':
            return {
                'attack': 5 * levels_gained,
                'defense': 1 * levels_gained,
                'health': 5 * levels_gained
            }
        else:
            # Valeurs par défaut pour un type de personnage inconnu
            return {
                'attack': 2 * levels_gained,
                'defense': 2 * levels_gained,
                'health': 8 * levels_gained
            }

class CombatManager:
    """Gère les mécaniques de combat"""
    
    @staticmethod
    def calculate_damage(attacker, defender):
        """Calcule les dégâts infligés par l'attaquant au défenseur"""
        base_damage = max(attacker.attack - defender.defense, 0)
        
        # 10% de chance de coup critique (dégâts doublés)
        if random.random() < 0.1:
            base_damage *= 2
            critical = True
        else:
            critical = False
            
        # Variation aléatoire des dégâts (+/- 20%)
        damage_variation = random.uniform(0.8, 1.2)
        final_damage = round(base_damage * damage_variation)
        
        return {
            "damage": final_damage,
            "critical": critical
        }
    
    @staticmethod
    def log_battle(battle_data, character_id=None, battle_type="pvp"):
        """Enregistre les détails d'un combat dans la base de données"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if battle_type == "pvp":
            player1_id = battle_data.get("players", {}).get("player1", {}).get("id")
            player2_id = battle_data.get("players", {}).get("player2", {}).get("id")
            winner_id = player1_id if battle_data.get("winner") == battle_data.get("players", {}).get("player1", {}).get("name") else player2_id
            
            cursor.execute('''
                INSERT INTO pvp_battles (player1_id, player2_id, winner_id, battle_data)
                VALUES (?, ?, ?, ?)
            ''', (player1_id, player2_id, winner_id, json.dumps(battle_data)))
        elif battle_type == "quest" and character_id:
            quest_id = battle_data.get("quest_id")
            success = 1 if battle_data.get("winner") == battle_data.get("hero", {}).get("name") else 0
            
            cursor.execute('''
                INSERT INTO completed_quests (character_id, quest_id, success, quest_data)
                VALUES (?, ?, ?, ?)
            ''', (character_id, quest_id, success, json.dumps(battle_data)))
        
        conn.commit()
        cursor.close()
        conn.close()

class RewardManager:
    """Gère les récompenses de quêtes et d'événements"""
    
    @staticmethod
    def generate_random_item(level=1, item_type=None):
        """Génère un objet aléatoire basé sur le niveau"""
        # Types d'objets possibles
        possible_types = ["weapon", "armor", "potion", "accessory"]
        
        if not item_type:
            item_type = random.choice(possible_types)
        
        # Préfixes et suffixes pour la génération de noms
        prefixes = {
            "weapon": ["Épée", "Hache", "Dague", "Masse", "Lance"],
            "armor": ["Armure", "Bouclier", "Casque", "Gantelet", "Bottes"],
            "potion": ["Potion", "Élixir", "Philtre", "Tonique", "Décoction"],
            "accessory": ["Amulette", "Anneau", "Pendentif", "Bracelet", "Talisman"]
        }
        
        qualities = ["", "de qualité", "supérieur", "exceptionnel", "légendaire"]
        materials = ["de fer", "d'acier", "de mithril", "en cuir", "en tissu", "en bois"]
        
        # Effets basés sur le type
        effects = {
            "weapon": [f"+{level * 2 + random.randint(1, 5)} atk", f"+{level + random.randint(1, 3)} def"],
            "armor": [f"+{level + random.randint(1, 5)} def", f"+{level * 2} hp"],
            "potion": [f"+{level * 10 + random.randint(5, 15)} hp", f"+{level * 2} atk temporaire"],
            "accessory": [f"+{level} à toutes les stats", f"+{level * 3} chance", f"+{level * 2} vitesse"]
        }
        
        # Générer le nom
        prefix = random.choice(prefixes.get(item_type, ["Objet"]))
        quality = random.choice(qualities) if random.random() < 0.7 else ""
        material = random.choice(materials) if random.random() < 0.5 else ""
        
        parts = [prefix]
        if quality:
            parts.append(quality)
        if material:
            parts.append(material)
            
        name = " ".join(parts)
        effect = random.choice(effects.get(item_type, [f"+{level} à une stat aléatoire"]))
        
        return {
            "name": name,
            "type": item_type,
            "effect": effect,
            "level": level
        }
    
    @staticmethod
    def award_quest_completion(character, quest_difficulty, quest_xp):
        """Attribue les récompenses pour la complétion d'une quête"""
        # Ajouter de l'XP
        character.add_experience(quest_xp)
        
        # Générer un objet aléatoire comme récompense
        item = RewardManager.generate_random_item(level=quest_difficulty)
        
        # Ajouter l'objet à l'inventaire du personnage
        from models.game import Item
        item_id = Item.add_to_character(
            character.id,
            item["name"],
            item["type"],
            item["effect"]
        )
        
        # Déterminer si le personnage a monté de niveau
        level_before = LevelManager.level_from_xp(character.experience - quest_xp)
        level_after = LevelManager.level_from_xp(character.experience)
        leveled_up = level_after > level_before
        
        return {
            "xp_gained": quest_xp,
            "level_up": leveled_up,
            "new_level": level_after if leveled_up else None,
            "item_reward": {
                "id": item_id,
                "name": item["name"],
                "type": item["type"],
                "effect": item["effect"]
            }
        }

class GameEventManager:
    """Gère les événements aléatoires du jeu"""
    
    @staticmethod
    def generate_random_event(character, event_type=None, difficulty=1):
        """Génère un événement aléatoire"""
        possible_events = ["combat", "treasure", "trap", "merchant", "rest"]
        
        if not event_type:
            event_type = random.choice(possible_events)
        
        if event_type == "combat":
            return GameEventManager._generate_combat_event(character, difficulty)
        elif event_type == "treasure":
            return GameEventManager._generate_treasure_event(character, difficulty)
        elif event_type == "trap":
            return GameEventManager._generate_trap_event(character, difficulty)
        elif event_type == "merchant":
            return GameEventManager._generate_merchant_event(character, difficulty)
        elif event_type == "rest":
            return GameEventManager._generate_rest_event(character, difficulty)
        else:
            return {"type": "unknown", "description": "Un événement mystérieux se produit..."}
    
    @staticmethod
    def _generate_combat_event(character, difficulty):
        """Génère un événement de combat"""
        enemy_types = ["bandit", "gobelin", "squelette", "loup", "troll"]
        enemy_type = random.choice(enemy_types)
        
        enemy_health = 20 + (difficulty * 10) + random.randint(-5, 10)
        enemy_attack = 5 + (difficulty * 2) + random.randint(-2, 4)
        
        return {
            "type": "combat",
            "description": f"Vous rencontrez un {enemy_type} hostile !",
            "enemy": {
                "name": f"{enemy_type.capitalize()} de niveau {difficulty}",
                "health": enemy_health,
                "attack": enemy_attack
            }
        }
    
    @staticmethod
    def _generate_treasure_event(character, difficulty):
        """Génère un événement de trésor"""
        item = RewardManager.generate_random_item(level=difficulty)
        gold = 10 * difficulty + random.randint(1, 20)
        
        return {
            "type": "treasure",
            "description": f"Vous trouvez un coffre au trésor !",
            "rewards": {
                "gold": gold,
                "item": item
            }
        }
    
    @staticmethod
    def _generate_trap_event(character, difficulty):
        """Génère un événement de piège"""
        trap_types = ["fosse", "fléchettes", "gaz toxique", "explosion", "filet"]
        trap_type = random.choice(trap_types)
        
        damage = 5 + (difficulty * 3) + random.randint(0, 5)
        
        return {
            "type": "trap",
            "description": f"Vous déclenchez un piège à {trap_type} !",
            "effects": {
                "damage": damage,
                "escape_difficulty": 5 + difficulty * 2
            }
        }
    
    @staticmethod
    def _generate_merchant_event(character, difficulty):
        """Génère un événement de marchand"""
        items_for_sale = []
        
        # Générer 3 objets à vendre
        for _ in range(3):
            item = RewardManager.generate_random_item(level=difficulty)
            item["price"] = 20 * difficulty + random.randint(5, 20)
            items_for_sale.append(item)
        
        return {
            "type": "merchant",
            "description": "Vous rencontrez un marchand ambulant.",
            "merchant": {
                "name": f"Marchand itinérant",
                "items": items_for_sale
            }
        }
    
    @staticmethod
    def _generate_rest_event(character, difficulty):
        """Génère un événement de repos"""
        health_recovery = 10 + (difficulty * 2)
        
        return {
            "type": "rest",
            "description": "Vous trouvez un endroit sûr pour vous reposer.",
            "effects": {
                "health_recovery": health_recovery
            }
        }