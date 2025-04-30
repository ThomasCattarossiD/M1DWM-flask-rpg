import sqlite3
import os
from flask import g, current_app

def get_db_connection():
    """Établir une connexion à la base de données"""
    conn = sqlite3.connect(current_app.config['DATABASE_PATH'])
    conn.row_factory = sqlite3.Row
    return conn

def close_db(exception=None):
    """Fermer la connexion à la base de données"""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """Initialiser la base de données avec le schéma"""
    if os.path.exists(current_app.config['DATABASE_PATH']):
        current_app.logger.info("Database already exists. Skipping initialization.")
        return
        
    current_app.logger.info("Initializing database...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Création des tables
    with current_app.open_resource('schema.sql') as f:
        cursor.executescript(f.read().decode('utf8'))
    
    # Insertion des données initiales
    cursor.executescript('''
        -- Types d'objets
        INSERT INTO item_types (type_name) VALUES 
        ('weapon'), ('armor'), ('potion'), ('plante'), ('material');
        
        -- Ajouter d'autres données initiales si nécessaire
    ''')
    
    conn.commit()
    cursor.close()
    conn.close()
    current_app.logger.info("Database initialized successfully.")