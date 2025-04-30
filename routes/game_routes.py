from flask import Blueprint, flash, redirect, render_template, request, url_for, jsonify
from flask_login import current_user, login_required

from init_db import get_db_connection
from models.game import Character, Item, Mage, Monster, Race, Warrior, Tableau

game_bp = Blueprint('game', __name__)

import json


@game_bp.route('/create_character', methods=['GET', 'POST'])
@login_required
def create_character():
    if request.method == 'POST':
        # Support des données JSON et form
        name = request.form.get('name') or request.json.get('name')
        race = request.form.get('race') or request.json.get('race')
        character_class = request.form.get('class') or request.json.get('class')

        if not name or not race or not character_class:
            return jsonify({"success": False, "message": "Tous les champs sont requis"}), 400

        # Créer l'instance temporaire du personnage (sans ID)
        try:
            if character_class == 'warrior':
                character = Warrior(name=name, race=Race[race.upper()])
            elif character_class == 'mage':
                character = Mage(name=name, race=Race[race.upper()])
            else:
                return jsonify({"success": False, "message": "Classe de personnage invalide"}), 400
                
            # Sauvegarder dans la base de données
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO characters (name, race, class, health, attack, defense, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (character.name, character.race.name, character.type,
                  character.health, character.attack, character.defense,
                  current_user.id))

            character_id = cursor.lastrowid
            # Mettre à jour l'ID du personnage
            character.id = character_id

            # Mettre à jour l'active_character_id de l'utilisateur
            cursor.execute('''
                UPDATE user 
                SET active_character_id = ? 
                WHERE user_id = ?
            ''', (character_id, current_user.id))

            conn.commit()
            cursor.close()
            conn.close()

            return jsonify({
                "success": True, 
                "message": "Personnage créé avec succès",
                "character": {
                    "id": character_id,
                    "name": character.name,
                    "race": character.race.name,
                    "class": character.type,
                    "health": character.health,
                    "attack": character.attack,
                    "defense": character.defense
                }
            }), 201
            
        except Exception as e:
            return jsonify({"success": False, "message": f"Erreur: {str(e)}"}), 500

    # Si c'est une requête GET, renvoyer les options disponibles
    races = [race.name for race in Race]
    classes = ["warrior", "mage"]
    
    return jsonify({
        "success": True,
        "options": {
            "races": races,
            "classes": classes
        }
    })


@game_bp.route('/select_character/<int:character_id>', methods=['POST'])
@login_required
def select_character(character_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Vérifier que le personnage appartient bien à l'utilisateur
    cursor.execute('''
        SELECT * FROM characters 
        WHERE id = ? AND user_id = ?
    ''', (character_id, current_user.id))

    character = cursor.fetchone()
    if character:
        cursor.execute('''
            UPDATE user 
            SET active_character_id = ? 
            WHERE user_id = ?
        ''', (character_id, current_user.id))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True, 
            "message": "Personnage sélectionné avec succès",
            "character_id": character_id
        })
    else:
        cursor.close()
        conn.close()
        return jsonify({"success": False, "message": "Personnage non trouvé"}), 404


@game_bp.route('/versus')
@login_required
def versus_mode():
    characters = Character.get_all_by_user(current_user.id)
    
    # Convertir les personnages en format JSON
    characters_data = []
    for char in characters:
        characters_data.append({
            "id": char.id,
            "name": char.name,
            "race": char.race.name,
            "class": char.type,
            "health": char.health,
            "attack": char.attack,
            "defense": char.defense,
            "level": char.level
        })
    
    return jsonify({
        "success": True,
        "characters": characters_data
    })


@game_bp.route('/quests')
@login_required
def quest_mode():
    if not current_user.active_character_id:
        return jsonify({
            "success": False, 
            "message": "Aucun personnage actif", 
            "redirect": "/game/create_character"
        }), 400

    character = Character.get_by_id(current_user.active_character_id)
    
    # Liste de quêtes disponibles
    quests = [
        {"id": 1, "name": "La forêt mystérieuse", "difficulty": "Facile", "enemy": "Forest Monster"},
        {"id": 2, "name": "Les cavernes obscures", "difficulty": "Moyen", "enemy": "Cave Troll"},
        {"id": 3, "name": "Le repaire du dragon", "difficulty": "Difficile", "enemy": "Dragon"}
    ]
    
    return jsonify({
        "success": True,
        "character": {
            "id": character.id,
            "name": character.name,
            "race": character.race.name,
            "class": character.type,
            "health": character.health,
            "attack": character.attack,
            "defense": character.defense,
            "level": character.level
        },
        "quests": quests
    })


