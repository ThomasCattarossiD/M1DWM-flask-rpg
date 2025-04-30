import sqlite3
from flask import Blueprint, flash, redirect, render_template, request, url_for, jsonify, current_app, make_response
from flask_login import current_user, login_required
from flask_cors import CORS, cross_origin

from init_db import get_db_connection
from models.game import Character, Item, Mage, Monster, Race, Warrior, Tableau

import json

game_bp = Blueprint('game', __name__)

# Fonction utilitaire pour répondre à la fois en JSON et HTML
def respond(is_json, json_data=None, html_template=None, html_data=None, html_redirect=None, flash_message=None, flash_category=None, status=200):
    if flash_message and flash_category:
        flash(flash_message, flash_category)
    
    if is_json:
        return jsonify(json_data), status
    
    if html_redirect:
        return redirect(html_redirect)
    
    return render_template(html_template, **html_data if html_data else {})

@game_bp.route('/create_character', methods=['GET', 'POST', 'OPTIONS'])
@cross_origin()
@login_required
def create_character():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response, 200
    
    is_json = request.is_json
    
    if request.method == 'POST':
        try:
            # Récupération des données
            if is_json:
                data = request.get_json()
                name = data.get('name')
                race = data.get('race')
                character_class = data.get('class')
            else:
                name = request.form.get('name')
                race = request.form.get('race')
                character_class = request.form.get('class')
            
            # Validation
            if not name or not race or not character_class:
                return respond(
                    is_json,
                    json_data={"success": False, "message": "Tous les champs sont obligatoires"},
                    html_template='game/create_character.html',
                    flash_message="Tous les champs sont obligatoires",
                    flash_category="danger",
                    status=400
                )
            
            # Création du personnage
            try:
                race_enum = Race[race.upper()]
            except KeyError:
                return respond(
                    is_json,
                    json_data={"success": False, "message": f"Race invalide: {race}"},
                    html_template='game/create_character.html',
                    flash_message=f"Race invalide: {race}",
                    flash_category="danger",
                    status=400
                )
            
            if character_class == 'warrior':
                character = Warrior(name=name, race=race_enum)
            elif character_class == 'mage':
                character = Mage(name=name, race=race_enum)
            else:
                return respond(
                    is_json,
                    json_data={"success": False, "message": f"Classe invalide: {character_class}"},
                    html_template='game/create_character.html',
                    flash_message=f"Classe invalide: {character_class}",
                    flash_category="danger",
                    status=400
                )
            
            # Sauvegarde en BDD
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT INTO characters (name, race, class, health, attack, defense, user_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (character.name, character.race.name, character.type,
                      character.health, character.attack, character.defense,
                      current_user.id))
                
                character_id = cursor.lastrowid
                character.id = character_id
                
                cursor.execute('''
                    UPDATE user 
                    SET active_character_id = ? 
                    WHERE user_id = ?
                ''', (character_id, current_user.id))
                
                # Créer une entrée dans player_stats
                cursor.execute('''
                    INSERT INTO player_stats (character_id)
                    VALUES (?)
                ''', (character_id,))
                
                conn.commit()
                
                return respond(
                    is_json,
                    json_data={"success": True, "message": "Personnage créé avec succès", "character_id": character_id},
                    html_redirect=url_for('game.character_profile'),
                    flash_message="Personnage créé avec succès",
                    flash_category="success"
                )
            except Exception as e:
                conn.rollback()
                current_app.logger.error(f"Database error: {str(e)}")
                
                return respond(
                    is_json,
                    json_data={"success": False, "message": f"Erreur de base de données: {str(e)}"},
                    html_template='game/create_character.html',
                    flash_message=f"Erreur de base de données: {str(e)}",
                    flash_category="danger",
                    status=500
                )
            finally:
                cursor.close()
                conn.close()
                
        except Exception as e:
            current_app.logger.error(f"Error in create_character: {str(e)}")
            
            return respond(
                is_json,
                json_data={"success": False, "message": f"Erreur serveur: {str(e)}"},
                html_template='game/create_character.html',
                flash_message=f"Erreur serveur: {str(e)}",
                flash_category="danger",
                status=500
            )
    
    # GET request
    return render_template('game/create_character.html')

