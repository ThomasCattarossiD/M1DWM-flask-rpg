from flask import Blueprint, flash, redirect, render_template, request, url_for, jsonify, current_app, make_response
from flask_login import current_user, login_required
from flask_cors import cross_origin

from init_db import get_db_connection
import sqlite3

inventory_bp = Blueprint('inventory', __name__)

@inventory_bp.route('/', methods=['GET', 'OPTIONS'])
@cross_origin()
@login_required
def view_inventory():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
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
    
    sort_by = request.args.get('sort_by', 'name')
    order = request.args.get('order', 'asc')
    
    # Valider les paramètres de tri
    valid_columns = {'name', 'type_id', 'quantity'}
    valid_order = {'asc', 'desc'}
    
    if sort_by not in valid_columns:
        sort_by = 'name'
    if order not in valid_order:
        order = 'asc'
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Récupérer les informations du personnage actif
    cursor.execute('SELECT name FROM characters WHERE id = ?', (current_user.active_character_id,))
    character = cursor.fetchone()
    
    if not character:
        cursor.close()
        conn.close()
        
        if is_json:
            return jsonify({
                "success": False,
                "message": "Personnage non trouvé"
            }), 404
        
        flash('Personnage non trouvé.', 'error')
        return redirect(url_for('game.character_list'))
    
    query = f'''
        SELECT inventory.id AS item_id, 
               inventory.name AS item_name, 
               inventory.quantity AS item_quantity,
               inventory.description AS item_description, 
               item_types.id AS type_id,
               item_types.type_name AS item_type
        FROM inventory 
        JOIN item_types ON inventory.type_id = item_types.id 
        WHERE inventory.character_id = ?
        ORDER BY {sort_by} {order}
    '''
    
    cursor.execute(query, (current_user.active_character_id,))
    items = cursor.fetchall()
    
    # Récupérer les types d'objets pour le formulaire d'ajout
    cursor.execute('SELECT * FROM item_types')
    item_types = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    # Formater les données
    items_data = []
    for item in items:
        items_data.append({
            'id': item['item_id'],
            'name': item['item_name'],
            'type': item['item_type'],
            'type_id': item['type_id'],
            'quantity': item['item_quantity'],
            'description': item['item_description'] or '',
            'can_be_consumed': item['item_type'] in ['potion', 'plante']
        })
    
    if is_json:
        return jsonify({
            "success": True,
            "character_name": character['name'],
            "items": items_data,
            "item_types": [{'id': t['id'], 'name': t['type_name']} for t in item_types]
        }), 200
    
    return render_template('inventory/inventory.html', 
                         items=items_data, 
                         character_name=character['name'], 
                         sort_by=sort_by, 
                         order=order,
                         item_types=item_types)

