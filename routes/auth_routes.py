from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from flask_cors import cross_origin

from init_db import get_db_connection
from models.user import User

auth_bp = Blueprint('auth', __name__)
bcrypt = Bcrypt()

@auth_bp.route('/login', methods=['GET', 'POST', 'OPTIONS'])
@cross_origin()
def login():
    if request.method == 'OPTIONS':
        # Permet de gérer les requêtes preflight CORS
        return '', 200
        
    if request.method == 'POST':
        # Vérifier si la requête est JSON (API) ou form-data (navigateur)
        if request.is_json:
            data = request.get_json()
            email = data.get('email')
            password = data.get('password')
        else:
            email = request.form.get('email')
            password = request.form.get('password')
            
        if not email or not password:
            if request.is_json:
                return jsonify({"success": False, "message": "Email et mot de passe requis"}), 400
            flash('Email et mot de passe requis', 'danger')
            return render_template('login.html')
            
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
            
            if request.is_json:
                return jsonify({
                    "success": True, 
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "active_character_id": user.active_character_id
                    }
                }), 200
            return redirect(url_for('inventory.view'))
        
        if request.is_json:
            return jsonify({"success": False, "message": "Email ou mot de passe incorrect"}), 401
        flash('Email ou mot de passe incorrect', 'danger')
        return render_template('login.html')
    
    # GET request
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST', 'OPTIONS'])
@cross_origin()
def register():
    if request.method == 'OPTIONS':
        return '', 200
        
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            email = data.get('email')
            username = data.get('username')
            password = data.get('password')
            recheck_password = data.get('recheck_password')
        else:
            email = request.form.get('email')
            username = request.form.get('username')
            password = request.form.get('password')
            recheck_password = request.form.get('recheck_password')
        
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
            if request.is_json:
                return jsonify({"success": False, "errors": errors}), 400
            for field, error in errors.items():
                flash(error, 'danger')
            return render_template('register.html')
            
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM user WHERE user_mail = ?', (email,))
        account = cursor.fetchone()
        
        if account:
            cursor.close()
            conn.close()
            if request.is_json:
                return jsonify({"success": False, "errors": {"email": "Cet email est déjà utilisé"}}), 400
            flash('Cet email est déjà utilisé', 'danger')
            return render_template('register.html')
            
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
            
            if request.is_json:
                return jsonify({
                    "success": True, 
                    "message": "Compte créé avec succès",
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email
                    }
                }), 201
                
            flash('Compte créé avec succès', 'success')
            return redirect(url_for('inventory.view'))
            
        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()
            if request.is_json:
                return jsonify({"success": False, "message": f"Erreur serveur: {str(e)}"}), 500
            flash(f'Erreur serveur: {str(e)}', 'danger')
            return render_template('register.html')
    
    # GET request
    return render_template('register.html')

@auth_bp.route('/logout', methods=['POST', 'OPTIONS'])
@cross_origin()
def logout():
    if request.method == 'OPTIONS':
        return '', 200
        
    logout_user()
    
    if request.is_json:
        return jsonify({"success": True, "message": "Déconnexion réussie"}), 200
        
    flash('Vous avez été déconnecté', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/api/check_auth', methods=['GET', 'OPTIONS'])
@cross_origin()
def check_auth():
    if request.method == 'OPTIONS':
        return '', 200
        
    if current_user.is_authenticated:
        return jsonify({
            "isAuthenticated": True,
            "user": {
                "id": current_user.id,
                "username": current_user.username,
                "email": current_user.email,
                "active_character_id": current_user.active_character_id
            }
        }), 200
    
    return jsonify({"isAuthenticated": False}), 401