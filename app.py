import os
from flask import Flask, jsonify, request
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, get_jwt_identity, jwt_required

from init_db import get_db_connection, init_db
from models.user import User
from routes.auth_routes import auth_bp
from routes.character_routes import character_bp
from routes.game_routes import game_bp
from routes.inventory_routes import inventory_bp

# Charger les variables d'environnement
from dotenv import load_dotenv
load_dotenv()

# Initialiser l'application Flask
app = Flask(__name__)

# Configuration
app.config["JWT_SECRET_KEY"] = os.getenv('SECRET_KEY', 'default-secret-key-for-jwt')
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 604800  
app.config["CORS_HEADERS"] = "Content-Type"
app.config["JSON_SORT_KEYS"] = False  # Préserver l'ordre des clés dans les réponses JSON
app.config["JWT_COOKIE_SECURE"] = False  # Mettre à True en production avec HTTPS
app.config["JWT_COOKIE_SAMESITE"] = "Lax"  # Permet la persistance lors de la navigation
app.config["JWT_TOKEN_LOCATION"] = ["headers", "cookies"]  # Accepter le token dans les en-têtes ou les cookies

# Initialiser les extensions
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
CORS(app, resources={r"/api/*": {"origins": "*"}})


# Enregistrer les blueprints
app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
app.register_blueprint(character_bp, url_prefix='/api/v1/characters')
app.register_blueprint(game_bp, url_prefix='/api/v1/game')
app.register_blueprint(inventory_bp, url_prefix='/api/v1/inventory')

# Route par défaut
@app.route('/api/v1/')
def home():
    return jsonify({
        "message": "Bienvenue sur l'API du RPG",
        "version": "1.0.0",
        "status": "online",
        "docs": "/api/v1/docs"
    })

# Documentation simplifiée de l'API
@app.route('/api/v1/docs/')
def api_docs():
    endpoints = [
        {"path": "/api/v1/auth/register/", "method": "POST", "description": "Inscription d'un nouvel utilisateur"},
        {"path": "/api/v1/auth/login/", "method": "POST", "description": "Connexion et obtention du token JWT"},
        {"path": "/api/v1/auth/user/", "method": "GET", "description": "Obtenir les informations de l'utilisateur connecté"},
        {"path": "/api/v1/characters/", "method": "GET", "description": "Liste des personnages de l'utilisateur"},
        {"path": "/api/v1/characters/", "method": "POST", "description": "Création d'un nouveau personnage"},
        {"path": "/api/v1/characters/{id}/", "method": "GET", "description": "Détails d'un personnage"},
        {"path": "/api/v1/characters/{id}/select/", "method": "POST", "description": "Sélectionner un personnage actif"},
        {"path": "/api/v1/inventory/", "method": "GET", "description": "Liste des objets du personnage actif"},
        {"path": "/api/v1/inventory/", "method": "POST", "description": "Ajouter un nouvel objet"},
        {"path": "/api/v1/inventory/{id}/", "method": "GET", "description": "Détails d'un objet"},
        {"path": "/api/v1/inventory/{id}/", "method": "PUT", "description": "Modifier un objet"},
        {"path": "/api/v1/inventory/{id}/", "method": "DELETE", "description": "Supprimer un objet"},
        {"path": "/api/v1/inventory/{id}/consume/", "method": "POST", "description": "Consommer un objet"},
        {"path": "/api/v1/inventory/types/", "method": "GET", "description": "Liste des types d'objets"},
        {"path": "/api/v1/game/versus/", "method": "GET", "description": "Mode Versus - Liste des personnages disponibles"},
        {"path": "/api/v1/game/versus/fight/", "method": "POST", "description": "Mode Versus - Simuler un combat"},
        {"path": "/api/v1/game/quests/", "method": "GET", "description": "Mode Quête - Liste des quêtes disponibles"},
        {"path": "/api/v1/game/quests/{id}/", "method": "POST", "description": "Mode Quête - Démarrer une quête"},
        {"path": "/api/v1/game/board/", "method": "GET", "description": "Mode Plateau - Initialiser un nouveau jeu"},
        {"path": "/api/v1/game/board/{session_id}/play/", "method": "POST", "description": "Mode Plateau - Jouer un tour"},
        {"path": "/api/v1/game/board/{session_id}/", "method": "GET", "description": "Mode Plateau - Statut d'une session"},
    ]
    
    return jsonify({
        "title": "API RPG Documentation",
        "version": "1.0.0",
        "base_url": "/api/v1",
        "auth": "JWT (Bearer Token)",
        "endpoints": endpoints
    })

# Gestion globale des erreurs
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({"error": "Internal server error"}), 500

# Fonction pour obtenir l'utilisateur courant
def get_current_user():
    user_id = get_jwt_identity()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM user WHERE user_id = ?', (user_id,))
    user_data = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if user_data:
        return User(
            user_data['user_id'], 
            user_data['user_login'], 
            user_data['user_mail'],
            user_data['active_character_id']
        )
    return None

# Exporter cette fonction pour les autres modules
app.get_current_user = get_current_user

# Initialisation de la base de données
with app.app_context():
    init_db()
    print("Base de données initialisée")
    
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    
    print(f"Starting RPG API server on port {port}...")
    if debug:
        print("Running in DEBUG mode")
    else:
        print("Running in PRODUCTION mode")
    
    app.run(host='0.0.0.0', port=port, debug=debug)