@game_bp.route('/select_character/<int:character_id>', methods=['POST', 'OPTIONS'])
@cross_origin()
@login_required
def select_character(character_id):
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response, 200
    
    is_json = request.is_json
    
    conn = get_db_connection()
    cursor = conn.cursor()

    # Vérifier que le personnage appartient bien à l'utilisateur
    cursor.execute('''
        SELECT * FROM characters 
        WHERE id = ? AND user_id = ?
    ''', (character_id, current_user.id))

    if cursor.fetchone():
        cursor.execute('''
            UPDATE user 
            SET active_character_id = ? 
            WHERE user_id = ?
        ''', (character_id, current_user.id))
        conn.commit()
        
        if is_json:
            cursor.execute('SELECT name FROM characters WHERE id = ?', (character_id,))
            character = cursor.fetchone()
            cursor.close()
            conn.close()
            
            return jsonify({
                "success": True, 
                "message": "Personnage sélectionné avec succès",
                "character_id": character_id,
                "character_name": character['name'] if character else ""
            }), 200
        
        flash('Personnage sélectionné avec succès!', 'success')
    else:
        if is_json:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "Personnage non trouvé"}), 404
        
        flash('Personnage non trouvé.', 'error')

    cursor.close()
    conn.close()
    return redirect(url_for('game.character_list'))

@game_bp.route('/versus', methods=['GET', 'OPTIONS'])
@cross_origin()
@login_required
def versus_mode():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response, 200
    
    characters = Character.get_all_by_user(current_user.id)
    
    if request.is_json or request.headers.get('Accept') == 'application/json':
        characters_data = []
        for character in characters:
            characters_data.append({
                'id': character.id,
                'name': character.name,
                'race': character.race.name,
                'class': character.type,
                'health': character.health,
                'attack': character.attack,
                'defense': character.defense,
                'level': character.level
            })
        
        return jsonify({
            "success": True,
            "characters": characters_data
        }), 200
    
    return render_template('game/versus.html', characters=characters)

@game_bp.route('/quests', methods=['GET', 'OPTIONS'])
@cross_origin()
@login_required
def quest_mode():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response, 200
    
    is_json = request.is_json or request.headers.get('Accept') == 'application/json'
    
    if not current_user.active_character_id:
        if is_json:
            return jsonify({
                "success": False,
                "message": "Veuillez d'abord créer ou sélectionner un personnage"
            }), 400
        
        flash('Veuillez d\'abord créer ou sélectionner un personnage.', 'warning')
        return redirect(url_for('game.create_character'))

    character = Character.get_by_id(current_user.active_character_id)
    
    # Récupérer les quêtes disponibles
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Récupérer toutes les quêtes adaptées au niveau du personnage
    cursor.execute('''
        SELECT q.id, q.title, q.description, q.level_required, 
               q.experience_reward, q.gold_reward
        FROM quests q
        WHERE q.level_required <= ?
        ORDER BY q.level_required ASC
    ''', (character.level,))
    
    quests = cursor.fetchall()
    
    # Convertir les Row en dictionnaires
    quests_data = []
    for quest in quests:
        # Récupérer les monstres pour cette quête
        cursor.execute('''
            SELECT m.name, m.health, m.attack, m.level, qm.quantity
            FROM quest_monsters qm
            JOIN monsters m ON qm.monster_id = m.id
            WHERE qm.quest_id = ?
        ''', (quest['id'],))
        
        monsters = cursor.fetchall()
        monsters_data = []
        
        for monster in monsters:
            monsters_data.append({
                'name': monster['name'],
                'health': monster['health'],
                'attack': monster['attack'],
                'level': monster['level'],
                'quantity': monster['quantity']
            })
        
        # Récupérer les récompenses pour cette quête
        cursor.execute('''
            SELECT qr.name, it.type_name, qr.quantity
            FROM quest_rewards qr
            JOIN item_types it ON qr.type_id = it.id
            WHERE qr.quest_id = ?
        ''', (quest['id'],))
        
        rewards = cursor.fetchall()
        rewards_data = []
        
        for reward in rewards:
            rewards_data.append({
                'name': reward['name'],
                'type': reward['type_name'],
                'quantity': reward['quantity']
            })
        
        # Ajouter la quête à la liste
        quests_data.append({
            'id': quest['id'],
            'title': quest['title'],
            'description': quest['description'],
            'level_required': quest['level_required'],
            'experience_reward': quest['experience_reward'],
            'gold_reward': quest['gold_reward'],
            'monsters': monsters_data,
            'rewards': rewards_data
        })
    
    cursor.close()
    conn.close()
    
    if is_json:
        return jsonify({
            "success": True,
            "character": {
                "id": character.id,
                "name": character.name,
                "level": character.level,
                "health": character.health
            },
            "quests": quests_data
        }), 200
    
    return render_template('game/quests.html', character=character, quests=quests_data)

