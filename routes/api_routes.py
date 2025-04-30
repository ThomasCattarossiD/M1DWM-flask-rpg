from flask import Blueprint, jsonify, request, current_app, make_response
from flask_login import login_required, current_user
from flask_cors import cross_origin
import json
from datetime import datetime

from init_db import get_db_connection
from models.game import Character, Monster, Race, Warrior, Mage

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/health', methods=['GET', 'OPTIONS'])
@cross_origin()
def health_check():
    """
    Simple endpoint pour vérifier que l'API est en ligne
    """
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response, 200
    
    return jsonify({
        "status": "ok",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }), 200

@api_bp.route('/user/current', methods=['GET', 'OPTIONS'])
@cross_origin()
@login_required
def current_user_info():
    """
    Renvoie les informations de l'utilisateur connecté
    """
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response, 200
    
    if not current_user.is_authenticated:
        return jsonify({
            "success": False,
            "message": "Non authentifié"
        }), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Récupérer les informations de l'utilisateur
        cursor.execute('SELECT user_id, user_login, user_mail, active_character_id FROM user WHERE user_id = ?', 
                      (current_user.id,))
        user_data = cursor.fetchone()
        
        # Récupérer le nombre de personnages
        cursor.execute('SELECT COUNT(*) as character_count FROM characters WHERE user_id = ?', 
                      (current_user.id,))
        character_count = cursor.fetchone()['character_count']
        
        # Si un personnage actif est défini, récupérer ses informations de base
        active_character = None
        if user_data['active_character_id']:
            cursor.execute('SELECT id, name, race, class, level FROM characters WHERE id = ?', 
                          (user_data['active_character_id'],))
            char_data = cursor.fetchone()
            if char_data:
                active_character = {
                    "id": char_data['id'],
                    "name": char_data['name'],
                    "race": char_data['race'],
                    "class": char_data['class'],
                    "level": char_data['level']
                }
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "user": {
                "id": user_data['user_id'],
                "username": user_data['user_login'],
                "email": user_data['user_mail'],
                "active_character_id": user_data['active_character_id'],
                "active_character": active_character,
                "character_count": character_count
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching user data: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Erreur serveur: {str(e)}"
        }), 500