@inventory_bp.route('/add', methods=['POST', 'OPTIONS'])
@cross_origin()
@login_required
def add_item():
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
    
    try:
        # Récupérer les données
        if is_json:
            data = request.get_json()
            name = data.get('name')
            type_id = int(data.get('type_id'))
            quantity = int(data.get('quantity', 1))
            description = data.get('description', '')
        else:
            name = request.form['name']
            type_id = int(request.form['type_id'])
            quantity = int(request.form.get('quantity', 1))
            description = request.form.get('description', '')
        
        # Validation
        if not name or not type_id or quantity < 1:
            if is_json:
                return jsonify({
                    "success": False,
                    "message": "Paramètres invalides"
                }), 400
            
            flash('Tous les champs sont obligatoires et la quantité doit être positive !', 'danger')
            return redirect(url_for('inventory.view_inventory'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Vérifier que le type d'objet existe
        cursor.execute('SELECT * FROM item_types WHERE id = ?', (type_id,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            
            if is_json:
                return jsonify({
                    "success": False,
                    "message": "Type d'objet invalide"
                }), 400
            
            flash('Type d\'objet invalide !', 'danger')
            return redirect(url_for('inventory.view_inventory'))
        
        # Vérifier si l'objet existe déjà dans l'inventaire
        cursor.execute('''
            SELECT * FROM inventory 
            WHERE character_id = ? AND name = ? AND type_id = ?
        ''', (current_user.active_character_id, name, type_id))
        
        existing_item = cursor.fetchone()
        
        if existing_item:
            # Mettre à jour la quantité
            new_quantity = existing_item['quantity'] + quantity
            cursor.execute('''
                UPDATE inventory 
                SET quantity = ? 
                WHERE id = ?
            ''', (new_quantity, existing_item['id']))
            item_id = existing_item['id']
            message = f'Quantité mise à jour pour {name}'
        else:
            # Insérer nouvel objet
            cursor.execute('''
                INSERT INTO inventory (character_id, name, type_id, quantity, description) 
                VALUES (?, ?, ?, ?, ?)
            ''', (current_user.active_character_id, name, type_id, quantity, description))
            item_id = cursor.lastrowid
            message = f'Objet {name} ajouté avec succès'
        
        # Mettre à jour les statistiques
        cursor.execute('''
            UPDATE player_stats 
            SET items_collected = items_collected + ? 
            WHERE character_id = ?
        ''', (quantity, current_user.active_character_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        if is_json:
            return jsonify({
                "success": True,
                "message": message,
                "item_id": item_id
            }), 200
        
        flash(message, 'success')
        return redirect(url_for('inventory.view_inventory'))
        
    except Exception as e:
        current_app.logger.error(f"Error adding item: {str(e)}")
        
        if is_json:
            return jsonify({
                "success": False,
                "message": f"Erreur: {str(e)}"
            }), 500
        
        flash(f'Erreur: {str(e)}', 'danger')
        return redirect(url_for('inventory.view_inventory'))

@inventory_bp.route('/edit/<int:item_id>', methods=['GET', 'POST', 'OPTIONS'])
@cross_origin()
@login_required
def edit_item(item_id):
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response, 200
    
    is_json = request.is_json or request.headers.get('Accept') == 'application/json'
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Vérifier que l'objet appartient au personnage actif de l'utilisateur
    cursor.execute('''
        SELECT inventory.*, item_types.type_name 
        FROM inventory 
        JOIN item_types ON inventory.type_id = item_types.id 
        WHERE inventory.id = ? AND inventory.character_id = ?
    ''', (item_id, current_user.active_character_id))
    
    item = cursor.fetchone()
    
    if not item:
        cursor.close()
        conn.close()
        
        if is_json:
            return jsonify({
                "success": False,
                "message": "Objet non trouvé ou accès non autorisé"
            }), 404
        
        flash('Objet non trouvé ou accès non autorisé.', 'danger')
        return redirect(url_for('inventory.view_inventory'))
    
    if request.method == 'POST':
        try:
            # Récupérer les données
            if is_json:
                data = request.get_json()
                name = data.get('name')
                type_id = int(data.get('type_id'))
                quantity = int(data.get('quantity', 1))
                description = data.get('description', '')
            else:
                name = request.form['name']
                type_id = int(request.form['type_id'])
                quantity = int(request.form.get('quantity', 1))
                description = request.form.get('description', '')
            
            # Validation
            if not name or not type_id or quantity < 1:
                if is_json:
                    return jsonify({
                        "success": False,
                        "message": "Paramètres invalides"
                    }), 400
                
                flash('Tous les champs sont obligatoires et la quantité doit être positive !', 'danger')
                return redirect(url_for('inventory.edit_item', item_id=item_id))
            
            # Vérifier que le type d'objet existe
            cursor.execute('SELECT * FROM item_types WHERE id = ?', (type_id,))
            if not cursor.fetchone():
                cursor.close()
                conn.close()
                
                if is_json:
                    return jsonify({
                        "success": False,
                        "message": "Type d'objet invalide"
                    }), 400
                
                flash('Type d\'objet invalide !', 'danger')
                return redirect(url_for('inventory.edit_item', item_id=item_id))
            
            # Mettre à jour l'objet
            cursor.execute('''
                UPDATE inventory 
                SET name = ?, type_id = ?, quantity = ?, description = ?
                WHERE id = ? AND character_id = ?
            ''', (name, type_id, quantity, description, item_id, current_user.active_character_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            if is_json:
                return jsonify({
                    "success": True,
                    "message": "Objet modifié avec succès"
                }), 200
            
            flash('Objet modifié avec succès !', 'success')
            return redirect(url_for('inventory.view_inventory'))
            
        except Exception as e:
            current_app.logger.error(f"Error editing item: {str(e)}")
            
            if is_json:
                return jsonify({
                    "success": False,
                    "message": f"Erreur: {str(e)}"
                }), 500
            
            flash(f'Erreur: {str(e)}', 'danger')
            return redirect(url_for('inventory.edit_item', item_id=item_id))
    
    # Pour GET, récupérer les types d'objets pour le formulaire
    cursor.execute('SELECT * FROM item_types')
    item_types = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    if is_json:
        return jsonify({
            "success": True,
            "item": {
                "id": item['id'],
                "name": item['name'],
                "type_id": item['type_id'],
                "type_name": item['type_name'],
                "quantity": item['quantity'],
                "description": item['description'] or ""
            },
            "item_types": [{'id': t['id'], 'name': t['type_name']} for t in item_types]
        }), 200
    
    return render_template('inventory/edit_item.html', 
                           action='Modifier', 
                           item=item, 
                           item_types=item_types)

@inventory_bp.route('/delete/<int:item_id>', methods=['POST', 'OPTIONS'])
@cross_origin()
@login_required
def delete_item(item_id):
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200
    
    is_json = request.is_json or request.headers.get('Accept') == 'application/json'
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Vérifier que l'objet appartient au personnage actif de l'utilisateur
        cursor.execute('''
            SELECT * FROM inventory 
            WHERE id = ? AND character_id = ?
        ''', (item_id, current_user.active_character_id))
        
        item = cursor.fetchone()
        
        if not item:
            cursor.close()
            conn.close()
            
            if is_json:
                return jsonify({
                    "success": False,
                    "message": "Objet non trouvé ou accès non autorisé"
                }), 404
            
            flash('Objet non trouvé ou accès non autorisé.', 'danger')
            return redirect(url_for('inventory.view_inventory'))
        
        # Supprimer l'objet
        cursor.execute('DELETE FROM inventory WHERE id = ?', (item_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        if is_json:
            return jsonify({
                "success": True,
                "message": "Objet supprimé avec succès"
            }), 200
        
        flash('Objet supprimé avec succès !', 'success')
        return redirect(url_for('inventory.view_inventory'))
    
    except Exception as e:
        current_app.logger.error(f"Error deleting item: {str(e)}")
        
        if is_json:
            return jsonify({
                "success": False,
                "message": f"Erreur: {str(e)}"
            }), 500
        
        flash(f'Erreur: {str(e)}', 'danger')
        return redirect(url_for('inventory.view_inventory'))

@inventory_bp.route('/consume/<int:item_id>', methods=['POST', 'OPTIONS'])
@cross_origin()
@login_required
def consume_item(item_id):
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
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
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Vérifier que l'objet appartient au personnage actif
        cursor.execute('''
            SELECT inventory.*, item_types.type_name 
            FROM inventory 
            JOIN item_types ON inventory.type_id = item_types.id 
            WHERE inventory.id = ? AND inventory.character_id = ?
        ''', (item_id, current_user.active_character_id))
        
        item = cursor.fetchone()
        
        if not item:
            cursor.close()
            conn.close()
            
            if is_json:
                return jsonify({
                    "success": False,
                    "message": "Objet non trouvé"
                }), 404
            
            flash('Objet non trouvé.', 'error')
            return redirect(url_for('inventory.view_inventory'))
        
        if item['type_name'] not in ['potion', 'plante']:
            cursor.close()
            conn.close()
            
            if is_json:
                return jsonify({
                    "success": False,
                    "message": "Cet objet ne peut pas être consommé"
                }), 400
            
            flash('Cet objet ne peut pas être consommé.', 'warning')
            return redirect(url_for('inventory.view_inventory'))
        
        # Appliquer les effets de l'objet sur le personnage
        effect_message = ""
        
        if item['type_name'] == 'potion':
            # Augmenter les points de vie du personnage
            cursor.execute('''
                UPDATE characters 
                SET health = MIN(health + 20, 100) 
                WHERE id = ?
            ''', (current_user.active_character_id,))
            effect_message = "Vous avez récupéré 20 points de vie!"
        elif item['type_name'] == 'plante':
            # Augmenter temporairement l'attaque
            cursor.execute('''
                UPDATE characters 
                SET attack = attack + 5 
                WHERE id = ?
            ''', (current_user.active_character_id,))
            effect_message = "Votre attaque a augmenté de 5 points!"
        
        # Réduire la quantité de l'objet
        if item['quantity'] > 1:
            cursor.execute('''
                UPDATE inventory 
                SET quantity = quantity - 1 
                WHERE id = ?
            ''', (item_id,))
            remaining = item['quantity'] - 1
        else:
            cursor.execute('DELETE FROM inventory WHERE id = ?', (item_id,))
            remaining = 0
        
        conn.commit()
        cursor.close()
        conn.close()
        
        if is_json:
            return jsonify({
                "success": True,
                "message": effect_message,
                "item_id": item_id,
                "remaining": remaining
            }), 200
        
        flash(f'Objet consommé! {effect_message}', 'success')
        return redirect(url_for('inventory.view_inventory'))
    
    except Exception as e:
        current_app.logger.error(f"Error consuming item: {str(e)}")
        
        if is_json:
            return jsonify({
                "success": False,
                "message": f"Erreur: {str(e)}"
            }), 500
        
        flash(f'Erreur: {str(e)}', 'danger')
        return redirect(url_for('inventory.view_inventory'))

