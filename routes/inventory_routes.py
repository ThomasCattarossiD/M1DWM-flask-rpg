from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from init_db import get_db_connection
from models.game import Character, Item

inventory_bp = Blueprint('inventory', __name__)

@inventory_bp.route('/', methods=['GET'])
@jwt_required()
def get_inventory():
    user = current_app.get_current_user()
    
    if not user or not user.active_character_id:
        return jsonify({"error": "Aucun personnage actif sélectionné"}), 400
    
    # Options de tri
    sort_by = request.args.get('sort_by', 'item_name')
    order = request.args.get('order', 'asc')
    
    valid_columns = {'item_name', 'item_type', 'item_quantity'}
    valid_order = {'asc', 'desc'}
    if sort_by not in valid_columns:
        sort_by = 'item_name'
    if order not in valid_order:
        order = 'asc'
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Récupérer le nom du personnage actif
    cursor.execute('SELECT name FROM characters WHERE id = ?', (user.active_character_id,))
    character = cursor.fetchone()
    
    # Récupérer l'inventaire normal du personnage
    query = f'''
        SELECT inventory.id AS item_id, inventory.name AS item_name, 
               item_types.type_name AS item_type, inventory.quantity AS item_quantity 
        FROM inventory 
        JOIN item_types ON inventory.type_id = item_types.id 
        WHERE inventory.character_id = ?
        ORDER BY {sort_by} {order}
    '''
    cursor.execute(query, (user.active_character_id,))
    regular_items = cursor.fetchall()
    
    # Récupérer les objets spéciaux du personnage (équipements, récompenses de quête, etc.)
    cursor.execute('''
        SELECT id, name, type, effect FROM character_items
        WHERE character_id = ?
    ''', (user.active_character_id,))
    special_items = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    # Construire la liste d'objets complète
    item_list = []
    
    # Ajouter les objets réguliers
    for item in regular_items:
        item_list.append({
            "id": item['item_id'],
            "name": item['item_name'],
            "type": item['item_type'],
            "quantity": item['item_quantity'],
            "source": "inventory",
            "consumable": item['item_type'] in ['potion', 'plante']
        })
    
    # Ajouter les objets spéciaux
    for item in special_items:
        item_list.append({
            "id": item['id'],
            "name": item['name'],
            "type": item['type'],
            "effect": item['effect'],
            "source": "character_items",
            "consumable": item['type'] in ['healing', 'potion', 'plante']
        })
    
    # Calculer des statistiques sur l'inventaire
    stats = {
        "total_items": len(item_list),
        "consumables": sum(1 for item in item_list if item.get('consumable', False)),
        "weapons": sum(1 for item in item_list if item.get('type') in ['weapon', 'arme']),
        "armor": sum(1 for item in item_list if item.get('type') in ['armor', 'armure'])
    }
    
    return jsonify({
        "character_name": character['name'] if character else "Personnage",
        "items": item_list,
        "stats": stats
    }), 200

