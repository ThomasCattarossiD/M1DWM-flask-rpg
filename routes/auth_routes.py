from flask import Blueprint, jsonify, request
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from init_db import get_db_connection
from models.user import User

auth_bp = Blueprint('auth', __name__)
bcrypt = Bcrypt()

@auth_bp.route('/register/', methods=['POST'])
def register():
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Aucune donnée fournie"}), 400
    
    email = data.get('email')
    username = data.get('username')
    password = data.get('password')
    
    if not email or not username or not password:
        return jsonify({"error": "Tous les champs sont obligatoires"}), 400
    
    # Vérifier si l'email est déjà utilisé
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM user WHERE user_mail = ?', (email,))
    account = cursor.fetchone()
    
    if account:
        cursor.close()
        conn.close()
        return jsonify({"error": "Cet email est déjà utilisé"}), 409
    
    # Hacher le mot de passe
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    
    # Insérer le nouvel utilisateur
    cursor.execute(
        'INSERT INTO user (user_login, user_password, user_mail) VALUES (?, ?, ?)',
        (username, hashed_password, email)
    )
    conn.commit()
    
    # Récupérer l'ID de l'utilisateur nouvellement créé
    user_id = cursor.lastrowid
    cursor.close()
    conn.close()
    
    # Générer un token JWT
    access_token = create_access_token(identity=user_id)
    
    return jsonify({
        "message": "Compte créé avec succès",
        "user": {
            "id": user_id,
            "username": username,
            "email": email
        },
        "token": access_token
    }), 201

@auth_bp.route('/login/', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Aucune donnée fournie"}), 400
    
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"error": "Email et mot de passe requis"}), 400
    
    # Vérifier les identifiants
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM user WHERE user_mail = ?', (email,))
    user_data = cursor.fetchone()
    
    if not user_data or not bcrypt.check_password_hash(user_data['user_password'], password):
        cursor.close()
        conn.close()
        return jsonify({"error": "Email ou mot de passe incorrect"}), 401
    
    # Mettre à jour la date de dernière connexion
    cursor.execute(
        'UPDATE user SET user_date_login = CURRENT_TIMESTAMP WHERE user_id = ?', 
        (user_data['user_id'],)
    )
    conn.commit()
    cursor.close()
    conn.close()
    
    # Générer un token JWT
    access_token = create_access_token(identity=user_data['user_id'])
    
    return jsonify({
        "message": "Connexion réussie",
        "user": {
            "id": user_data['user_id'],
            "username": user_data['user_login'],
            "email": user_data['user_mail'],
            "active_character_id": user_data['active_character_id']
        },
        "token": access_token
    }), 200

@auth_bp.route('/user/', methods=['GET'])
@jwt_required()
def get_user():
    user_id = get_jwt_identity()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM user WHERE user_id = ?', (user_id,))
    user_data = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not user_data:
        return jsonify({"error": "Utilisateur non trouvé"}), 404
    
    return jsonify({
        "id": user_data['user_id'],
        "username": user_data['user_login'],
        "email": user_data['user_mail'],
        "active_character_id": user_data['active_character_id'],
        "date_registered": user_data['user_date_new'],
        "last_login": user_data['user_date_login']
    }), 200