import os

from dotenv import load_dotenv
from flask import (Flask, redirect, request, session, url_for, jsonify)
from flask_cors import CORS 
from flask_bcrypt import Bcrypt
from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user)
from init_db import get_db_connection
from models.user import User
from routes.game_routes import game_bp

# Charger les variables d'environnement
load_dotenv()

# Initialiser l'application Flask
app = Flask(__name__)
CORS(app)

# Charger la clé secrète depuis le fichier .env pour sécuriser les sessions
app.secret_key = os.getenv('SECRET_KEY')

# Initialiser Bcrypt pour le hachage des mots de passe
bcrypt = Bcrypt(app)

app.register_blueprint(game_bp, url_prefix='/game')

# Après l'initialisation de l'app Flask
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM user WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if user:
        return User(
            user['user_id'], 
            user['user_login'], 
            user['user_mail'],
            user['active_character_id']
        )
    return None

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('inventory'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email') or request.json.get('email')
        password = request.form.get('password') or request.json.get('password')

        if not email or not password:
            return jsonify({"success": False, "message": "Email ou mot de passe manquant"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM user WHERE user_mail = ?', (email,))
        user_data = cursor.fetchone()
        cursor.close()
        conn.close()

        if user_data and bcrypt.check_password_hash(user_data['user_password'], password):
            user = User(
                user_data['user_id'], 
                user_data['user_login'], 
                user_data['user_mail'],
                user_data['active_character_id']
            )
            login_user(user)
            return jsonify({
                "success": True, 
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "active_character_id": user.active_character_id
                },
                "message": "Connexion réussie"
            })
        else:
            return jsonify({"success": False, "message": "Email ou mot de passe incorrect"}), 401

    # Si c'est une requête GET, informer que seules les requêtes POST sont acceptées
    return jsonify({"success": False, "message": "Méthode non autorisée"}), 405

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Support des données JSON et form
        email = request.form.get('email') or request.json.get('email')
        username = request.form.get('username') or request.json.get('username')
        password = request.form.get('password') or request.json.get('password')
        recheck_password = request.form.get('recheck_password') or request.json.get('recheck_password')

        if not email or not username or not password or not recheck_password:
            return jsonify({"success": False, "message": "Tous les champs sont obligatoires"}), 400

        if password != recheck_password:
            return jsonify({"success": False, "message": "Les mots de passe ne correspondent pas"}), 400

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM user WHERE user_mail = ?', (email,))
        account = cursor.fetchone()

        if account:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "Cet email est déjà utilisé"}), 409
        else:
            cursor.execute(
                'INSERT INTO user (user_login, user_password, user_mail) VALUES (?, ?, ?)',
                (username, hashed_password, email)
            )
            conn.commit()
            user_id = cursor.lastrowid
            cursor.close()
            conn.close()
            
            user = User(user_id, username, email)
            login_user(user)
            
            return jsonify({
                "success": True, 
                "user": {
                    "id": user_id,
                    "username": username,
                    "email": email
                },
                "message": "Compte créé avec succès"
            }), 201

    # Si c'est une requête GET, informer que seules les requêtes POST sont acceptées
    return jsonify({"success": False, "message": "Méthode non autorisée"}), 405

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({"success": True, "message": "Déconnexion réussie"})

@app.route('/inventory')
@login_required
def inventory():
    if not current_user.active_character_id:
        return jsonify({
            "success": False, 
            "message": "Aucun personnage actif", 
            "redirect": "/game/character_list"
        }), 400

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

    # Récupérer les informations du personnage actif
    cursor.execute('SELECT name FROM characters WHERE id = ?', (current_user.active_character_id,))
    character = cursor.fetchone()

    query = f'''
        SELECT inventory.id AS item_id, inventory.name AS item_name, 
               item_types.type_name AS item_type, inventory.quantity AS item_quantity 
        FROM inventory 
        JOIN item_types ON inventory.type_id = item_types.id 
        WHERE inventory.character_id = ?
        ORDER BY {sort_by} {order}
    '''
    cursor.execute(query, (current_user.active_character_id,))
    items_data = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Convertir les résultats en liste de dictionnaires pour JSON
    items = []
    for item in items_data:
        items.append({
            "id": item['item_id'],
            "name": item['item_name'],
            "type": item['item_type'],
            "quantity": item['item_quantity']
        })

    return jsonify({
        "success": True,
        "character_name": character['name'] if character else None,
        "items": items,
        "sort_by": sort_by,
        "order": order
    })