def fight_hero_vs_monster(hero, monster):
    """Simulates a fight between a hero and a monster."""
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

    round = 1  # Reset round for each fight

    # Fight until one of the participants is defeated
    while monster.health > 0 and hero.health > 0:
        round_data = {
            "round": round,
            "hero_health": hero.health,
            "monster_health": monster.health,
        }

        # Hero attacks monster
        damage_to_monster = max(hero.attack, 0)  # No negative damage
        monster.health -= damage_to_monster
        round_data["damage_to_monster"] = damage_to_monster

        if monster.health <= 0:
            round_data["winner"] = hero.name
            fight_data["winner"] = hero.name
            fight_data["rounds"].append(round_data)
            break  # Monster is defeated

        # Monster retaliates
        damage_to_hero = max(monster.attack, 0)  # No negative damage
        hero.health -= damage_to_hero
        round_data["damage_to_hero"] = damage_to_hero

        if hero.health <= 0:
            round_data["winner"] = monster.name
            fight_data["winner"] = monster.name
            fight_data["rounds"].append(round_data)
            break  # Hero is defeated

        fight_data["rounds"].append(round_data)
        round += 1

    return json.dumps(fight_data, indent=4)


@game_bp.route('/quest/<int:quest_id>', methods=['POST'])
@login_required
def start_quest(quest_id):
    if not current_user.active_character_id:
        return jsonify({
            "success": False, 
            "message": "Aucun personnage actif", 
            "redirect": "/game/create_character"
        }), 400
        
    # Fetch the character and the opponent for the quest
    character = Character.get_by_id(current_user.active_character_id)
    opponent = get_opponent_for_quest(quest_id)

    # Call the quest logic (PvP battle or similar)
    result_json = fight_hero_vs_monster(character, opponent)

    # Deserialize JSON string into a dictionary
    result = json.loads(result_json)
    
    # Update character stats based on result if needed
    # (e.g., add experience, health recovery, etc.)
    
    return jsonify({
        "success": True,
        "quest_id": quest_id,
        "result": result
    })


def get_opponent_for_quest(quest_id):
    """Fetches the opponent based on the quest ID."""
    if quest_id == 1:
        return Monster(name="Forest Monster", health=50, attack=10)
    elif quest_id == 2:
        return Monster(name="Cave Troll", health=80, attack=15)
    elif quest_id == 3:
        return Monster(name="Dragon", health=200, attack=40)


@game_bp.route("/fight", methods=["POST"])
@login_required
def fight():
    # Support des données JSON et form
    player1_id = request.form.get('player1') or request.json.get('player1')
    player2_id = request.form.get('player2') or request.json.get('player2')
    
    if not player1_id or not player2_id:
        return jsonify({"success": False, "message": "IDs des deux joueurs requis"}), 400
        
    player1_id = int(player1_id)
    player2_id = int(player2_id)

    # Retrieve characters based on IDs (replace with DB query)
    characters = Character.get_all_by_user(current_user.id)
    player1 = next((c for c in characters if c.id == player1_id), None)
    player2 = next((c for c in characters if c.id == player2_id), None)

    if not player1 or not player2:
        return jsonify({"success": False, "message": "Personnages invalides"}), 400

    # Run the fight logic
    result_json = fight_logic(player1, player2)

    # Deserialize JSON string into a dictionary
    result = json.loads(result_json)

    return jsonify({
        "success": True,
        "result": result
    })


