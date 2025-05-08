from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from init_db import get_db_connection
from models.game import Character, Race, Warrior, Mage

character_bp = Blueprint('characters', __name__)

@character_bp.route('/', methods=['GET'])
@jwt_required()
def get_characters():
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
            "defense": char.defense,
            "is_active": user_id and char.id == current_app.get_current_user().active_character_id
        })
    
    return jsonify({"characters": character_list}), 200

@character_bp.route('/<int:character_id>/', methods=['GET'])
@jwt_required()
def get_character(character_id):
    user_id = get_jwt_identity()
    
    # Vérifier que le personnage appartient à l'utilisateur
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM characters 
        WHERE id = ? AND user_id = ?
    ''', (character_id, user_id))
    char_data = cursor.fetchone()
    
    if not char_data:
        cursor.close()
        conn.close()
        return jsonify({"error": "Personnage non trouvé ou non autorisé"}), 404
    
    character = Character(
        id=char_data['id'],
        name=char_data['name'],
        race=Race[char_data['race']],
        character_type=char_data['class'],
        health=char_data['health'],
        attack=char_data['attack'],
        defense=char_data['defense'],
        level=char_data['level']
    )
    
    # Récupérer les objets du personnage - à la fois de l'inventaire et des objets spéciaux
    # 1. Objets de l'inventaire régulier
    cursor.execute('''
        SELECT inventory.id, inventory.name, item_types.type_name as type, inventory.quantity 
        FROM inventory 
        JOIN item_types ON inventory.type_id = item_types.id
        WHERE inventory.character_id = ?
    ''', (character_id,))
    inventory_items = cursor.fetchall()
    
    # 2. Objets spéciaux du personnage
    cursor.execute('''
        SELECT id, name, type, effect 
        FROM character_items 
        WHERE character_id = ?
    ''', (character_id,))
    special_items = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    # Combiner les deux types d'objets
    item_list = []
    for item in inventory_items:
        item_list.append({
            "id": item['id'],
            "name": item['name'],
            "type": item['type'],
            "quantity": item['quantity'],
            "source": "inventory"
        })
    
    for item in special_items:
        item_list.append({
            "id": item['id'],
            "name": item['name'],
            "type": item['type'],
            "effect": item['effect'],
            "source": "character_items"
        })
    
    # Récupérer l'expérience de manière sécurisée
    try:
        experience = char_data['experience']
    except (KeyError, IndexError):
        experience = 0
    
    return jsonify({
        "character": {
            "id": character.id,
            "name": character.name,
            "race": character.race.value,
            "class": character.type,
            "level": character.level,
            "health": character.health,
            "attack": character.attack,
            "defense": character.defense,
            "experience": experience,  # Expérience sécurisée
            "is_active": user_id and character.id == current_app.get_current_user().active_character_id,
            "items": item_list
        }
    }), 200

@character_bp.route('/', methods=['POST'])
@jwt_required()
def create_character():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Aucune donnée fournie"}), 400
    
    name = data.get('name')
    race = data.get('race')
    character_class = data.get('class')
    
    if not name or not race or not character_class:
        return jsonify({"error": "Tous les champs sont obligatoires"}), 400
    
    try:
        race_enum = Race[race.upper()]
    except KeyError:
        return jsonify({"error": "Race invalide"}), 400
    
    # Créer l'instance temporaire du personnage (sans ID)
    if character_class == 'warrior':
        character = Warrior(name=name, race=race_enum)
    elif character_class == 'mage':
        character = Mage(name=name, race=race_enum)
    else:
        return jsonify({"error": "Classe invalide"}), 400
    
    # Sauvegarder dans la base de données
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO characters (name, race, class, health, attack, defense, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (character.name, character.race.name, character.type,
          character.health, character.attack, character.defense,
          user_id))
    
    character_id = cursor.lastrowid
    # Mettre à jour l'ID du personnage
    character.id = character_id
    
    # Mettre à jour l'active_character_id de l'utilisateur
    cursor.execute('''
        UPDATE user 
        SET active_character_id = ? 
        WHERE user_id = ?
    ''', (character_id, user_id))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({
        "message": "Personnage créé avec succès",
        "character": {
            "id": character.id,
            "name": character.name,
            "race": character.race.value,
            "class": character.type,
            "health": character.health,
            "attack": character.attack,
            "defense": character.defense,
            "level": character.level
        }
    }), 201

@character_bp.route('/<int:character_id>/select/', methods=['POST'])
@jwt_required()
def select_character(character_id):
    user_id = get_jwt_identity()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Vérifier que le personnage appartient bien à l'utilisateur
    cursor.execute('''
        SELECT * FROM characters 
        WHERE id = ? AND user_id = ?
    ''', (character_id, user_id))
    
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({"error": "Personnage non trouvé ou non autorisé"}), 404
    
    cursor.execute('''
        UPDATE user 
        SET active_character_id = ? 
        WHERE user_id = ?
    ''', (character_id, user_id))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    return jsonify({"message": "Personnage sélectionné avec succès"}), 200