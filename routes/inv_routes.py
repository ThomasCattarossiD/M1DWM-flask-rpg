from flask import Blueprint, request, jsonify, make_response
from flask_login import login_required, current_user
from flask_cors import cross_origin
import sqlite3

from init_db import get_db_connection

inv_bp = Blueprint('inv', __name__)

@inv_bp.route('/api/inventory', methods=['GET', 'OPTIONS'])
@cross_origin()
@login_required
def get_inventory():
    """Récupérer l'inventaire du personnage actif de l'utilisateur actuel"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response, 200
        
    try:
        # Vérifie si l'utilisateur a un personnage actif
        if not current_user.active_character_id:
            return jsonify({
                "success": False,
                "message": "Aucun personnage actif sélectionné"
            }), 400
            
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Récupération des objets de l'inventaire avec leurs types
        cursor.execute('''
            SELECT i.*, it.type_name 
            FROM inventory i
            JOIN item_types it ON i.type_id = it.id
            WHERE i.character_id = ?
            ORDER BY i.type_id, i.name
        ''', (current_user.active_character_id,))
        
        inventory_items = [dict(row) for row in cursor.fetchall()]
        
        # Récupération des objets équipés
        cursor.execute('''
            SELECT ei.inventory_id, ei.slot
            FROM equipped_items ei
            WHERE ei.character_id = ?
        ''', (current_user.active_character_id,))
        
        equipped_items = [dict(row) for row in cursor.fetchall()]
        equipped_ids = {item['inventory_id']: item['slot'] for item in equipped_items}
        
        # Ajout d'informations supplémentaires à chaque objet
        for item in inventory_items:
            item['is_equipped'] = item['id'] in equipped_ids
            item['equipped_slot'] = equipped_ids.get(item['id'], None)
            # Déterminer si l'objet est stackable basé sur son type
            item['is_stackable'] = item['type_id'] in [3, 4]  # Potions et Matériaux sont stackables
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "items": inventory_items
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Erreur lors de la récupération de l'inventaire: {str(e)}"
        }), 500

@inv_bp.route('/api/inventory', methods=['POST', 'OPTIONS'])
@cross_origin()
@login_required
def add_item():
    """Ajouter un nouvel objet à l'inventaire du personnage actif"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response, 200
        
    try:
        # Vérifie si l'utilisateur a un personnage actif
        if not current_user.active_character_id:
            return jsonify({
                "success": False,
                "message": "Aucun personnage actif sélectionné"
            }), 400
            
        data = request.get_json()
        name = data.get('name')
        type_id = data.get('type_id')
        quantity = data.get('quantity', 1)  # Valeur par défaut: 1
        description = data.get('description', '')  # Valeur par défaut: chaîne vide
        
        # Validation des données
        if not name or not type_id:
            return jsonify({
                "success": False,
                "message": "Nom et type de l'objet requis"
            }), 400
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Vérification du type d'objet
        cursor.execute('SELECT id FROM item_types WHERE id = ?', (type_id,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({
                "success": False,
                "message": "Type d'objet invalide"
            }), 400
            
        # Pour les objets stackables (Potions et Matériaux), on peut vérifier s'ils existent déjà
        # et augmenter leur quantité plutôt que de créer un nouvel enregistrement
        is_stackable = type_id in [3, 4]  # Potions et Matériaux
        
        if is_stackable:
            # Vérification si l'objet existe déjà
            cursor.execute('''
                SELECT id, quantity FROM inventory 
                WHERE character_id = ? AND name = ? AND type_id = ?
            ''', (current_user.active_character_id, name, type_id))
            
            existing_item = cursor.fetchone()
            
            if existing_item:
                # Mise à jour de la quantité
                new_quantity = existing_item[1] + quantity
                cursor.execute('''
                    UPDATE inventory SET quantity = ? WHERE id = ?
                ''', (new_quantity, existing_item[0]))
                conn.commit()
                
                # Récupération de l'objet mis à jour
                cursor.execute('''
                    SELECT i.*, it.type_name 
                    FROM inventory i
                    JOIN item_types it ON i.type_id = it.id
                    WHERE i.id = ?
                ''', (existing_item[0],))
                
                item = dict(cursor.fetchone())
                
                cursor.close()
                conn.close()
                
                return jsonify({
                    "success": True,
                    "message": "Quantité de l'objet mise à jour",
                    "item": item
                }), 200
        
        # Insertion d'un nouvel objet
        cursor.execute('''
            INSERT INTO inventory (character_id, name, type_id, quantity, description)
            VALUES (?, ?, ?, ?, ?)
        ''', (current_user.active_character_id, name, type_id, quantity, description))
        
        item_id = cursor.lastrowid
        conn.commit()
        
        # Récupération de l'objet inséré
        cursor.execute('''
            SELECT i.*, it.type_name 
            FROM inventory i
            JOIN item_types it ON i.type_id = it.id
            WHERE i.id = ?
        ''', (item_id,))
        
        new_item = dict(cursor.fetchone())
        new_item['is_equipped'] = False
        new_item['equipped_slot'] = None
        new_item['is_stackable'] = is_stackable
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Objet ajouté avec succès",
            "item": new_item
        }), 201
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Erreur lors de l'ajout de l'objet: {str(e)}"
        }), 500