@game_bp.route('/board_game')
@login_required
def board_game():
    if not current_user.active_character_id:
        return jsonify({
            "success": False, 
            "message": "Aucun personnage actif", 
            "redirect": "/game/create_character"
        }), 400

    # Get the active character
    hero = Character.get_by_id(current_user.active_character_id)

    # Create the Tableau game instance
    tableau_game = Tableau(hero)

    # Play the entire game and get the result
    game_result = play_game(tableau_game)

    # You might want to save game results or update character stats here
    character_updated = False
    if tableau_game.is_completed:
        hero.level += 1  # Assuming you have a method to add XP
        character_updated = True
        
    # JSON for dynamic styling
    style_data = {
        "background_color": "#282c34",
        "header_color": "#61dafb",
        "button_color": "#ff5733",
        "text_color": "#ffffff",
        "font_family": "Arial, sans-serif",
        "font_size": "16px",
        "board_border": "2px solid #61dafb",
        "game_title_font_size": "2rem"
    }

    return jsonify({
        "success": True,
        "character": {
            "id": hero.id,
            "name": hero.name,
            "race": hero.race.name,
            "class": hero.type,
            "health": hero.health,
            "attack": hero.attack,
            "defense": hero.defense,
            "level": hero.level
        },
        "game_result": game_result,
        "tableau_game": {
            "current_position": tableau_game.current_position,
            "length": tableau_game.length,
            "is_completed": tableau_game.is_completed,
            "is_game_over": tableau_game.is_game_over
        },
        "character_updated": character_updated,
        "style_data": style_data
    })


def play_game(Tableau):
    """
    Play the entire tableau game
    """
    output = f"Starting Tableau Game with {Tableau.hero.name}\n"

    while Tableau.current_position < Tableau.length:
        turn_output = Tableau.play_turn()
        output += turn_output

        # Check if hero died during the game
        if Tableau.hero.health <= 0:
            output += f"{Tableau.hero.name} died. Game Over!\n"
            break

    if Tableau.current_position >= Tableau.length:
        output += f"{Tableau.hero.name} completed the tableau and gained experience!\n"

    return output


@game_bp.route('/character_profile')
@login_required
def character_profile():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM characters WHERE user_id = ? ORDER BY id DESC LIMIT 1', (current_user.id,))
    character_data = cursor.fetchone()
    cursor.close()
    conn.close()

    if character_data:
        character = Character(
            id=character_data['id'],
            name=character_data['name'],
            race=Race[character_data['race']],
            character_type=character_data['class'],
            health=character_data['health'],
            attack=character_data['attack'],
            defense=character_data['defense'],
            level=character_data['level']
        )
        
        equipment = []
        # Ici, vous pourriez récupérer l'équipement du personnage
        # Exemple fictif:
        # equipment = get_character_equipment(character.id)
        
        return jsonify({
            "success": True,
            "character": {
                "id": character.id,
                "name": character.name,
                "race": character.race.name,
                "class": character.type,
                "health": character.health,
                "attack": character.attack,
                "defense": character.defense,
                "level": character.level
            },
            "equipment": equipment
        })

    return jsonify({
        "success": False, 
        "message": "Aucun personnage trouvé", 
        "redirect": "/game/create_character"
    }), 404


@game_bp.route('/characters')
@login_required
def character_list():
    characters = Character.get_all_by_user(current_user.id)
    
    # Convertir les personnages en format JSON
    characters_data = []
    for char in characters:
        characters_data.append({
            "id": char.id,
            "name": char.name,
            "race": char.race.name,
            "class": char.type,
            "health": char.health,
            "attack": char.attack,
            "defense": char.defense,
            "level": char.level,
            "is_active": char.id == current_user.active_character_id
        })
    
    return jsonify({
        "success": True,
        "characters": characters_data,
        "active_character_id": current_user.active_character_id
    })


@game_bp.route("/start_battle", methods=["POST"])
@login_required
def start_battle():
    player1_id = request.json.get("player1")
    player2_id = request.json.get("player2")

    if not player1_id or not player2_id:
        return jsonify({"success": False, "message": "IDs des deux joueurs requis"}), 400

    # Simulate game logic
    result = f"Player 1 (Character {player1_id}) battles Player 2 (Character {player2_id})!"
    # Your actual game function would go here instead of this mock result.

    # Return the result
    return jsonify({
        "success": True,
        "result": result,
        "player1_id": player1_id,
        "player2_id": player2_id
    })


