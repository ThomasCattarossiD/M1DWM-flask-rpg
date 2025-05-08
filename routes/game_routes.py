from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import json
import random

from init_db import get_db_connection
from models.game import Character, Monster, Tableau

game_bp = Blueprint('game', __name__)

@game_bp.route('/versus/', methods=['GET'])
@jwt_required()
def versus_mode():
    user_id = get_jwt_identity()
    characters = Character.get_all_by_user(user_id)
    
    character_list = []
    for char in characters:
        character_list.append({
            "id": char.id,
            "name": char.name,
            "race": char.race.value,
            "class": char.type,
            "level": char.level,
            "health": char.health,
            "attack": char.attack,
            "defense": char.defense
        })
    
    return jsonify({"characters": character_list}), 200

@game_bp.route('/versus/fight/', methods=['POST'])
@jwt_required()
def fight():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Aucune donnée fournie"}), 400
    
    player1_id = data.get('player1')
    player2_id = data.get('player2')
    
    if not player1_id or not player2_id:
        return jsonify({"error": "Deux personnages sont requis pour le combat"}), 400
    
    # Récupérer les personnages
    characters = Character.get_all_by_user(user_id)
    player1 = next((c for c in characters if c.id == player1_id), None)
    player2 = next((c for c in characters if c.id == player2_id), None)
    
    if not player1 or not player2:
        return jsonify({"error": "Personnages invalides"}), 400
    
    # Stocker les points de vie originaux avant le combat
    original_health_p1 = player1.health
    original_health_p2 = player2.health
    
    # Simuler le combat
    result_json = fight_logic(player1, player2)
    result = json.loads(result_json)
    
    # Ajouter les données originales de santé au résultat
    result["original_health"] = {
        "player1": original_health_p1,
        "player2": original_health_p2
    }
    
    # En mode Versus, nous ne modifions pas la santé réelle des personnages
    return jsonify(result), 200

@game_bp.route('/quests/', methods=['GET'])
@jwt_required()
def quest_mode():
    user = current_app.get_current_user()
    
    if not user or not user.active_character_id:
        return jsonify({"error": "Aucun personnage actif sélectionné"}), 400
    
    character = Character.get_by_id(user.active_character_id)
    
    quests = [
        {
            "id": 1,
            "name": "La Forêt Sombre",
            "difficulty": 1,
            "description": "Explorez la forêt sombre et affrontez les monstres qui s'y cachent.",
            "recommended_level": 1
        },
        {
            "id": 2,
            "name": "Les Grottes Mystérieuses",
            "difficulty": 2,
            "description": "Descendez dans les grottes mystérieuses et découvrez leurs secrets.",
            "recommended_level": 2
        },
        {
            "id": 3,
            "name": "Le Donjon du Dragon",
            "difficulty": 3,
            "description": "Affrontez le terrible dragon qui terrorise la région.",
            "recommended_level": 3
        }
    ]
    
    return jsonify({
        "character": {
            "id": character.id,
            "name": character.name,
            "level": character.level,
            "health": character.health,
            "attack": character.attack,
            "defense": character.defense
        },
        "quests": quests
    }), 200