@inv_bp.route('/api/inventory/<int:item_id>', methods=['PUT', 'OPTIONS'])
@cross_origin()
@login_required
def update_item(item_id):
    """Modifier un objet existant dans l'inventaire"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'PUT, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response, 200
        
    try:
        # Vérifie si l'utilisateur a un personnage actif
        if not current_user.active_character_id:
            return jsonify({
                "success": False,
                "message": "Aucun personnage actif sélectionné"
            }), 400
            
        data = request.get_json()
        name = data.get('name')
        type_id = data.get('type_id')
        quantity = data.get('quantity')
        description = data.get('description')
        
        # Au moins un champ doit être modifié
        if not any([name, type_id, quantity is not None, description]):
            return jsonify({
                "success": False,
                "message": "Aucune donnée fournie pour la mise à jour"
            }), 400
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Vérification que l'objet existe et appartient au personnage actif
        cursor.execute('''
            SELECT * FROM inventory 
            WHERE id = ? AND character_id = ?
        ''', (item_id, current_user.active_character_id))
        
        item = cursor.fetchone()
        if not item:
            cursor.close()
            conn.close()
            return jsonify({
                "success": False,
                "message": "Objet non trouvé ou non autorisé"
            }), 404
            
        # Construction de la requête de mise à jour
        update_fields = []
        update_values = []
        
        if name:
            update_fields.append("name = ?")
            update_values.append(name)
        
        if type_id:
            # Vérification du type d'objet
            cursor.execute('SELECT id FROM item_types WHERE id = ?', (type_id,))
            if not cursor.fetchone():
                cursor.close()
                conn.close()
                return jsonify({
                    "success": False,
                    "message": "Type d'objet invalide"
                }), 400
            
            update_fields.append("type_id = ?")
            update_values.append(type_id)
            
        if quantity is not None:
            if quantity < 1:
                cursor.close()
                conn.close()
                return jsonify({
                    "success": False,
                    "message": "La quantité doit être supérieure à 0"
                }), 400
                
            update_fields.append("quantity = ?")
            update_values.append(quantity)
            
        if description is not None:
            update_fields.append("description = ?")
            update_values.append(description)
            
        # Exécution de la mise à jour
        if update_fields:
            update_query = f"UPDATE inventory SET {', '.join(update_fields)} WHERE id = ?"
            update_values.append(item_id)
            
            cursor.execute(update_query, update_values)
            conn.commit()
            
        # Récupération de l'objet mis à jour
        cursor.execute('''
            SELECT i.*, it.type_name 
            FROM inventory i
            JOIN item_types it ON i.type_id = it.id
            WHERE i.id = ?
        ''', (item_id,))
        
        updated_item = dict(cursor.fetchone())
        
        # Vérification si l'objet est équipé
        cursor.execute('''
            SELECT slot FROM equipped_items 
            WHERE character_id = ? AND inventory_id = ?
        ''', (current_user.active_character_id, item_id))
        
        equipped = cursor.fetchone()
        updated_item['is_equipped'] = equipped is not None
        updated_item['equipped_slot'] = equipped[0] if equipped else None
        updated_item['is_stackable'] = updated_item['type_id'] in [3, 4]  # Potions et Matériaux
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Objet mis à jour avec succès",
            "item": updated_item
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Erreur lors de la mise à jour de l'objet: {str(e)}"
        }), 500

@inv_bp.route('/api/inventory/<int:item_id>', methods=['DELETE', 'OPTIONS'])
@cross_origin()
@login_required
def delete_item(item_id):
    """Supprimer un objet de l'inventaire"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'DELETE, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response, 200
        
    try:
        # Vérifie si l'utilisateur a un personnage actif
        if not current_user.active_character_id:
            return jsonify({
                "success": False,
                "message": "Aucun personnage actif sélectionné"
            }), 400
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Vérification que l'objet existe et appartient au personnage actif
        cursor.execute('''
            SELECT * FROM inventory 
            WHERE id = ? AND character_id = ?
        ''', (item_id, current_user.active_character_id))
        
        item = cursor.fetchone()
        if not item:
            cursor.close()
            conn.close()
            return jsonify({
                "success": False,
                "message": "Objet non trouvé ou non autorisé"
            }), 404
            
        # Vérification si l'objet est équipé, auquel cas on le déséquipe d'abord
        cursor.execute('''
            DELETE FROM equipped_items 
            WHERE character_id = ? AND inventory_id = ?
        ''', (current_user.active_character_id, item_id))
        
        # Suppression de l'objet
        cursor.execute('DELETE FROM inventory WHERE id = ?', (item_id,))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Objet supprimé avec succès"
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Erreur lors de la suppression de l'objet: {str(e)}"
        }), 500