def fight_logic(player1, player2):
    round = 1
    fight_data = {
        "mode": "PVP",
        "players": {
            "player1": {
                "name": player1.name,
                "original_health": player1.health,
            },
            "player2": {
                "name": player2.name,
                "original_health": player2.health,
            }
        },
        "rounds": []
    }

    original_player1_health = player1.health
    original_player2_health = player2.health

    while player1.health > 0 and player2.health > 0:
        round_data = {
            "round": round,
            "player1_health": player1.health,
            "player2_health": player2.health,
        }

        # Determine initiative: Who attacks first
        if player1.attack > player2.attack:
            round_data["initiative"] = player1.name

            damage_to_player2 = max(player1.attack - player2.defense, 0)  # Attack - defense, cannot be negative
            player2.health -= damage_to_player2
            round_data["damage_to_player2"] = damage_to_player2

            if player2.health <= 0:
                round_data["winner"] = player1.name
                fight_data["winner"] = player1.name
                fight_data["rounds"].append(round_data)
                break

            damage_to_player1 = max(player2.attack - player1.defense, 0)
            player1.health -= damage_to_player1
            round_data["damage_to_player1"] = damage_to_player1
        else:
            round_data["initiative"] = player2.name

            damage_to_player1 = max(player2.attack - player1.defense, 0)
            player1.health -= damage_to_player1
            round_data["damage_to_player1"] = damage_to_player1

            if player1.health <= 0:
                round_data["winner"] = player2.name
                fight_data["winner"] = player2.name
                fight_data["rounds"].append(round_data)
                break

            damage_to_player2 = max(player1.attack - player2.defense, 0)
            player2.health -= damage_to_player2
            round_data["damage_to_player2"] = damage_to_player2

        fight_data["rounds"].append(round_data)
        round += 1

    # Reset player health for future battles (optional)
    player1.health = original_player1_health
    player2.health = original_player2_health

    return json.dumps(fight_data, indent=4)

@game_bp.route('/characters', methods=['GET'])
@login_required
def get_characters():
    """
    Récupérer tous les personnages de l'utilisateur connecté sous format JSON
    pour l'API React
    """
    characters = Character.get_all_by_user(current_user.id)
    characters_data = []
    
    for character in characters:
        characters_data.append({
            'id': character.id,
            'name': character.name,
            'race': character.race.name if hasattr(character.race, 'name') else str(character.race),
            'class': character.type,
            'health': character.health,
            'attack': character.attack,
            'defense': character.defense,
            'level': character.level
        })
    
    return jsonify(characters_data)


@game_bp.route('/character_profile', methods=['GET'])
@login_required
def get_character_profile():
    """
    Récupérer les détails du personnage actif pour l'API React
    """
    if not current_user.active_character_id:
        return jsonify({'error': 'Aucun personnage actif'}), 404
    
    character = Character.get_by_id(current_user.active_character_id)
    
    if not character:
        return jsonify({'error': 'Personnage non trouvé'}), 404
    
    character_data = {
        'id': character.id,
        'name': character.name,
        'race': character.race.name if hasattr(character.race, 'name') else str(character.race),
        'class': character.type,
        'health': character.health,
        'attack': character.attack,
        'defense': character.defense,
        'level': character.level
    }
    
    return jsonify(character_data)


@game_bp.route('/quest/<int:quest_id>/details', methods=['GET'])
@login_required
def get_quest_details(quest_id):
    """
    Récupérer les détails d'une quête spécifique pour l'API React
    """
    quests = {
        1: {
            'id': 1,
            'title': 'Forêt Enchantée',
            'description': 'Explorez la forêt mystérieuse et affrontez le monstre qui y rôde.',
            'difficulty': 'Facile',
            'reward': "50 pièces d'or, 1 potion de santé",
            'monster': 'Monstre de la forêt',
            'monsterHealth': 50,
            'monsterAttack': 10,
        },
        2: {
            'id': 2,
            'title': 'Cavernes Sombres',
            'description': 'Descendez dans les profondeurs des cavernes et combattez le troll qui terrorise les mineurs.',
            'difficulty': 'Moyen',
            'reward': "100 pièces d'or, 1 équipement rare",
            'monster': 'Troll des cavernes',
            'monsterHealth': 80,
            'monsterAttack': 15,
        },
        3: {
            'id': 3,
            'title': 'Montagne du Dragon',
            'description': 'Escaladez la montagne périlleuse et affrontez le dragon ancestral qui y sommeille.',
            'difficulty': 'Difficile',
            'reward': "300 pièces d'or, 1 arme légendaire",
            'monster': 'Dragon',
            'monsterHealth': 200,
            'monsterAttack': 40,
        }
    }
    
    if quest_id not in quests:
        return jsonify({'error': 'Quête non trouvée'}), 404
    
    return jsonify(quests[quest_id])


