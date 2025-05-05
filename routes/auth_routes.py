from flask import Blueprint, request, jsonify, make_response
from flask_login import login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from flask_cors import cross_origin

from init_db import get_db_connection
from models.user import User

auth_bp = Blueprint('auth', __name__)
bcrypt = Bcrypt()

@auth_bp.route('/login', methods=['POST', 'OPTIONS'])
@cross_origin()
def login():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response, 200
    
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
    cursor.close()
    conn.close()
        
    if user_data and bcrypt.check_password_hash(user_data['user_password'], password):
        user = User(
            user_data['user_id'], 
            user_data['user_login'], 
            user_data['user_mail'],
            user_data['active_character_id']
        )
        
        # Définir la session comme permanente pour la persistance
        from flask import session
        session.permanent = True
        
        # Login avec remember=True
        login_user(user, remember=True)
        
        # Préparer une réponse avec un cookie de session explicite
        response = jsonify({
            "success": True, 
            "message": "Connexion réussie",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "active_character_id": user.active_character_id
            }
        })
        
        return response, 200
        
    return jsonify({
        "success": False, 
        "message": "Email ou mot de passe incorrect"
    }), 401

@auth_bp.route('/register', methods=['POST', 'OPTIONS'])
@cross_origin()
def register():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response, 200
        
    data = request.get_json()
    email = data.get('email')
    username = data.get('username')
    password = data.get('password')
    recheck_password = data.get('recheck_password')
    
    # Validation
    errors = {}
    if not email:
        errors['email'] = 'Email requis'
    if not username:
        errors['username'] = 'Nom d\'utilisateur requis'
    if not password:
        errors['password'] = 'Mot de passe requis'
    if password != recheck_password:
        errors['recheck_password'] = 'Les mots de passe ne correspondent pas'
        
    if errors:
        return jsonify({
            "success": False, 
            "errors": errors
        }), 400
        
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM user WHERE user_mail = ?', (email,))
    account = cursor.fetchone()
    
    if account:
        cursor.close()
        conn.close()
        return jsonify({
            "success": False, 
            "errors": {"email": "Cet email est déjà utilisé"}
        }), 400
        
    try:
        cursor.execute(
            'INSERT INTO user (user_login, user_password, user_mail) VALUES (?, ?, ?)',
            (username, hashed_password, email)
        )
        conn.commit()
        user_id = cursor.lastrowid
        
        # Connexion automatique après inscription
        user = User(user_id, username, email)
        login_user(user)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True, 
            "message": "Compte créé avec succès",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "active_character_id": None
            }
        }), 201
        
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({
            "success": False, 
            "message": f"Erreur serveur: {str(e)}"
        }), 500

@auth_bp.route('/logout', methods=['POST', 'OPTIONS'])
@cross_origin()
def logout():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response, 200
        
    logout_user()
    
    return jsonify({
        "success": True, 
        "message": "Déconnexion réussie"
    }), 200

@auth_bp.route('/check-auth', methods=['GET', 'OPTIONS'])
@cross_origin()
def check_auth():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response, 200
        
    if current_user.is_authenticated:
        return jsonify({
            "success": True,
            "authenticated": True,
            "user": {
                "id": current_user.id,
                "username": current_user.username,
                "email": current_user.email,
                "active_character_id": current_user.active_character_id
            }
        }), 200
    
    return jsonify({
        "success": True,
        "authenticated": False
    }), 200