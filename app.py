import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, jsonify, request, redirect, url_for
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user
from datetime import datetime, timedelta
from init_db import get_db_connection, init_db
from models.user import User

# Routes
from routes.auth_routes import auth_bp
from routes.game_routes import game_bp
from routes.inventory_routes import inventory_bp
from routes.api_routes import api_bp
from routes.inv_routes import inv_bp

# Configuration du logging
def setup_logging(app):
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/flask_app.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Application startup')

# Création et configuration de l'application
# Dans app.py, ajoute ces configurations
def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    # Configuration supplémentaire pour les sessions
    app.config['SESSION_COOKIE_SAMESITE'] = 'None'  # Requis pour les requêtes cross-origin
    app.config['SESSION_COOKIE_SECURE'] = True  # Recommandé pour la sécurité
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)  # Session plus longue
    
    # Configuration CORS mise à jour
    CORS(app, 
         resources={
             r"/*": {
                 "origins": ["http://localhost:4200", "http://localhost:3000", "http://127.0.0.1:4200"],
                 "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                 "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
                 "supports_credentials": True,
                 "expose_headers": ["Access-Control-Allow-Origin", "Access-Control-Allow-Credentials"]
             }
         })
    
    # Hook pour les entêtes CORS
    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')
        
        # Important: Corriger l'entête Access-Control-Allow-Origin pour les credentials
        # Ne pas utiliser '*' avec credentials, spécifier l'origine exacte
        origin = request.headers.get('Origin')
        if origin in ["http://localhost:4200", "http://localhost:3000", "http://127.0.0.1:4200"]:
            response.headers.set('Access-Control-Allow-Origin', origin)
        
        return response
    
    # Initialisation des extensions
    bcrypt = Bcrypt(app)
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # Personnaliser le gestionnaire d'unauthorised pour l'API
    @login_manager.unauthorized_handler
    def unauthorized_handler():
        return jsonify({
            "success": False,
            "message": "Authentification requise"
        }), 401
       
    # Configuration des blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(game_bp, url_prefix='/game')
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(inv_bp, url_prefix='/inv')
    
    # Initialisation de la base de données
    with app.app_context():
        init_db()
    
    # Configuration du gestionnaire d'utilisateur
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
    
    # Route de base pour vérifier que l'API fonctionne
    @app.route('/api/health')
    def health_check():
        return jsonify({"status": "ok", "message": "API is running"}), 200
    
    # Gestionnaire d'erreur global pour les erreurs 404
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Resource not found", "status": 404}), 404
    
    # Gestionnaire d'erreur global pour les erreurs 500
    @app.errorhandler(500)
    def server_error(error):
        app.logger.error(f"Server error: {str(error)}")
        return jsonify({"error": "Internal server error", "status": 500}), 500
    
    setup_logging(app)
    return app

# Point d'entrée de l'application
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)