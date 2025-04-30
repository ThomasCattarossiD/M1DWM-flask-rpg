from flask import Blueprint, flash, redirect, render_template, request, url_for, jsonify, current_app
from flask_login import current_user, login_required
from flask_cors import cross_origin

from init_db import get_db_connection

inventory_bp = Blueprint('inventory', __name__)

@inventory_bp.route('/', methods=['GET', 'OPTIONS'])
@cross_origin()
@login_required
def view():
    if request.method == 'OPTIONS':
        return '', 200
    
    if not current_user.active_character_id:
        if request.is_json:
            return jsonify({
                "success": False,
                "message": "Veuillez d'abord sélectionner un personnage"
            }), 400
        
        flash('Veuillez d\'abord sélectionner un personnage.', 'warning')
        return redirect(url_for('game.character_list'))
    
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
    
    try:
        # Récupérer les informations du personnage actif
        cursor.execute('SELECT name FROM characters WHERE id = ?', (current_user.active_character_id,))
        character = cursor.fetchone()
        
        if not character:
            cursor.close()
            conn.close()
            
            if request.is_json:
                return jsonify({
                    "success": False,
                    "message": "Personnage actif non trouvé"
                }), 404
            
            flash('Personnage actif non trouvé.', 'error')
            return redirect(url_for('game.character_list'))
        
        query = f'''
            SELECT inventory.id AS item_id, inventory.name AS item_name, 
                   item_types.type_name AS item_type, inventory.quantity AS item_quantity 
            FROM inventory 
            JOIN item_types ON inventory.type_id = item_types.id 
            WHERE inventory.character_id = ?
            ORDER BY {sort_by} {order}
        '''
        
        cursor.execute(query, (current_user.active_character_id,))
        items = cursor.fetchall()
        
        if request.is_json:
            # Convertir les Row objects en dictionnaires
            items_list = []
            for item in items:
                items_list.append({
                    "id": item["item_id"],
                    "name": item["item_name"],
                    "type": item["item_type"],
                    "quantity": item["item_quantity"]
                })
                
            return jsonify({
                "success": True,
                "character_name": character["name"],
                "items": items_list,
                "sort": {
                    "by": sort_by,
                    "order": order
                }
            }), 200
        
        return render_template('inventory.html',
                               items=items,
                               character_name=character["name"],
                               sort_by=sort_by,
                               order=order)
                               
    except Exception as e:
        current_app.logger.error(f"Error in inventory view: {str(e)}")
        
        if request.is_json:
            return jsonify({
                "success": False,
                "message": f"Erreur serveur: {str(e)}"
            }), 500
        
        flash(f'Erreur serveur: {str(e)}', 'danger')
        return redirect(url_for('game.character_list'))
        
    finally:
        cursor.close()
        conn.close()

# Les autres routes d'inventaire (add_item, edit_item, delete_item, consume_item) avec la même structure