@game_bp.route('/quests/<int:quest_id>/', methods=['POST'])
@jwt_required()
def start_quest(quest_id):
    user = current_app.get_current_user()
    
    if not user or not user.active_character_id:
        return jsonify({"error": "Aucun personnage actif sélectionné"}), 400
    
    character = Character.get_by_id(user.active_character_id)
    opponent = get_opponent_for_quest(quest_id)
    
    # Simuler le combat pour la quête
    result_json = fight_hero_vs_monster(character, opponent)
    result = json.loads(result_json)
    
    # Mettre à jour les statistiques du personnage après la quête
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if result.get("winner") == character.name:
        # Le personnage a gagné, augmenter l'expérience et éventuellement le niveau
        xp_gain = 20 * quest_id  # Plus la quête est difficile, plus on gagne d'XP
        
        # Récupérer l'expérience actuelle
        cursor.execute('SELECT experience, level FROM characters WHERE id = ?', (character.id,))
        char_data = cursor.fetchone()
        
        current_xp = char_data["experience"] or 0
        current_level = char_data["level"]
        
        new_xp = current_xp + xp_gain
        new_level = current_level
        
        # Vérifier si le personnage monte de niveau (100 XP par niveau)
        if new_xp >= current_level * 100:
            new_level = new_xp // 100 + 1
            
            # Augmenter les statistiques en fonction de la classe
            if character.type == 'warrior':
                # Guerrier: plus de défense et de santé
                cursor.execute('''
                    UPDATE characters 
                    SET level = ?, experience = ?, 
                        attack = attack + ?, defense = defense + ?,
                        health = ?
                    WHERE id = ?
                ''', (new_level, new_xp, 3, 2, min(character.health + 10, 100), character.id))
            else:
                # Mage: plus d'attaque
                cursor.execute('''
                    UPDATE characters 
                    SET level = ?, experience = ?, 
                        attack = attack + ?, defense = defense + ?,
                        health = ?
                    WHERE id = ?
                ''', (new_level, new_xp, 5, 1, min(character.health + 5, 100), character.id))
        else:
            # Mise à jour de l'XP et récupération partielle des PV
            health_recovery = 10 + quest_id * 5
            new_health = min(character.health + health_recovery, 100)
            
            cursor.execute('''
                UPDATE characters 
                SET experience = ?, health = ? 
                WHERE id = ?
            ''', (new_xp, new_health, character.id))
    else:
        # Le personnage a perdu, récupère un peu de santé mais pas d'XP
        recovery = min(20, 100 - character.health // 2)
        new_health = max(character.health // 2, 20) + recovery
        
        cursor.execute('UPDATE characters SET health = ? WHERE id = ?', 
                      (min(new_health, 100), character.id))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    # Ajouter les informations du personnage mis à jour
    character = Character.get_by_id(character.id)
    result["character"] = {
        "id": character.id,
        "name": character.name,
        "level": character.level,
        "health": character.health,
        "attack": character.attack,
        "defense": character.defense
    }
    
    return jsonify(result), 200

@game_bp.route('/board/', methods=['GET'])
@jwt_required()
def board_game():
    user = current_app.get_current_user()
    
    if not user or not user.active_character_id:
        return jsonify({"error": "Aucun personnage actif sélectionné"}), 400
    
    hero = Character.get_by_id(user.active_character_id)
    
    # Créer une nouvelle instance de jeu de plateau avec 20 cases
    tableau_game = Tableau(hero, length=20)
    
    return jsonify({
        "character": {
            "id": hero.id,
            "name": hero.name,
            "level": hero.level,
            "health": hero.health,
            "attack": hero.attack,
            "defense": hero.defense
        },
        "board": {
            "length": tableau_game.length,
            "current_position": tableau_game.current_position,
            "status": "ready"
        },
        "message": "Jeu de plateau prêt à commencer"
    }), 200

@game_bp.route('/board/play/', methods=['POST'])
@jwt_required()
def play_board_turn():
    user = current_app.get_current_user()
    
    if not user or not user.active_character_id:
        return jsonify({"error": "Aucun personnage actif sélectionné"}), 400
    
    hero = Character.get_by_id(user.active_character_id)
    data = request.get_json() or {}
    
    # Récupérer l'état actuel du jeu ou en créer un nouveau
    current_position = data.get('current_position', 0)
    tableau_game = Tableau(hero)
    tableau_game.current_position = current_position
    
    # Jouer un tour
    turn_result = tableau_game.play_turn()
    
    # Vérifier l'état du jeu
    game_status = "in_progress"
    level_up = False  # Nouvelle variable pour suivre la montée de niveau
    
    if tableau_game.is_completed:
        game_status = "completed"
        # Augmenter le niveau du personnage et rafraîchir ses statistiques
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Récupérer les données actuelles
        cursor.execute('SELECT level, experience FROM characters WHERE id = ?', (hero.id,))
        char_data = cursor.fetchone()
        
        current_level = char_data["level"]
        current_xp = char_data["experience"] or 0
        
        # Attribuer de l'XP pour avoir complété le plateau
        xp_gain = 50
        new_xp = current_xp + xp_gain
        new_level = current_level
        
        # Vérifier si le personnage monte de niveau
        if new_xp >= current_level * 100:
            new_level = new_xp // 100 + 1
            level_up = True  # Le personnage monte de niveau
        
        # Augmenter le niveau et les stats en fonction de la classe
        if level_up:
            # Si le personnage monte de niveau, restauration complète des PV + bonus de stats
            if hero.type == 'warrior':
                cursor.execute('''
                    UPDATE characters 
                    SET level = ?, experience = ?, health = 100,
                        attack = attack + ?, defense = defense + ?
                    WHERE id = ?
                ''', (new_level, new_xp, 3 * (new_level - current_level), 
                      2 * (new_level - current_level), hero.id))
            else:  # mage
                cursor.execute('''
                    UPDATE characters 
                    SET level = ?, experience = ?, health = 100,
                        attack = attack + ?, defense = defense + ?
                    WHERE id = ?
                ''', (new_level, new_xp, 5 * (new_level - current_level), 
                      1 * (new_level - current_level), hero.id))
        else:
            # Pas de montée de niveau, restauration partielle des PV (50% des PV manquants)
            health_recovery = min(50, (100 - hero.health) // 2)
            new_health = min(hero.health + health_recovery, 100)
            
            cursor.execute('''
                UPDATE characters 
                SET experience = ?, health = ?
                WHERE id = ?
            ''', (new_xp, new_health, hero.id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Recharger le héros pour obtenir les nouvelles statistiques
        hero = Character.get_by_id(hero.id)
        
    elif tableau_game.is_game_over:
        game_status = "game_over"
        
        # Remettre un minimum de santé au personnage
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE characters SET health = 50 WHERE id = ?', (hero.id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        hero = Character.get_by_id(hero.id)
    else:
        # Mettre à jour la santé du héros dans la base de données
        # même si celle-ci a été modifiée pendant le tour
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE characters SET health = ? WHERE id = ?', 
                      (min(tableau_game.hero.health, 100), hero.id))
        conn.commit()
        cursor.close()
        conn.close()
        
        hero = Character.get_by_id(hero.id)
    
    return jsonify({
        "character": {
            "id": hero.id,
            "name": hero.name,
            "health": hero.health,
            "attack": hero.attack,
            "defense": hero.defense,
            "level": hero.level
        },
        "board": {
            "length": tableau_game.length,
            "current_position": tableau_game.current_position,
            "status": game_status
        },
        "level_up": level_up,  # Nouvelle propriété pour indiquer si le niveau a augmenté
        "turn_result": turn_result
    }), 200

# Fonctions utilitaires
def fight_hero_vs_monster(hero, monster):
    """Simule un combat entre un héros et un monstre."""
    fight_data = {
        "mode": "Quest",
        "hero": {
            "name": hero.name,
            "original_health": hero.health,
        },
        "monster": {
            "name": monster.name,
            "original_health": monster.health,
        },
        "rounds": []
    }

    round = 1  # Réinitialiser le compteur de tours
    
    # Copier les attributs pour éviter de modifier les objets originaux
    hero_health = hero.health
    monster_health = monster.health

    # Combattre jusqu'à ce qu'un participant soit vaincu
    while monster_health > 0 and hero_health > 0:
        round_data = {
            "round": round,
            "hero_health": hero_health,
            "monster_health": monster_health,
        }

        # Le héros attaque le monstre
        # Calcul amélioré des dégâts en tenant compte de la défense
        damage_to_monster = max(hero.attack - monster.attack // 4, 0)  # Minimum 0
        monster_health -= damage_to_monster
        round_data["damage_to_monster"] = damage_to_monster

        if monster_health <= 0:
            round_data["winner"] = hero.name
            fight_data["winner"] = hero.name
            fight_data["rounds"].append(round_data)
            break  # Monstre vaincu

        # Le monstre riposte
        damage_to_hero = max(monster.attack - hero.defense, 0)  # Minimum 0
        hero_health -= damage_to_hero
        round_data["damage_to_hero"] = damage_to_hero

        if hero_health <= 0:
            round_data["winner"] = monster.name
            fight_data["winner"] = monster.name
            fight_data["rounds"].append(round_data)
            break  # Héros vaincu

        fight_data["rounds"].append(round_data)
        round += 1

    return json.dumps(fight_data, indent=4)

def get_opponent_for_quest(quest_id):
    """Récupère l'adversaire en fonction de l'ID de la quête."""
    if quest_id == 1:
        return Monster(name="Monstre de la Forêt", health=50, attack=10)
    elif quest_id == 2:
        return Monster(name="Troll des Cavernes", health=80, attack=15)
    elif quest_id == 3:
        return Monster(name="Dragon", health=200, attack=40)
    return Monster(name="Monstre Inconnu", health=30, attack=5)

def fight_logic(player1, player2):
    """Logique de combat améliorée entre deux personnages."""
    round = 1
    fight_data = {
        "mode": "PVP",
        "players": {
            "player1": {
                "name": player1.name,
                "original_health": player1.health,
                "id": player1.id
            },
            "player2": {
                "name": player2.name,
                "original_health": player2.health,
                "id": player2.id
            }
        },
        "rounds": []
    }

    # Copier les attributs pour éviter de modifier les objets originaux
    player1_health = player1.health
    player2_health = player2.health

    while player1_health > 0 and player2_health > 0:
        round_data = {
            "round": round,
            "player1_health": player1_health,
            "player2_health": player2_health,
        }

        # Déterminer l'initiative: qui attaque en premier
        # Ajout d'un élément de hasard pour plus de variété
        initiative_modifier = random.randint(-2, 2)
        player1_initiative = player1.attack + initiative_modifier
        player2_initiative = player2.attack + initiative_modifier
        
        if player1_initiative >= player2_initiative:
            round_data["initiative"] = player1.name

            # Player 1 attaque Player 2
            damage_to_player2 = max(player1.attack - player2.defense // 2, 0)
            player2_health -= damage_to_player2
            round_data["damage_to_player2"] = damage_to_player2

            if player2_health <= 0:
                round_data["winner"] = player1.name
                fight_data["winner"] = player1.name
                fight_data["rounds"].append(round_data)
                break

            # Player 2 riposte
            damage_to_player1 = max(player2.attack - player1.defense // 2, 0)
            player1_health -= damage_to_player1
            round_data["damage_to_player1"] = damage_to_player1

        else:
            round_data["initiative"] = player2.name

            # Player 2 attaque Player 1
            damage_to_player1 = max(player2.attack - player1.defense // 2, 0)
            player1_health -= damage_to_player1
            round_data["damage_to_player1"] = damage_to_player1

            if player1_health <= 0:
                round_data["winner"] = player2.name
                fight_data["winner"] = player2.name
                fight_data["rounds"].append(round_data)
                break

            # Player 1 riposte
            damage_to_player2 = max(player1.attack - player2.defense // 2, 0)
            player2_health -= damage_to_player2
            round_data["damage_to_player2"] = damage_to_player2

        fight_data["rounds"].append(round_data)
        round += 1

        # Limiter le nombre de tours pour éviter les combats sans fin
        if round > 20:
            # Déterminer un gagnant basé sur les PV restants en pourcentage
            p1_health_percent = player1_health / player1.health
            p2_health_percent = player2_health / player2.health
            
            if p1_health_percent > p2_health_percent:
                fight_data["winner"] = player1.name
            else:
                fight_data["winner"] = player2.name
            break

    # S'assurer qu'un gagnant est déterminé
    if "winner" not in fight_data:
        if player1_health <= 0:
            fight_data["winner"] = player2.name
        else:
            fight_data["winner"] = player1.name

    return json.dumps(fight_data, indent=4)