import os

from dotenv import load_dotenv
from flask import (Flask, flash, redirect, render_template, request, session,
                   url_for)
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
        email = request.form['email']
        password = request.form['password']

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
            return redirect(url_for('inventory'))
        else:
            flash('Email ou mot de passe incorrect !', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        recheck_password = request.form['recheck_password']

        if not email or not username or not password or not recheck_password:
            flash('Tous les champs sont obligatoires !', 'danger')
            return redirect(url_for('register'))

        if password != recheck_password:
            flash('Les mots de passe ne correspondent pas !', 'danger')
            return redirect(url_for('register'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM user WHERE user_mail = ?', (email,))
        account = cursor.fetchone()

        if account:
            flash('Cet email est déjà utilisé!', 'danger')
        else:
            cursor.execute(
                'INSERT INTO user (user_login, user_password, user_mail) VALUES (?, ?, ?)',
                (username, hashed_password, email)
            )
            conn.commit()
            user_id = cursor.lastrowid
            user = User(user_id, username, email)
            login_user(user)
            flash('Compte créé avec succès !', 'success')
            return redirect(url_for('home'))

        cursor.close()
        conn.close()

    return render_template('register.html')

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('Vous avez été déconnecté !', 'success')
    return redirect(url_for('login'))

@app.route('/inventory')
@login_required
def inventory():
    if not current_user.active_character_id:
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
    items = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('inventory.html', 
                         items=items, 
                         character_name=character['name'], 
                         sort_by=sort_by, 
                         order=order)

@app.route('/add_item', methods=['GET', 'POST'])
@login_required
def add_item():
    if not current_user.active_character_id:
        flash('Veuillez d\'abord sélectionner un personnage.', 'warning')
        return redirect(url_for('game.character_list'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM item_types')
    item_types = cursor.fetchall()

    if request.method == 'POST':
        name = request.form['name']
        type_id = request.form['type_id']
        quantity = request.form['quantity']

        if not name or not type_id or not quantity:
            flash('Tous les champs sont obligatoires !', 'danger')
            return redirect(url_for('add_item'))

        cursor.execute('''
            INSERT INTO inventory (character_id, name, type_id, quantity) 
            VALUES (?, ?, ?, ?)''',
            (current_user.active_character_id, name, type_id, quantity))
        
        conn.commit()
        cursor.close()
        conn.close()
        flash('Objet ajouté avec succès !', 'success')
        return redirect(url_for('inventory'))

    cursor.close()
    conn.close()
    return render_template('edit_item.html', action='Ajouter', item=None, item_types=item_types)

@app.route('/delete/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    if 'loggedin' not in session:
        flash('Veuillez vous connecter.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM inventory WHERE id = ?', (item_id,))
    conn.commit()
    cursor.close()
    conn.close()

    flash('Objet supprimé avec succès !', 'success')
    return redirect(url_for('inventory'))

@app.route('/consume/<int:item_id>', methods=['POST'])
@login_required
def consume_item(item_id):
    if not current_user.active_character_id:
        flash('Veuillez d\'abord sélectionner un personnage.', 'warning')
        return redirect(url_for('game.character_list'))

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Vérifier que l'objet appartient au personnage actif
    cursor.execute('''
        SELECT inventory.*, item_types.type_name 
        FROM inventory 
        JOIN item_types ON inventory.type_id = item_types.id 
        WHERE inventory.id = ? AND inventory.character_id = ?
    ''', (item_id, current_user.active_character_id))
    
    item = cursor.fetchone()
    
    if not item:
        flash('Objet non trouvé.', 'error')
        return redirect(url_for('inventory'))
    
    if item['type_name'] not in ['potion', 'plante']:
        flash('Cet objet ne peut pas être consommé.', 'warning')
        return redirect(url_for('inventory'))
    
    # Appliquer les effets de l'objet
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
    else:
        cursor.execute('DELETE FROM inventory WHERE id = ?', (item_id,))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    flash(f'Objet consommé! {effect_message}', 'success')
    return redirect(url_for('inventory'))

@app.route('/edit/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    if 'loggedin' not in session:
        flash('Veuillez vous connecter pour modifier un item.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM inventory WHERE id = ?', (item_id,))
    item = cursor.fetchone()

    if not item:
        flash("L'objet n'existe pas.", 'danger')
        return redirect(url_for('inventory'))

    cursor.execute('SELECT * FROM item_types')
    item_types = cursor.fetchall()

    if request.method == 'POST':
        name = request.form['name']
        type_id = request.form['type_id']
        quantity = request.form['quantity']

        if not name or not type_id or not quantity:
            flash('Tous les champs sont obligatoires !', 'danger')
            return redirect(url_for('edit_item', item_id=item_id))

        cursor.execute('UPDATE inventory SET name = ?, type_id = ?, quantity = ? WHERE id = ?',
                       (name, type_id, quantity, item_id))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Objet modifié avec succès !', 'success')
        return redirect(url_for('inventory'))

    cursor.close()
    conn.close()
    return render_template('edit_item.html', action='Modifier', item=item, item_types=item_types)

if __name__ == '__main__':
    app.run(debug=True)