@inventory_bp.route('/', methods=['POST'])
@jwt_required()
def add_item():
    user = current_app.get_current_user()
    
    if not user or not user.active_character_id:
        return jsonify({"error": "Aucun personnage actif sélectionné"}), 400
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "Aucune donnée fournie"}), 400
    
    name = data.get('name')
    type_id = data.get('type_id')
    quantity = data.get('quantity', 1)
    
    if not name or not type_id:
        return jsonify({"error": "Nom et type de l'objet requis"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Vérifier que le type d'item existe
    cursor.execute('SELECT * FROM item_types WHERE id = ?', (type_id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({"error": "Type d'objet invalide"}), 400
    
    # Vérifier si l'objet existe déjà dans l'inventaire
    cursor.execute('''
        SELECT * FROM inventory 
        WHERE character_id = ? AND name = ? AND type_id = ?
    ''', (user.active_character_id, name, type_id))
    
    existing_item = cursor.fetchone()
    
    if existing_item:
        # Mettre à jour la quantité de l'objet existant
        new_quantity = existing_item['quantity'] + quantity
        cursor.execute('''
            UPDATE inventory 
            SET quantity = ? 
            WHERE id = ?
        ''', (new_quantity, existing_item['id']))
        item_id = existing_item['id']
    else:
        # Créer un nouvel objet
        cursor.execute('''
            INSERT INTO inventory (character_id, name, type_id, quantity) 
            VALUES (?, ?, ?, ?)''',
            (user.active_character_id, name, type_id, quantity))
        item_id = cursor.lastrowid
    
    # Récupérer le nom du type d'objet
    cursor.execute('SELECT type_name FROM item_types WHERE id = ?', (type_id,))
    type_name = cursor.fetchone()['type_name']
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({
        "message": "Objet ajouté avec succès",
        "item": {
            "id": item_id,
            "name": name,
            "type": type_name,
            "quantity": quantity if not existing_item else new_quantity,
            "consumable": type_name in ['potion', 'plante']
        }
    }), 201

@inventory_bp.route('/<int:item_id>/', methods=['GET'])
@jwt_required()
def get_item(item_id):
    user = current_app.get_current_user()
    
    if not user or not user.active_character_id:
        return jsonify({"error": "Aucun personnage actif sélectionné"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Essayer de récupérer depuis l'inventaire régulier
    cursor.execute('''
        SELECT inventory.*, item_types.type_name 
        FROM inventory 
        JOIN item_types ON inventory.type_id = item_types.id 
        WHERE inventory.id = ? AND inventory.character_id = ?
    ''', (item_id, user.active_character_id))
    
    item = cursor.fetchone()
    
    if item:
        cursor.close()
        conn.close()
        return jsonify({
            "id": item['id'],
            "name": item['name'],
            "type": item['type_name'],
            "type_id": item['type_id'],
            "quantity": item['quantity'],
            "source": "inventory",
            "consumable": item['type_name'] in ['potion', 'plante']
        }), 200
    
    # Si pas trouvé, essayer dans les objets spéciaux
    cursor.execute('''
        SELECT * FROM character_items
        WHERE id = ? AND character_id = ?
    ''', (item_id, user.active_character_id))
    
    special_item = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if special_item:
        return jsonify({
            "id": special_item['id'],
            "name": special_item['name'],
            "type": special_item['type'],
            "effect": special_item['effect'],
            "source": "character_items",
            "consumable": special_item['type'] in ['healing', 'potion', 'plante']
        }), 200
    
    return jsonify({"error": "Objet non trouvé ou non autorisé"}), 404

@inventory_bp.route('/<int:item_id>/', methods=['PUT'])
@jwt_required()
def update_item(item_id):
    user = current_app.get_current_user()
    
    if not user or not user.active_character_id:
        return jsonify({"error": "Aucun personnage actif sélectionné"}), 400
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "Aucune donnée fournie"}), 400
    
    source = data.get('source', 'inventory')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if source == 'inventory':
        name = data.get('name')
        type_id = data.get('type_id')
        quantity = data.get('quantity')
        
        if not name or not type_id or not quantity:
            cursor.close()
            conn.close()
            return jsonify({"error": "Tous les champs sont obligatoires"}), 400
        
        # Vérifier que l'objet appartient au personnage actif
        cursor.execute('''
            SELECT * FROM inventory 
            WHERE id = ? AND character_id = ?
        ''', (item_id, user.active_character_id))
        
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Objet non trouvé ou non autorisé"}), 404
        
        # Mettre à jour l'objet
        cursor.execute('''
            UPDATE inventory 
            SET name = ?, type_id = ?, quantity = ? 
            WHERE id = ?
        ''', (name, type_id, quantity, item_id))
        
        # Récupérer le nom du type d'objet
        cursor.execute('SELECT type_name FROM item_types WHERE id = ?', (type_id,))
        type_name = cursor.fetchone()['type_name']
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "message": "Objet mis à jour avec succès",
            "item": {
                "id": item_id,
                "name": name,
                "type": type_name,
                "quantity": quantity,
                "source": "inventory",
                "consumable": type_name in ['potion', 'plante']
            }
        }), 200
    
    elif source == 'character_items':
        name = data.get('name')
        item_type = data.get('type')
        effect = data.get('effect')
        
        if not name or not item_type:
            cursor.close()
            conn.close()
            return jsonify({"error": "Nom et type sont obligatoires"}), 400
        
        # Vérifier que l'objet appartient au personnage actif
        cursor.execute('''
            SELECT * FROM character_items 
            WHERE id = ? AND character_id = ?
        ''', (item_id, user.active_character_id))
        
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Objet non trouvé ou non autorisé"}), 404
        
        # Mettre à jour l'objet spécial
        cursor.execute('''
            UPDATE character_items 
            SET name = ?, type = ?, effect = ? 
            WHERE id = ?
        ''', (name, item_type, effect, item_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "message": "Objet mis à jour avec succès",
            "item": {
                "id": item_id,
                "name": name,
                "type": item_type,
                "effect": effect,
                "source": "character_items",
                "consumable": item_type in ['healing', 'potion', 'plante']
            }
        }), 200
    
    cursor.close()
    conn.close()
    return jsonify({"error": "Source d'objet invalide"}), 400

@inventory_bp.route('/<int:item_id>/', methods=['DELETE'])
@jwt_required()
def delete_item(item_id):
    user = current_app.get_current_user()
    
    if not user or not user.active_character_id:
        return jsonify({"error": "Aucun personnage actif sélectionné"}), 400
    
    source = request.args.get('source', 'inventory')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if source == 'inventory':
        # Vérifier que l'objet appartient au personnage actif
        cursor.execute('''
            SELECT * FROM inventory 
            WHERE id = ? AND character_id = ?
        ''', (item_id, user.active_character_id))
        
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Objet non trouvé ou non autorisé"}), 404
        
        cursor.execute('DELETE FROM inventory WHERE id = ?', (item_id,))
    
    elif source == 'character_items':
        # Vérifier que l'objet appartient au personnage actif
        cursor.execute('''
            SELECT * FROM character_items 
            WHERE id = ? AND character_id = ?
        ''', (item_id, user.active_character_id))
        
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Objet non trouvé ou non autorisé"}), 404
        
        cursor.execute('DELETE FROM character_items WHERE id = ?', (item_id,))
    
    else:
        cursor.close()
        conn.close()
        return jsonify({"error": "Source d'objet invalide"}), 400
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({"message": "Objet supprimé avec succès"}), 200

@inventory_bp.route('/<int:item_id>/consume/', methods=['POST'])
@jwt_required()
def consume_item(item_id):
    user = current_app.get_current_user()
    
    if not user or not user.active_character_id:
        return jsonify({"error": "Aucun personnage actif sélectionné"}), 400
    
    source = request.json.get('source', 'inventory') if request.json else 'inventory'
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if source == 'inventory':
        # Récupérer l'objet et vérifier qu'il appartient au personnage actif
        cursor.execute('''
            SELECT inventory.*, item_types.type_name 
            FROM inventory 
            JOIN item_types ON inventory.type_id = item_types.id 
            WHERE inventory.id = ? AND inventory.character_id = ?
        ''', (item_id, user.active_character_id))
        
        item = cursor.fetchone()
        
        if not item:
            cursor.close()
            conn.close()
            return jsonify({"error": "Objet non trouvé ou non autorisé"}), 404
        
        if item['type_name'] not in ['potion', 'plante']:
            cursor.close()
            conn.close()
            return jsonify({"error": "Cet objet ne peut pas être consommé"}), 400
        
        # Appliquer les effets de l'objet
        effect_message = ""
        if item['type_name'] == 'potion':
            # Augmenter les points de vie du personnage
            cursor.execute('''
                UPDATE characters 
                SET health = MIN(health + 20, 100) 
                WHERE id = ?
            ''', (user.active_character_id,))
            effect_message = "Vous avez récupéré 20 points de vie !"
        elif item['type_name'] == 'plante':
            # Augmenter temporairement l'attaque
            cursor.execute('''
                UPDATE characters 
                SET attack = attack + 5 
                WHERE id = ?
            ''', (user.active_character_id,))
            effect_message = "Votre attaque a augmenté de 5 points !"
        
        # Réduire la quantité de l'objet
        if item['quantity'] > 1:
            cursor.execute('''
                UPDATE inventory 
                SET quantity = quantity - 1 
                WHERE id = ?
            ''', (item_id,))
            new_quantity = item['quantity'] - 1
            item_consumed = False
        else:
            cursor.execute('DELETE FROM inventory WHERE id = ?', (item_id,))
            new_quantity = 0
            item_consumed = True
        
    elif source == 'character_items':
        # Récupérer l'objet spécial
        cursor.execute('''
            SELECT * FROM character_items
            WHERE id = ? AND character_id = ?
        ''', (item_id, user.active_character_id))
        
        item = cursor.fetchone()
        
        if not item:
            cursor.close()
            conn.close()
            return jsonify({"error": "Objet non trouvé ou non autorisé"}), 404
        
        if item['type'] not in ['healing', 'potion', 'plante']:
            cursor.close()
            conn.close()
            return jsonify({"error": "Cet objet ne peut pas être consommé"}), 400
        
        # Appliquer les effets de l'objet
        effect_message = "Objet utilisé !"
        if item['type'] == 'healing' or item['type'] == 'potion':
            # Récupérer l'effet de l'objet (format "+X hp")
            effect = item['effect']
            heal_amount = 20  # Valeur par défaut
            
            if effect and '+' in effect and 'hp' in effect:
                try:
                    heal_amount = int(effect.split('+')[1].split('hp')[0].strip())
                except (ValueError, IndexError):
                    pass
            
            # Augmenter les points de vie du personnage
            cursor.execute('''
                UPDATE characters 
                SET health = MIN(health + ?, 100) 
                WHERE id = ?
            ''', (heal_amount, user.active_character_id,))
            effect_message = f"Vous avez récupéré {heal_amount} points de vie !"
        
        # Supprimer l'objet après utilisation
        cursor.execute('DELETE FROM character_items WHERE id = ?', (item_id,))
        new_quantity = 0
        item_consumed = True
    
    else:
        cursor.close()
        conn.close()
        return jsonify({"error": "Source d'objet invalide"}), 400
    
    conn.commit()
    
    # Récupérer les nouvelles stats du personnage
    cursor.execute('SELECT * FROM characters WHERE id = ?', (user.active_character_id,))
    character = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return jsonify({
        "message": f"Objet consommé ! {effect_message}",
        "item_consumed": item_consumed,
        "remaining_quantity": new_quantity if 'new_quantity' in locals() else 0,
        "character": {
            "id": character['id'],
            "name": character['name'],
            "health": character['health'],
            "attack": character['attack'],
            "defense": character['defense'],
            "level": character['level'],
            "experience": character['experience']
        }
    }), 200

@inventory_bp.route('/types/', methods=['GET'])
@jwt_required()
def get_item_types():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM item_types')
    types = cursor.fetchall()
    cursor.close()
    conn.close()
    
    types_list = []
    for type_info in types:
        types_list.append({
            "id": type_info['id'],
            "name": type_info['type_name']
        })
    
    return jsonify({"item_types": types_list}), 200