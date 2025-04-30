import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, jsonify
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_login import LoginManager

from init_db import get_db_connection, init_db
from models.user import User

# Routes
from routes.auth_routes import auth_bp
from routes.game_routes import game_bp
from routes.inventory_routes import inventory_bp
from routes.api_routes import api_bp

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
def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    # Configuration CORS globale
    CORS(app, 
         resources={
             r"/*": {
                 "origins": ["http://localhost:3000"],
                 "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                 "allow_headers": ["Content-Type", "Authorization"],
                 "supports_credentials": True
             }
         })
    
    # Initialisation des extensions
    bcrypt = Bcrypt(app)
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # Configuration des blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(game_bp, url_prefix='/game')
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    app.register_blueprint(api_bp, url_prefix='/api')
    
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