@inv_bp.route('/api/inventory/<int:item_id>/use', methods=['POST', 'OPTIONS'])
@cross_origin()
@login_required
def use_item(item_id):
    """Utiliser un objet (consommer une potion ou équiper une arme/armure)"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response, 200
        
    try:
        # Vérifie si l'utilisateur a un personnage actif
        if not current_user.active_character_id:
            return jsonify({
                "success": False,
                "message": "Aucun personnage actif sélectionné"
            }), 400
            
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Récupération de l'objet avec son type
        cursor.execute('''
            SELECT i.*, it.type_name 
            FROM inventory i
            JOIN item_types it ON i.type_id = it.id
            WHERE i.id = ? AND i.character_id = ?
        ''', (item_id, current_user.active_character_id))
        
        item = cursor.fetchone()
        
        if not item:
            cursor.close()
            conn.close()
            return jsonify({
                "success": False,
                "message": "Objet non trouvé ou non autorisé"
            }), 404
            
        item = dict(item)
        
        # Logique différente selon le type d'objet
        if item['type_id'] == 3:  # Potion
            # Vérification que la quantité est suffisante
            if item['quantity'] < 1:
                cursor.close()
                conn.close()
                return jsonify({
                    "success": False,
                    "message": "Quantité insuffisante"
                }), 400
                
            # Effet de la potion (exemple: +20 points de vie)
            # Simulation d'un effet simple basé sur le nom
            effect_message = "Aucun effet"
            
            if "health" in item['name'].lower() or "vie" in item['name'].lower():
                # Potion de vie: augmentation des points de vie
                cursor.execute('''
                    UPDATE characters 
                    SET health = MIN(health + 20, 100) 
                    WHERE id = ?
                ''', (current_user.active_character_id,))
                effect_message = "Vous avez récupéré 20 points de vie"
            
            elif "strength" in item['name'].lower() or "force" in item['name'].lower():
                # Potion de force: augmentation temporaire de l'attaque
                cursor.execute('''
                    UPDATE characters 
                    SET attack = attack + 5 
                    WHERE id = ?
                ''', (current_user.active_character_id,))
                effect_message = "Votre attaque a augmenté de 5 points"
                
            elif "defense" in item['name'].lower():
                # Potion de défense: augmentation temporaire de la défense
                cursor.execute('''
                    UPDATE characters 
                    SET defense = defense + 5 
                    WHERE id = ?
                ''', (current_user.active_character_id,))
                effect_message = "Votre défense a augmenté de 5 points"
            
            # Décrémenter la quantité
            new_quantity = item['quantity'] - 1
            if new_quantity > 0:
                cursor.execute('''
                    UPDATE inventory SET quantity = ? WHERE id = ?
                ''', (new_quantity, item_id))
            else:
                # Supprimer l'objet si sa quantité tombe à 0
                cursor.execute('DELETE FROM inventory WHERE id = ?', (item_id,))
                
            conn.commit()
            cursor.close()
            conn.close()
            
            return jsonify({
                "success": True,
                "message": "Potion consommée",
                "effect": effect_message
            }), 200
            
        elif item['type_id'] == 1 or item['type_id'] == 2:  # Arme ou Armure
            # Déterminer le slot d'équipement
            slot = 'weapon' if item['type_id'] == 1 else 'armor'
            
            # Vérifier si un objet est déjà équipé dans ce slot
            cursor.execute('''
                SELECT inventory_id FROM equipped_items 
                WHERE character_id = ? AND slot = ?
            ''', (current_user.active_character_id, slot))
            
            currently_equipped = cursor.fetchone()
            
            if currently_equipped:
                # Déséquiper l'objet actuel
                cursor.execute('''
                    DELETE FROM equipped_items 
                    WHERE character_id = ? AND slot = ?
                ''', (current_user.active_character_id, slot))
            
            # Équiper le nouvel objet
            cursor.execute('''
                INSERT INTO equipped_items (character_id, inventory_id, slot)
                VALUES (?, ?, ?)
            ''', (current_user.active_character_id, item_id, slot))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return jsonify({
                "success": True,
                "message": f"{item['name']} équipé(e) avec succès",
                "effect": f"Vous avez équipé {item['name']} comme {slot}"
            }), 200
            
        else:  # Matériau ou autre type
            cursor.close()
            conn.close()
            return jsonify({
                "success": False,
                "message": "Ce type d'objet ne peut pas être utilisé directement"
            }), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Erreur lors de l'utilisation de l'objet: {str(e)}"
        }), 500

@inv_bp.route('/api/items', methods=['GET', 'OPTIONS'])
@cross_origin()
@login_required
def get_item_types():
    """Récupérer tous les types d'objets disponibles"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response, 200
        
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM item_types ORDER BY id')
        item_types = [dict(row) for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "item_types": item_types
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Erreur lors de la récupération des types d'objets: {str(e)}"
        }), 500