@game_bp.route('/item_types', methods=['GET'])
@login_required
def get_item_types():
    """
    Récupérer la liste des types d'objets disponibles
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, type_name FROM item_types')
    item_types = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return jsonify([{'id': t['id'], 'type_name': t['type_name']} for t in item_types])


@game_bp.route('/item/<int:item_id>', methods=['GET'])
@login_required
def get_item_details(item_id):
    """
    Récupérer les détails d'un objet spécifique
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Vérifier que l'objet appartient au personnage actif
    cursor.execute('''
        SELECT inventory.id, inventory.name, inventory.type_id, inventory.quantity 
        FROM inventory 
        WHERE inventory.id = ? AND inventory.character_id = ?
    ''', (item_id, current_user.active_character_id))
    
    item = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not item:
        return jsonify({'error': 'Objet non trouvé'}), 404
    
    item_data = {
        'id': item['id'],
        'name': item['name'],
        'type_id': item['type_id'],
        'quantity': item['quantity']
    }
    
    return jsonify(item_data)


@game_bp.route('/quests/available', methods=['GET'])
@login_required
def get_available_quests():
    """
    Récupérer la liste des quêtes disponibles pour le personnage actif
    """
    if not current_user.active_character_id:
        return jsonify({'error': 'Aucun personnage actif'}), 400
    
    character = Character.get_by_id(current_user.active_character_id)
    character_level = character.level if character else 1
    
    # Dans une application réelle, vous récupéreriez les quêtes depuis la base de données
    # et filtreriez en fonction du niveau du personnage
    quests = [
        {
            'id': 1,
            'title': 'Forêt Enchantée',
            'description': 'Explorez la forêt mystérieuse et affrontez le monstre qui y rôde.',
            'difficulty': 'Facile',
            'minLevel': 1,
        },
        {
            'id': 2,
            'title': 'Cavernes Sombres',
            'description': 'Descendez dans les profondeurs des cavernes et combattez le troll.',
            'difficulty': 'Moyen',
            'minLevel': 3,
        },
        {
            'id': 3,
            'title': 'Montagne du Dragon',
            'description': 'Escaladez la montagne périlleuse et affrontez le dragon ancestral.',
            'difficulty': 'Difficile',
            'minLevel': 5,
        }
    ]
    
    # Marquer les quêtes comme disponibles ou non en fonction du niveau
    for quest in quests:
        quest['available'] = character_level >= quest['minLevel']
    
    return jsonify(quests)


@game_bp.route('/board_game/result', methods=['GET'])
@login_required
def get_board_game_result():
    """
    Obtenir le résultat du jeu de plateau pour le personnage actif
    """
    if not current_user.active_character_id:
        return jsonify({'error': 'Aucun personnage actif'}), 400
    
    hero = Character.get_by_id(current_user.active_character_id)
    
    if not hero:
        return jsonify({'error': 'Personnage non trouvé'}), 404
    
    # Créer une instance du jeu de plateau
    tableau_game = Tableau(hero)
    
    # Jouer le jeu et obtenir le résultat
    game_result = play_game(tableau_game)
    
    # Mettre à jour le personnage si nécessaire
    if tableau_game.is_completed and not tableau_game.is_game_over:
        # Le personnage a terminé le jeu avec succès
        hero.level += 1
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE characters SET level = ? WHERE id = ?', (hero.level, hero.id))
        conn.commit()
        cursor.close()
        conn.close()
    
    result_data = {
        'character': {
            'id': hero.id,
            'name': hero.name,
            'health': hero.health,
            'level': hero.level,
        },
        'game_completed': tableau_game.is_completed,
        'game_over': tableau_game.is_game_over,
        'position': tableau_game.current_position,
        'board_length': tableau_game.length,
        'result_text': game_result
    }
    
    return jsonify(result_data)