@game_bp.route('/start_quest/<int:quest_id>', methods=['POST', 'OPTIONS'])
@cross_origin()
@login_required
def start_quest(quest_id):
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response, 200
    
    is_json = request.is_json or request.headers.get('Accept') == 'application/json'
    
    if not current_user.active_character_id:
        if is_json:
            return jsonify({
                "success": False,
                "message": "Veuillez d'abord sélectionner un personnage"
            }), 400
        
        flash('Veuillez d\'abord sélectionner un personnage.', 'warning')
        return redirect(url_for('game.character_list'))
    
    # Récupérer le personnage et l'adversaire pour la quête
    character = Character.get_by_id(current_user.active_character_id)
    
    if not character:
        if is_json:
            return jsonify({
                "success": False,
                "message": "Personnage non trouvé"
            }), 404
        
        flash('Personnage non trouvé.', 'error')
        return redirect(url_for('game.character_list'))
    
    # Vérifier que la quête existe et est disponible pour le niveau du personnage
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM quests
        WHERE id = ? AND level_required <= ?
    ''', (quest_id, character.level))
    
    quest = cursor.fetchone()
    
    if not quest:
        cursor.close()
        conn.close()
        
        if is_json:
            return jsonify({
                "success": False,
                "message": "Quête non disponible pour votre niveau"
            }), 403
        
        flash('Quête non disponible pour votre niveau.', 'warning')
        return redirect(url_for('game.quest_mode'))
    
    # Récupérer tous les monstres de la quête
    cursor.execute('''
        SELECT m.*, qm.quantity
        FROM quest_monsters qm
        JOIN monsters m ON qm.monster_id = m.id
        WHERE qm.quest_id = ?
    ''', (quest_id,))
    
    quest_monsters = cursor.fetchall()
    
    # Simuler le combat contre tous les monstres
    all_fights = []
    quest_completed = True
    
    original_character_health = character.health
    
    for quest_monster in quest_monsters:
        for i in range(quest_monster['quantity']):
            # Créer l'instance du monstre
            monster = Monster(
                name=quest_monster['name'],
                health=quest_monster['health'],
                attack=quest_monster['attack']
            )
            
            # Simuler le combat
            fight_result_json = fight_hero_vs_monster(character, monster)
            fight_result = json.loads(fight_result_json)
            
            all_fights.append(fight_result)
            
            # Vérifier si le héros a perdu
            if fight_result.get('winner') != character.name:
                quest_completed = False
                break
        
        if not quest_completed:
            break
    
    # Mise à jour des stats et récompenses si la quête est réussie
    if quest_completed:
        # Ajouter l'expérience
        cursor.execute('''
            UPDATE characters
            SET experience = experience + ?, level = CASE
                WHEN experience + ? >= level * 100 THEN level + 1
                ELSE level
                END
            WHERE id = ?
        ''', (quest['experience_reward'], quest['experience_reward'], character.id))
        
        # Ajouter les récompenses d'objets à l'inventaire
        cursor.execute('''
            SELECT qr.name, qr.type_id, qr.quantity
            FROM quest_rewards qr
            WHERE qr.quest_id = ?
        ''', (quest_id,))
        
        rewards = cursor.fetchall()
        
        for reward in rewards:
            # Vérifier si l'objet existe déjà dans l'inventaire
            cursor.execute('''
                SELECT id, quantity FROM inventory
                WHERE character_id = ? AND name = ? AND type_id = ?
            ''', (character.id, reward['name'], reward['type_id']))
            
            existing_item = cursor.fetchone()
            
            if existing_item:
                # Mettre à jour la quantité
                cursor.execute('''
                    UPDATE inventory
                    SET quantity = quantity + ?
                    WHERE id = ?
                ''', (reward['quantity'], existing_item['id']))
            else:
                # Ajouter un nouvel objet
                cursor.execute('''
                    INSERT INTO inventory (character_id, name, type_id, quantity)
                    VALUES (?, ?, ?, ?)
                ''', (character.id, reward['name'], reward['type_id'], reward['quantity']))
        
        # Enregistrer la quête comme complétée
        try:
            cursor.execute('''
                INSERT INTO completed_quests (character_id, quest_id)
                VALUES (?, ?)
            ''', (character.id, quest_id))
        except sqlite3.IntegrityError:
            # La quête a déjà été complétée par ce personnage
            pass
        
        # Mettre à jour les statistiques du joueur
        cursor.execute('''
            UPDATE player_stats
            SET quests_completed = quests_completed + 1,
                monsters_defeated = monsters_defeated + ?
            WHERE character_id = ?
        ''', (sum(qm['quantity'] for qm in quest_monsters), character.id))
        
        conn.commit()
        
        # Récupérer le niveau mis à jour du personnage
        cursor.execute('''
            SELECT level FROM characters WHERE id = ?
        ''', (character.id,))
        
        updated_character = cursor.fetchone()
        character.level = updated_character['level']
        
        # Restaurer la santé du personnage après la quête
        cursor.execute('''
            UPDATE characters
            SET health = ?
            WHERE id = ?
        ''', (original_character_health, character.id))
        
        conn.commit()
    else:
        # Restaurer la santé du personnage même si la quête échoue
        cursor.execute('''
            UPDATE characters
            SET health = ?
            WHERE id = ?
        ''', (original_character_health, character.id))
        
        # Mettre à jour les statistiques en cas d'échec
        cursor.execute('''
            UPDATE player_stats
            SET battles_lost = battles_lost + 1
            WHERE character_id = ?
        ''', (character.id,))
        
        conn.commit()
    
    cursor.close()
    conn.close()
    
    # Construire la réponse
    result = {
        "success": True,
        "quest_completed": quest_completed,
        "quest": {
            "id": quest['id'],
            "title": quest['title'],
            "experience_reward": quest['experience_reward'] if quest_completed else 0,
        },
        "character": {
            "id": character.id,
            "name": character.name,
            "level": character.level,
        },
        "fights": all_fights
    }
    
    if is_json:
        return jsonify(result), 200
    
    return render_template('game/quest_result.html', result=result)

@game_bp.route('/character_profile', methods=['GET', 'OPTIONS'])
@cross_origin()
@login_required
def character_profile():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response, 200
    
    is_json = request.is_json or request.headers.get('Accept') == 'application/json'
    
    # Si un ID de personnage est spécifié, afficher ce personnage, sinon prendre le personnage actif
    character_id = request.args.get('id')
    if character_id:
        character_id = int(character_id)
    else:
        character_id = current_user.active_character_id
    
    if not character_id:
        if is_json:
            return jsonify({
                "success": False,
                "message": "Aucun personnage sélectionné"
            }), 404
        
        flash('Aucun personnage sélectionné.', 'warning')
        return redirect(url_for('game.character_list'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Vérifier que le personnage appartient à l'utilisateur
    cursor.execute('''
        SELECT c.*, u.active_character_id
        FROM characters c
        JOIN user u ON c.user_id = u.user_id
        WHERE c.id = ? AND c.user_id = ?
    ''', (character_id, current_user.id))
    
    character_data = cursor.fetchone()
    
    if not character_data:
        cursor.close()
        conn.close()
        
        if is_json:
            return jsonify({
                "success": False,
                "message": "Personnage non trouvé"
            }), 404
        
        flash('Personnage non trouvé.', 'error')
        return redirect(url_for('game.character_list'))
    
    # Récupérer les statistiques du personnage
    cursor.execute('''
        SELECT * FROM player_stats
        WHERE character_id = ?
    ''', (character_id,))
    
    stats_data = cursor.fetchone() or {}
    
    # Récupérer les objets équipés
    cursor.execute('''
        SELECT e.slot, i.name, i.id as item_id, it.type_name
        FROM equipped_items e
        JOIN inventory i ON e.inventory_id = i.id
        JOIN item_types it ON i.type_id = it.id
        WHERE e.character_id = ?
    ''', (character_id,))
    
    equipped_items = cursor.fetchall()
    
    # Récupérer les quêtes complétées
    cursor.execute('''
        SELECT q.title, cq.completed_at
        FROM completed_quests cq
        JOIN quests q ON cq.quest_id = q.id
        WHERE cq.character_id = ?
        ORDER BY cq.completed_at DESC
    ''', (character_id,))
    
    completed_quests = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    # Créer le personnage avec les données récupérées
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
    
    # Préparer les données pour la réponse
    is_active = character_data['active_character_id'] == character_id
    
    # Pour les quêtes complétées, formater les données
    completed_quests_data = []
    for quest in completed_quests:
        completed_quests_data.append({
            'title': quest['title'],
            'completed_at': quest['completed_at']
        })
    
    # Pour les objets équipés, formater les données
    equipment_data = {}
    for item in equipped_items:
        equipment_data[item['slot']] = {
            'name': item['name'],
            'type': item['type_name'],
            'id': item['item_id']
        }
    
    # Statistiques
    stats = {
        'battles_won': stats_data.get('battles_won', 0),
        'battles_lost': stats_data.get('battles_lost', 0),
        'monsters_defeated': stats_data.get('monsters_defeated', 0),
        'quests_completed': stats_data.get('quests_completed', 0),
        'items_collected': stats_data.get('items_collected', 0)
    }
    
    if is_json:
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
                "level": character.level,
                "experience": character_data['experience'],
                "is_active": is_active
            },
            "stats": stats,
            "equipment": equipment_data,
            "completed_quests": completed_quests_data
        }), 200
    
    return render_template('game/character_profile.html', 
                          character=character, 
                          stats=stats,
                          equipment=equipment_data,
                          completed_quests=completed_quests_data,
                          is_active=is_active)

@game_bp.route('/characters', methods=['GET', 'OPTIONS'])
@cross_origin()
@login_required
def character_list():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response, 200
    
    is_json = request.is_json or request.headers.get('Accept') == 'application/json'
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Récupérer tous les personnages de l'utilisateur
    cursor.execute('''
        SELECT c.*, u.active_character_id
        FROM characters c
        JOIN user u ON c.user_id = u.user_id
        WHERE c.user_id = ?
        ORDER BY c.level DESC, c.name ASC
    ''', (current_user.id,))
    
    characters_data = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not characters_data:
        if is_json:
            return jsonify({
                "success": True,
                "message": "Aucun personnage trouvé",
                "characters": []
            }), 200
        
        flash('Vous n\'avez pas encore créé de personnage.', 'info')
        return redirect(url_for('game.create_character'))
    
    # Transformer les données en objets Character
    characters = []
    for char_data in characters_data:
        character = {
            'id': char_data['id'],
            'name': char_data['name'],
            'race': char_data['race'],
            'class': char_data['class'],
            'health': char_data['health'],
            'attack': char_data['attack'],
            'defense': char_data['defense'],
            'level': char_data['level'],
            'experience': char_data['experience'],
            'is_active': char_data['id'] == char_data['active_character_id']
        }
        characters.append(character)
    
    if is_json:
        return jsonify({
            "success": True,
            "characters": characters
        }), 200
    
    return render_template('game/character_list.html', characters=characters)

@game_bp.route('/fight', methods=['POST', 'OPTIONS'])
@cross_origin()
@login_required
def fight():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response, 200
    
    is_json = request.is_json or request.headers.get('Accept') == 'application/json'
    
    try:
        if is_json:
            data = request.get_json()
            player1_id = int(data.get('player1'))
            player2_id = int(data.get('player2'))
        else:
            player1_id = int(request.form.get('player1'))
            player2_id = int(request.form.get('player2'))
        
        # Récupérer les personnages par ID
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Vérifier que les personnages appartiennent à l'utilisateur
        cursor.execute('''
            SELECT * FROM characters
            WHERE id IN (?, ?) AND user_id = ?
        ''', (player1_id, player2_id, current_user.id))
        
        characters_data = cursor.fetchall()
        
        if len(characters_data) != 2:
            cursor.close()
            conn.close()
            
            if is_json:
                return jsonify({
                    "success": False,
                    "message": "Personnages invalides"
                }), 400
            
            flash('Personnages invalides.', 'error')
            return redirect(url_for('game.versus_mode'))
        
        # Créer les objets Character
        player1 = next((Character(
            id=c['id'],
            name=c['name'],
            race=Race[c['race']],
            character_type=c['class'],
            health=c['health'],
            attack=c['attack'],
            defense=c['defense'],
            level=c['level']
        ) for c in characters_data if c['id'] == player1_id), None)
        
        player2 = next((Character(
            id=c['id'],
            name=c['name'],
            race=Race[c['race']],
            character_type=c['class'],
            health=c['health'],
            attack=c['attack'],
            defense=c['defense'],
            level=c['level']
        ) for c in characters_data if c['id'] == player2_id), None)
        
        # Exécuter la logique de combat
        result_json = fight_logic(player1, player2)
        result = json.loads(result_json)
        
        # Mettre à jour les statistiques
        winner_id = player1_id if result.get('winner') == player1.name else player2_id
        loser_id = player2_id if winner_id == player1_id else player1_id
        
        cursor.execute('''
            UPDATE player_stats
            SET battles_won = battles_won + 1
            WHERE character_id = ?
        ''', (winner_id,))
        
        cursor.execute('''
            UPDATE player_stats
            SET battles_lost = battles_lost + 1
            WHERE character_id = ?
        ''', (loser_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        if is_json:
            return jsonify({
                "success": True,
                "result": result
            }), 200
        
        return render_template('game/fight_result.html', result=result)
    
    except Exception as e:
        current_app.logger.error(f"Error in fight: {str(e)}")
        
        if is_json:
            return jsonify({
                "success": False,
                "message": f"Erreur: {str(e)}"
            }), 500
        
        flash(f'Erreur: {str(e)}', 'error')
        return redirect(url_for('game.versus_mode'))

@game_bp.route('/board_game', methods=['GET', 'POST', 'OPTIONS'])
@cross_origin()
@login_required
def board_game():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response, 200
    
    is_json = request.is_json or request.headers.get('Accept') == 'application/json'
    
    if not current_user.active_character_id:
        if is_json:
            return jsonify({
                "success": False,
                "message": "Veuillez d'abord sélectionner un personnage"
            }), 400
        
        flash('Veuillez d\'abord créer ou sélectionner un personnage.', 'warning')
        return redirect(url_for('game.character_list'))
    
    # Récupérer le personnage actif
    hero = Character.get_by_id(current_user.active_character_id)
    
    if not hero:
        if is_json:
            return jsonify({
                "success": False,
                "message": "Personnage non trouvé"
            }), 404
        
        flash('Personnage non trouvé.', 'error')
        return redirect(url_for('game.character_list'))
    
    # Si c'est une requête POST, jouer un tour
    if request.method == 'POST':
        # Créer le jeu de tableau
        tableau_game = Tableau(hero)
        
        # Récupérer le tableau du jeu en cours depuis la session ou en créer un nouveau
        game_state = request.get_json().get('game_state') if request.is_json else None
        
        if game_state:
            tableau_game.from_dict(game_state)
        
        # Jouer un tour
        turn_result = tableau_game.play_turn()
        game_result = turn_result
        
        # Vérifier si le jeu est terminé
        is_completed = tableau_game.is_completed
        is_game_over = tableau_game.is_game_over
        
        if is_completed:
            # Mettre à jour le personnage en cas de victoire
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE characters
                SET level = level + 1,
                    attack = attack + 2,
                    defense = defense + 1,
                    health = health + 10
                WHERE id = ?
            ''', (hero.id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            game_result += f"\nFélicitations ! {hero.name} a complété le tableau et a gagné un niveau !\n"
        
        elif is_game_over:
            game_result += f"\n{hero.name} est mort durant le jeu. Game Over!\n"
        
        if is_json:
            return jsonify({
                "success": True,
                "turn_result": turn_result,
                "game_state": tableau_game.to_dict(),
                "is_completed": is_completed,
                "is_game_over": is_game_over
            }), 200
        
        # Styles pour le rendu HTML
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
        
        return render_template('game/board_game.html',
                              character=hero,
                              game_result=game_result,
                              tableau_game=tableau_game,
                              style_data=style_data)
    
    # Pour GET, afficher le jeu initial
    tableau_game = Tableau(hero)
    
    if is_json:
        return jsonify({
            "success": True,
            "character": {
                "id": hero.id,
                "name": hero.name
            },
            "game_state": tableau_game.to_dict()
        }), 200
    
    # JSON pour le style dynamique
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
    
    return render_template('game/board_game.html',
                         character=hero,
                         game_result="",
                         tableau_game=tableau_game,
                         style_data=style_data)

# Fonctions utilitaires
def play_game(tableau):
    """
    Jouer le jeu de tableau complet
    """
    output = f"Starting Tableau Game with {tableau.hero.name}\n"
    
    while tableau.current_position < tableau.length:
        turn_output = tableau.play_turn()
        output += turn_output
        
        if tableau.hero.health <= 0:
            output += f"{tableau.hero.name} died. Game Over!\n"
            break
    
    if tableau.current_position >= tableau.length:
        output += f"{tableau.hero.name} completed the tableau and gained experience!\n"
    
    return output

def fight_hero_vs_monster(hero, monster):
    """Simule un combat entre un héros et un monstre."""
    original_hero_health = hero.health
    original_monster_health = monster.health
    
    fight_data = {
        "mode": "Quest",
        "hero": {
            "name": hero.name,
            "original_health": original_hero_health,
        },
        "monster": {
            "name": monster.name,
            "original_health": original_monster_health,
        },
        "rounds": []
    }

    round = 1

    while monster.health > 0 and hero.health > 0:
        round_data = {
            "round": round,
            "hero_health": hero.health,
            "monster_health": monster.health,
        }

        # Héros attaque monstre
        damage_to_monster = max(hero.attack, 0)
        monster.health -= damage_to_monster
        round_data["damage_to_monster"] = damage_to_monster

        if monster.health <= 0:
            round_data["winner"] = hero.name
            fight_data["winner"] = hero.name
            fight_data["rounds"].append(round_data)
            break

        # Monstre riposte
        damage_to_hero = max(monster.attack, 0)
        hero.health -= damage_to_hero
        round_data["damage_to_hero"] = damage_to_hero

        if hero.health <= 0:
            round_data["winner"] = monster.name
            fight_data["winner"] = monster.name
            fight_data["rounds"].append(round_data)
            break

        fight_data["rounds"].append(round_data)
        round += 1
    
    # Restaurer la santé pour les futurs combats
    hero.health = original_hero_health
    monster.health = original_monster_health

    return json.dumps(fight_data, indent=4)

def fight_logic(player1, player2):
    """Simule un combat PvP entre deux personnages."""
    original_player1_health = player1.health
    original_player2_health = player2.health
    
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

    while player1.health > 0 and player2.health > 0:
        round_data = {
            "round": round,
            "player1_health": player1.health,
            "player2_health": player2.health,
        }

        # Déterminer l'initiative: qui attaque en premier
        if player1.attack > player2.attack:
            round_data["initiative"] = player1.name

            damage_to_player2 = max(player1.attack - player2.defense, 0)
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

        # Vérifier la fin du tour
        if player1.health <= 0:
            round_data["winner"] = player2.name
            fight_data["winner"] = player2.name
            fight_data["rounds"].append(round_data)
            break
            
        if player2.health <= 0:
            round_data["winner"] = player1.name
            fight_data["winner"] = player1.name
            fight_data["rounds"].append(round_data)
            break

        fight_data["rounds"].append(round_data)
        round += 1

    # Restaurer la santé pour les futurs combats
    player1.health = original_player1_health
    player2.health = original_player2_health

    return json.dumps(fight_data, indent=4)