@api_bp.route('/auth/login', methods=['POST', 'OPTIONS'])
@cross_origin()
def api_login():
    """
    Point d'entrée API pour la connexion
    """
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response, 200
    
    from flask_bcrypt import Bcrypt
    from flask_login import login_user
    
    bcrypt = Bcrypt()
    
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({
                "success": False,
                "message": "Email et mot de passe requis"
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM user WHERE user_mail = ?', (email,))
        user_data = cursor.fetchone()
        
        if not user_data:
            cursor.close()
            conn.close()
            return jsonify({
                "success": False,
                "message": "Email ou mot de passe incorrect"
            }), 401
        
        if not bcrypt.check_password_hash(user_data['user_password'], password):
            cursor.close()
            conn.close()
            return jsonify({
                "success": False,
                "message": "Email ou mot de passe incorrect"
            }), 401
        
        from models.user import User
        user = User(
            user_data['user_id'], 
            user_data['user_login'], 
            user_data['user_mail'],
            user_data['active_character_id']
        )
        login_user(user)
        
        # Récupérer le nombre de personnages
        cursor.execute('SELECT COUNT(*) as character_count FROM characters WHERE user_id = ?', 
                      (user_data['user_id'],))
        character_count = cursor.fetchone()['character_count']
        
        # Si un personnage actif est défini, récupérer ses informations de base
        active_character = None
        if user_data['active_character_id']:
            cursor.execute('SELECT id, name, race, class, level FROM characters WHERE id = ?', 
                          (user_data['active_character_id'],))
            char_data = cursor.fetchone()
            if char_data:
                active_character = {
                    "id": char_data['id'],
                    "name": char_data['name'],
                    "race": char_data['race'],
                    "class": char_data['class'],
                    "level": char_data['level']
                }
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Connexion réussie",
            "user": {
                "id": user_data['user_id'],
                "username": user_data['user_login'],
                "email": user_data['user_mail'],
                "active_character_id": user_data['active_character_id'],
                "active_character": active_character,
                "character_count": character_count
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Login error: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Erreur serveur: {str(e)}"
        }), 500

@api_bp.route('/auth/register', methods=['POST', 'OPTIONS'])
@cross_origin()
def api_register():
    """
    Point d'entrée API pour l'inscription
    """
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response, 200
    
    from flask_bcrypt import Bcrypt
    from flask_login import login_user
    
    bcrypt = Bcrypt()
    
    try:
        data = request.get_json()
        email = data.get('email')
        username = data.get('username')
        password = data.get('password')
        
        if not email or not username or not password:
            return jsonify({
                "success": False,
                "message": "Tous les champs sont obligatoires"
            }), 400
        
        # Validation basique du format email
        if '@' not in email or '.' not in email:
            return jsonify({
                "success": False,
                "message": "Format d'email invalide"
            }), 400
            
        # Validation de la longueur du mot de passe
        if len(password) < 6:
            return jsonify({
                "success": False,
                "message": "Le mot de passe doit contenir au moins 6 caractères"
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Vérifier si l'email existe déjà
        cursor.execute('SELECT * FROM user WHERE user_mail = ?', (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({
                "success": False,
                "message": "Cet email est déjà utilisé"
            }), 400
        
        # Vérifier si le nom d'utilisateur existe déjà
        cursor.execute('SELECT * FROM user WHERE user_login = ?', (username,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({
                "success": False,
                "message": "Ce nom d'utilisateur est déjà utilisé"
            }), 400
        
        # Hacher le mot de passe
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # Insérer le nouvel utilisateur
        cursor.execute(
            'INSERT INTO user (user_login, user_password, user_mail) VALUES (?, ?, ?)',
            (username, hashed_password, email)
        )
        conn.commit()
        
        # Récupérer l'ID de l'utilisateur créé
        user_id = cursor.lastrowid
        
        # Connecter l'utilisateur
        from models.user import User
        user = User(user_id, username, email)
        login_user(user)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Compte créé avec succès",
            "user": {
                "id": user_id,
                "username": username,
                "email": email,
                "active_character_id": None,
                "character_count": 0
            }
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Registration error: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Erreur serveur: {str(e)}"
        }), 500

@api_bp.route('/auth/logout', methods=['POST', 'OPTIONS'])
@cross_origin()
@login_required
def api_logout():
    """
    Point d'entrée API pour la déconnexion
    """
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200
    
    from flask_login import logout_user
    
    try:
        logout_user()
        return jsonify({
            "success": True,
            "message": "Déconnexion réussie"
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Logout error: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Erreur serveur: {str(e)}"
        }), 500

@api_bp.route('/characters', methods=['GET', 'OPTIONS'])
@cross_origin()
@login_required
def get_characters():
    """
    Récupère la liste des personnages de l'utilisateur
    """
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response, 200
    
    try:
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
        
        characters = []
        for char_data in characters_data:
            characters.append({
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
            })
        
        return jsonify({
            "success": True,
            "characters": characters
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching characters: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Erreur serveur: {str(e)}"
        }), 500

@api_bp.route('/characters', methods=['POST', 'OPTIONS'])
@cross_origin()
@login_required
def create_character():
    """
    Crée un nouveau personnage pour l'utilisateur
    """
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response, 200
    
    try:
        data = request.get_json()
        name = data.get('name')
        race = data.get('race')
        character_class = data.get('class')
        
        if not name or not race or not character_class:
            return jsonify({
                "success": False,
                "message": "Tous les champs sont obligatoires"
            }), 400
            
        # Valider la race et la classe
        valid_races = [r.name.lower() for r in Race]
        valid_classes = ['warrior', 'mage']
        
        if race.lower() not in valid_races:
            return jsonify({
                "success": False,
                "message": f"Race invalide. Valeurs possibles: {', '.join(valid_races)}"
            }), 400
            
        if character_class.lower() not in valid_classes:
            return jsonify({
                "success": False,
                "message": f"Classe invalide. Valeurs possibles: {', '.join(valid_classes)}"
            }), 400
        
        # Créer l'instance du personnage
        if character_class.lower() == 'warrior':
            character = Warrior(name=name, race=Race[race.upper()])
        elif character_class.lower() == 'mage':
            character = Mage(name=name, race=Race[race.upper()])
        
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
        character.id = character_id
        
        # Créer les statistiques du joueur
        cursor.execute('''
            INSERT INTO player_stats (character_id, battles_won, battles_lost, monsters_defeated, quests_completed, items_collected)
            VALUES (?, 0, 0, 0, 0, 0)
        ''', (character_id,))
        
        # Mettre à jour l'active_character_id de l'utilisateur s'il n'a pas déjà un personnage actif
        cursor.execute('SELECT active_character_id FROM user WHERE user_id = ?', (current_user.id,))
        if not cursor.fetchone()['active_character_id']:
            cursor.execute('UPDATE user SET active_character_id = ? WHERE user_id = ?', 
                          (character_id, current_user.id))
            current_user.active_character_id = character_id
        
        # Ajouter des objets de départ selon la classe
        starter_items = []
        if character_class.lower() == 'warrior':
            starter_items = [
                ('Épée en fer', 1, 1, "Une épée basique mais solide"),
                ('Armure en cuir', 2, 1, "Une armure légère offrant une protection minimale"),
                ('Potion de soin', 3, 2, "Restaure 20 points de vie")
            ]
        elif character_class.lower() == 'mage':
            starter_items = [
                ('Baguette en bois', 4, 1, "Une baguette simple qui canalise la magie"),
                ('Robe de mage', 2, 1, "Une robe légère imprégnée d'énergie magique"),
                ('Potion de mana', 3, 2, "Restaure 20 points de mana")
            ]
        
        for item_name, type_id, quantity, description in starter_items:
            cursor.execute('''
                INSERT INTO inventory (character_id, name, type_id, quantity, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (character_id, item_name, type_id, quantity, description))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Personnage créé avec succès",
            "character": {
                "id": character.id,
                "name": character.name,
                "race": character.race.name,
                "class": character.type,
                "health": character.health,
                "attack": character.attack,
                "defense": character.defense,
                "level": 1,
                "experience": 0,
                "is_active": current_user.active_character_id == character.id
            }
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error creating character: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Erreur serveur: {str(e)}"
        }), 500

@api_bp.route('/character/<int:character_id>', methods=['GET', 'OPTIONS'])
@cross_origin()
@login_required
def get_character(character_id):
    """
    Récupère les détails d'un personnage spécifique
    """
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response, 200
    
    try:
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
            return jsonify({
                "success": False,
                "message": "Personnage non trouvé ou accès non autorisé"
            }), 404
        
        # Récupérer l'inventaire du personnage
        cursor.execute('''
            SELECT i.id, i.name, i.quantity, i.description, t.id as type_id, t.type_name
            FROM inventory i
            JOIN item_types t ON i.type_id = t.id
            WHERE i.character_id = ?
        ''', (character_id,))
        
        inventory_items = cursor.fetchall()
        
        # Récupérer les statistiques du personnage
        cursor.execute('''
            SELECT * FROM player_stats
            WHERE character_id = ?
        ''', (character_id,))
        
        stats_data = cursor.fetchone() or {}
        
        cursor.close()
        conn.close()
        
        # Préparer les données du personnage
        character = {
            'id': character_data['id'],
            'name': character_data['name'],
            'race': character_data['race'],
            'class': character_data['class'],
            'health': character_data['health'],
            'attack': character_data['attack'],
            'defense': character_data['defense'],
            'level': character_data['level'],
            'experience': character_data['experience'],
            'is_active': character_data['id'] == character_data['active_character_id']
        }
        
        # Préparer les données de l'inventaire
        inventory = []
        for item in inventory_items:
            inventory.append({
                'id': item['id'],
                'name': item['name'],
                'type_id': item['type_id'],
                'type': item['type_name'],
                'quantity': item['quantity'],
                'description': item['description'] or ""
            })
        
        # Préparer les statistiques
        stats = {
            'battles_won': stats_data.get('battles_won', 0),
            'battles_lost': stats_data.get('battles_lost', 0),
            'monsters_defeated': stats_data.get('monsters_defeated', 0),
            'quests_completed': stats_data.get('quests_completed', 0),
            'items_collected': stats_data.get('items_collected', 0)
        }
        
        return jsonify({
            "success": True,
            "character": character,
            "inventory": inventory,
            "stats": stats
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching character details: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Erreur serveur: {str(e)}"
        }), 500

@api_bp.route('/character/<int:character_id>/select', methods=['POST', 'OPTIONS'])
@cross_origin()
@login_required
def select_character(character_id):
    """
    Définit un personnage comme personnage actif
    """
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Vérifier que le personnage appartient à l'utilisateur
        cursor.execute('''
            SELECT * FROM characters 
            WHERE id = ? AND user_id = ?
        ''', (character_id, current_user.id))
        
        character = cursor.fetchone()
        
        if not character:
            cursor.close()
            conn.close()
            return jsonify({
                "success": False,
                "message": "Personnage non trouvé ou accès non autorisé"
            }), 404
        
        # Mettre à jour le personnage actif
        cursor.execute('''
            UPDATE user 
            SET active_character_id = ? 
            WHERE user_id = ?
        ''', (character_id, current_user.id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Mettre à jour la session de l'utilisateur
        current_user.active_character_id = character_id
        
        return jsonify({
            "success": True,
            "message": "Personnage sélectionné avec succès",
            "character_id": character_id
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error selecting character: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Erreur serveur: {str(e)}"
        }), 500

@api_bp.route('/quests', methods=['GET', 'OPTIONS'])
@cross_origin()
@login_required
def get_quests():
    """
    Récupère la liste des quêtes disponibles
    """
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response, 200
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Récupérer le niveau du personnage actif
        character_level = 1
        if current_user.active_character_id:
            cursor.execute('SELECT level FROM characters WHERE id = ?', (current_user.active_character_id,))
            char_data = cursor.fetchone()
            if char_data:
                character_level = char_data['level']
        
        # Récupérer les quêtes adaptées au niveau
        cursor.execute('''
            SELECT q.*,
                   (SELECT COUNT(*) FROM completed_quests cq 
                    WHERE cq.quest_id = q.id AND cq.character_id = ?) as is_completed
            FROM quests q
            WHERE q.level_required <= ?
            ORDER BY q.level_required ASC, q.id ASC
        ''', (current_user.active_character_id or 0, character_level))
        
        quests_data = cursor.fetchall()
        cursor.close()
        conn.close()
        
        quests = []
        for quest in quests_data:
            quests.append({
                'id': quest['id'],
                'title': quest['title'],
                'description': quest['description'],
                'level_required': quest['level_required'],
                'experience_reward': quest['experience_reward'],
                'gold_reward': quest['gold_reward'],
                'is_completed': quest['is_completed'] > 0
            })
        
        return jsonify({
            "success": True,
            "quests": quests,
            "active_character": {
                "id": current_user.active_character_id,
                "level": character_level
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching quests: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Erreur serveur: {str(e)}"
        }), 500

@api_bp.route('/quest/<int:quest_id>', methods=['POST', 'OPTIONS'])
@cross_origin()
@login_required
def start_quest(quest_id):
    """
    Démarre une quête pour le personnage actif
    """
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response, 200
    
    if not current_user.active_character_id:
        return jsonify({
            "success": False,
            "message": "Veuillez d'abord sélectionner un personnage"
        }), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Vérifier que la quête existe et que le niveau du personnage est suffisant
        cursor.execute('''
            SELECT q.*, c.level
            FROM quests q, characters c
            WHERE q.id = ? AND c.id = ?
        ''', (quest_id, current_user.active_character_id))
        
        data = cursor.fetchone()
        
        if not data:
            cursor.close()
            conn.close()
            return jsonify({
                "success": False,
                "message": "Quête ou personnage non trouvé"
            }), 404
        
        if data['level_required'] > data['level']:
            cursor.close()
            conn.close()
            return jsonify({
                "success": False,
                "message": f"Niveau insuffisant. Niveau requis: {data['level_required']}"
            }), 400
        
        # Vérifier si la quête a déjà été complétée
        cursor.execute('''
            SELECT * FROM completed_quests
            WHERE quest_id = ? AND character_id = ?
        ''', (quest_id, current_user.active_character_id))
        
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({
                "success": False,
                "message": "Cette quête a déjà été complétée"
            }), 400
        
        # Récupérer le personnage
        cursor.execute('SELECT * FROM characters WHERE id = ?', (current_user.active_character_id,))
        char_data = cursor.fetchone()
        
        character = Character(
            id=char_data['id'],
            name=char_data['name'],
            race=Race[char_data['race'].upper()],
            character_type=char_data['class'],
            health=char_data['health'],
            attack=char_data['attack'],
            defense=char_data['defense'],
            level=char_data['level']
        )
        
        # Récupérer ou créer le monstre pour cette quête
        monster = get_opponent_for_quest(quest_id)
        
        # Simuler le combat
        result_json = fight_hero_vs_monster(character, monster)
        result = json.loads(result_json)
        
        # Gérer le résultat
        if result.get('winner') == character.name:
            # Le personnage a gagné
            # Mettre à jour l'expérience et les statistiques
            cursor.execute('''
                UPDATE characters
                SET experience = experience + ?,
                    level = CASE 
                        WHEN experience + ? >= level * 100 THEN level + 1 
                        ELSE level 
                    END
                WHERE id = ?
            ''', (data['experience_reward'], data['experience_reward'], character.id))
            
            # Ajouter la quête aux quêtes complétées
            cursor.execute('''
                INSERT INTO completed_quests (character_id, quest_id, completed_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (character.id, quest_id))
            
            # Mettre à jour les statistiques
            cursor.execute('''
                UPDATE player_stats
                SET quests_completed = quests_completed + 1,
                    monsters_defeated = monsters_defeated + 1,
                    battles_won = battles_won + 1
                WHERE character_id = ?
            ''', (character.id,))
            
            # Ajouter une récompense aléatoire à l'inventaire
            cursor.execute('''
                SELECT * FROM item_types
                ORDER BY RANDOM() LIMIT 1
            ''')
            item_type = cursor.fetchone()
            
            item_names = {
                1: ["Épée de bronze", "Épée d'acier", "Hache de guerre", "Masse lourde"],
                2: ["Cape de voyageur", "Armure de cuir", "Bouclier en bois", "Casque en fer"],
                3: ["Potion de guérison", "Élixir de force", "Potion de vitalité", "Fiole de soins"],
                4: ["Bâton magique", "Tome de sorts", "Baguette arcanique", "Orbe mystique"]
            }
            
            if item_type and item_type['id'] in item_names:
                from random import choice
                item_name = choice(item_names[item_type['id']])
                
                cursor.execute('''
                    INSERT INTO inventory (character_id, name, type_id, quantity, description)
                    VALUES (?, ?, ?, 1, "Récompense de quête")
                ''', (character.id, item_name, item_type['id']))
                
                cursor.execute('''
                    UPDATE player_stats
                    SET items_collected = items_collected + 1
                    WHERE character_id = ?
                ''', (character.id,))
            
            # Résultat de quête réussie
            quest_result = {
                "success": True,
                "battle_result": result,
                "rewards": {
                    "experience": data['experience_reward'],
                    "gold": data['gold_reward'],
                    "item": item_name if item_type else None
                },
                "quest_completed": True
            }
        else:
            # Le personnage a perdu
            cursor.execute('''
                UPDATE player_stats
                SET battles_lost = battles_lost + 1
                WHERE character_id = ?
            ''', (character.id,))
            
            # Résultat de quête échouée
            quest_result = {
                "success": False,
                "battle_result": result,
                "quest_completed": False
            }
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify(quest_result), 200
        
    except Exception as e:
        current_app.logger.error(f"Error during quest: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Erreur serveur: {str(e)}"
        }), 500

@api_bp.route('/versus', methods=['POST', 'OPTIONS'])
@cross_origin()
@login_required
def versus_battle():
    """
    Démarre un combat entre deux personnages de l'utilisateur
    """
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response, 200
    
    try:
        data = request.get_json()
        player1_id = data.get('player1_id')
        player2_id = data.get('player2_id')
        
        if not player1_id or not player2_id:
            return jsonify({
                "success": False,
                "message": "Les identifiants des deux personnages sont requis"
            }), 400
        
        # Vérifier que les personnages appartiennent à l'utilisateur
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM characters 
            WHERE id IN (?, ?) AND user_id = ?
        ''', (player1_id, player2_id, current_user.id))
        
        characters_data = cursor.fetchall()
        
        if len(characters_data) != 2:
            cursor.close()
            conn.close()
            return jsonify({
                "success": False,
                "message": "Un ou plusieurs personnages sont introuvables ou n'appartiennent pas à l'utilisateur"
            }), 404
        
        # Créer les instances de personnage
        player1 = None
        player2 = None
        
        for char_data in characters_data:
            character = Character(
                id=char_data['id'],
                name=char_data['name'],
                race=Race[char_data['race'].upper()],
                character_type=char_data['class'],
                health=char_data['health'],
                attack=char_data['attack'],
                defense=char_data['defense'],
                level=char_data['level']
            )
            
            if char_data['id'] == player1_id:
                player1 = character
            else:
                player2 = character
        
        # Simuler le combat
        result_json = fight_logic(player1, player2)
        result = json.loads(result_json)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "battle_result": result
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error during versus battle: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Erreur serveur: {str(e)}"
        }), 500

@api_bp.route('/items', methods=['GET', 'OPTIONS'])
@cross_origin()
@login_required
def get_items():
    """
    Récupère la liste des types d'objets disponibles
    """
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response, 200
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM item_types')
        item_types = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        items = []
        for item in item_types:
            items.append({
                'id': item['id'],
                'name': item['type_name'],
                'description': item.get('description', "")
            })
        
        return jsonify({
            "success": True,
            "item_types": items
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching item types: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Erreur serveur: {str(e)}"
        }), 500

# Fonction utilitaire pour récupérer un opponent pour une quête
def get_opponent_for_quest(quest_id):
    """Récupère l'adversaire basé sur l'ID de la quête."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM quests
            WHERE id = ?
        ''', (quest_id,))
        
        quest_data = cursor.fetchone()
        
        if not quest_data:
            cursor.close()
            conn.close()
            # Retourner un monstre par défaut si la quête n'existe pas
            return Monster(
                name="Monstre inconnu",
                health=50,
                attack=10
            )
        
        # Vérifier si un monstre spécifique est défini pour cette quête
        cursor.execute('''
            SELECT * FROM quest_monsters
            WHERE quest_id = ?
        ''', (quest_id,))
        
        monster_data = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if monster_data:
            return Monster(
                name=monster_data['name'],
                health=monster_data['health'],
                attack=monster_data['attack']
            )
        else:
            # Générer un monstre basé sur le niveau de la quête
            level = quest_data['level_required']
            monsters_by_level = {
                1: {"name": "Gobelin", "base_health": 30, "base_attack": 5},
                2: {"name": "Loup sauvage", "base_health": 40, "base_attack": 8},
                3: {"name": "Bandit", "base_health": 50, "base_attack": 10},
                4: {"name": "Ogre", "base_health": 70, "base_attack": 12},
                5: {"name": "Troll des montagnes", "base_health": 90, "base_attack": 15},
                6: {"name": "Démon mineur", "base_health": 110, "base_attack": 18},
                7: {"name": "Dragon de glace", "base_health": 140, "base_attack": 22},
                8: {"name": "Seigneur des ténèbres", "base_health": 180, "base_attack": 25},
                9: {"name": "Behemoth", "base_health": 220, "base_attack": 30},
                10: {"name": "Dragon ancestral", "base_health": 300, "base_attack": 35}
            }
            
            monster_template = monsters_by_level.get(level, {"name": f"Monstre niveau {level}", "base_health": 20 + level * 10, "base_attack": 3 + level * 2})
            
            # Ajouter un peu d'aléatoire à la puissance du monstre
            import random
            health_variation = random.uniform(0.9, 1.1)
            attack_variation = random.uniform(0.9, 1.1)
            
            return Monster(
                name=monster_template["name"],
                health=int(monster_template["base_health"] * health_variation),
                attack=int(monster_template["base_attack"] * attack_variation)
            )
    
    except Exception as e:
        current_app.logger.error(f"Error creating opponent for quest: {str(e)}")
        return Monster(
            name="Monstre d'erreur",
            health=50,
            attack=10
        )

def fight_logic(player1, player2):
    """Simule un combat entre deux personnages."""
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

        # Déterminer l'initiative: Qui attaque en premier
        if player1.attack > player2.attack:
            round_data["initiative"] = player1.name

            damage_to_player2 = max(player1.attack - player2.defense//2, 0)
            player2.health -= damage_to_player2
            round_data["damage_to_player2"] = damage_to_player2

            if player2.health <= 0:
                round_data["winner"] = player1.name
                fight_data["winner"] = player1.name
                fight_data["rounds"].append(round_data)
                break

            damage_to_player1 = max(player2.attack - player1.defense//2, 0)
            player1.health -= damage_to_player1
            round_data["damage_to_player1"] = damage_to_player1

        else:
            round_data["initiative"] = player2.name

            damage_to_player1 = max(player2.attack - player1.defense//2, 0)
            player1.health -= damage_to_player1
            round_data["damage_to_player1"] = damage_to_player1

            if player1.health <= 0:
                round_data["winner"] = player2.name
                fight_data["winner"] = player2.name
                fight_data["rounds"].append(round_data)
                break

            damage_to_player2 = max(player1.attack - player2.defense//2, 0)
            player2.health -= damage_to_player2
            round_data["damage_to_player2"] = damage_to_player2

        fight_data["rounds"].append(round_data)
        round += 1

    # Réinitialiser la santé des joueurs pour les futurs combats
    player1.health = original_player1_health
    player2.health = original_player2_health

    return json.dumps(fight_data, indent=4)

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
        damage_to_hero = max(monster.attack - hero.defense//2, 0)
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