@app.route('/add_item', methods=['POST'])
@login_required
def add_item():
    if not current_user.active_character_id:
        return jsonify({
            "success": False, 
            "message": "Aucun personnage actif", 
            "redirect": "/game/character_list"
        }), 400

    # Support des données JSON et form
    name = request.form.get('name') or request.json.get('name')
    type_id = request.form.get('type_id') or request.json.get('type_id')
    quantity = request.form.get('quantity') or request.json.get('quantity')

    if not name or not type_id or not quantity:
        return jsonify({"success": False, "message": "Tous les champs sont obligatoires"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO inventory (character_id, name, type_id, quantity) 
            VALUES (?, ?, ?, ?)''',
            (current_user.active_character_id, name, type_id, quantity))
        
        item_id = cursor.lastrowid
        conn.commit()
        
        # Récupérer les détails du type de l'objet pour la réponse
        cursor.execute('SELECT type_name FROM item_types WHERE id = ?', (type_id,))
        type_name = cursor.fetchone()['type_name']
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True, 
            "message": "Objet ajouté avec succès",
            "item": {
                "id": item_id,
                "name": name,
                "type": type_name,
                "quantity": quantity
            }
        }), 201
        
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"success": False, "message": f"Erreur: {str(e)}"}), 500

@app.route('/delete/<int:item_id>', methods=['DELETE'])
@login_required
def delete_item(item_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Vérifier que l'objet appartient au personnage actif
        cursor.execute('SELECT * FROM inventory WHERE id = ? AND character_id = ?', 
                       (item_id, current_user.active_character_id))
        item = cursor.fetchone()
        
        if not item:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "Objet non trouvé ou non autorisé"}), 404
        
        cursor.execute('DELETE FROM inventory WHERE id = ?', (item_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"success": True, "message": "Objet supprimé avec succès", "id": item_id})
        
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"success": False, "message": f"Erreur: {str(e)}"}), 500

@app.route('/consume/<int:item_id>', methods=['POST'])
@login_required
def consume_item(item_id):
    if not current_user.active_character_id:
        return jsonify({
            "success": False, 
            "message": "Aucun personnage actif", 
            "redirect": "/game/character_list"
        }), 400

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
            return jsonify({"success": False, "message": "Objet non trouvé"}), 404
        
        if item['type_name'] not in ['potion', 'plante']:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "Cet objet ne peut pas être consommé"}), 400
        
        # Appliquer les effets de l'objet
        effect = {}
        if item['type_name'] == 'potion':
            cursor.execute('''
                UPDATE characters 
                SET health = MIN(health + 20, 100) 
                WHERE id = ?
            ''', (current_user.active_character_id,))
            effect = {"type": "health", "value": 20}
        elif item['type_name'] == 'plante':
            cursor.execute('''
                UPDATE characters 
                SET attack = attack + 5 
                WHERE id = ?
            ''', (current_user.active_character_id,))
            effect = {"type": "attack", "value": 5}
        
        # Réduire la quantité de l'objet
        new_quantity = item['quantity'] - 1
        if new_quantity > 0:
            cursor.execute('''
                UPDATE inventory 
                SET quantity = quantity - 1 
                WHERE id = ?
            ''', (item_id,))
            item_status = {"id": item_id, "quantity": new_quantity}
        else:
            cursor.execute('DELETE FROM inventory WHERE id = ?', (item_id,))
            item_status = {"id": item_id, "deleted": True}
        
        conn.commit()
        
        # Récupérer les nouvelles stats du personnage pour la réponse
        cursor.execute('SELECT health, attack FROM characters WHERE id = ?', 
                      (current_user.active_character_id,))
        character_stats = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True, 
            "message": f"Objet consommé avec succès", 
            "effect": effect,
            "item": item_status,
            "character": {
                "health": character_stats['health'],
                "attack": character_stats['attack']
            }
        })
        
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"success": False, "message": f"Erreur: {str(e)}"}), 500

@app.route('/edit/<int:item_id>', methods=['GET', 'PUT'])
@login_required
def edit_item(item_id):
    if not current_user.active_character_id:
        return jsonify({
            "success": False, 
            "message": "Aucun personnage actif", 
            "redirect": "/game/character_list"
        }), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'GET':
        cursor.execute('SELECT * FROM inventory WHERE id = ? AND character_id = ?', 
                      (item_id, current_user.active_character_id))
        item = cursor.fetchone()
        
        if not item:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "Objet non trouvé ou non autorisé"}), 404
        
        cursor.execute('SELECT * FROM item_types')
        item_types_data = cursor.fetchall()
        
        # Convertir en liste pour JSON
        item_types = []
        for type_item in item_types_data:
            item_types.append({
                "id": type_item['id'],
                "name": type_item['type_name']
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "item": {
                "id": item['id'],
                "name": item['name'],
                "type_id": item['type_id'],
                "quantity": item['quantity']
            },
            "item_types": item_types
        })
    
    elif request.method == 'PUT':
        # Support des données JSON
        name = request.json.get('name')
        type_id = request.json.get('type_id')
        quantity = request.json.get('quantity')
        
        if not name or not type_id or not quantity:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "Tous les champs sont obligatoires"}), 400
        
        try:
            # Vérifier que l'objet appartient au personnage actif
            cursor.execute('SELECT id FROM inventory WHERE id = ? AND character_id = ?', 
                          (item_id, current_user.active_character_id))
            
            if not cursor.fetchone():
                cursor.close()
                conn.close()
                return jsonify({"success": False, "message": "Objet non trouvé ou non autorisé"}), 404
            
            cursor.execute('UPDATE inventory SET name = ?, type_id = ?, quantity = ? WHERE id = ?',
                           (name, type_id, quantity, item_id))
            
            # Récupérer le nom du type pour la réponse
            cursor.execute('SELECT type_name FROM item_types WHERE id = ?', (type_id,))
            type_data = cursor.fetchone()
            type_name = type_data['type_name'] if type_data else "Unknown"
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return jsonify({
                "success": True, 
                "message": "Objet modifié avec succès",
                "item": {
                    "id": item_id,
                    "name": name,
                    "type": type_name,
                    "type_id": type_id,
                    "quantity": quantity
                }
            })
            
        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": f"Erreur: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
