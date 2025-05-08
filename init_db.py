import os
import sqlite3
import json

DATABASE_PATH = os.getenv('DATABASE_PATH', 'rpg.db')

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Table des utilisateurs
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_login TEXT NOT NULL,
        user_password TEXT NOT NULL,
        user_mail TEXT UNIQUE NOT NULL,
        user_date_new DATETIME DEFAULT CURRENT_TIMESTAMP,
        user_date_login DATETIME,
        user_compte_id INTEGER DEFAULT 0,
        active_character_id INTEGER REFERENCES characters(id)
    )
    ''')

    # Table des types d'objets
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS item_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type_name TEXT NOT NULL
    )
    ''')

    # Vérifier si les types d'objets existent déjà
    cursor.execute('SELECT COUNT(*) FROM item_types')
    count = cursor.fetchone()[0]
    
    if count == 0:
        # Insérer les types d'objets de base
        cursor.execute('''INSERT INTO item_types (type_name) VALUES ('potion')''')
        cursor.execute('''INSERT INTO item_types (type_name) VALUES ('plante')''')
        cursor.execute('''INSERT INTO item_types (type_name) VALUES ('arme')''')
        cursor.execute('''INSERT INTO item_types (type_name) VALUES ('clé')''')
        cursor.execute('''INSERT INTO item_types (type_name) VALUES ('armure')''')

    # Table des personnages
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS characters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        race TEXT NOT NULL,
        class TEXT NOT NULL,
        level INTEGER DEFAULT 1,
        health INTEGER NOT NULL,
        attack INTEGER NOT NULL,
        defense INTEGER NOT NULL,
        experience INTEGER DEFAULT 0,
        user_id INTEGER,
        FOREIGN KEY (user_id) REFERENCES user (user_id)
    )
    ''')

    # Table de l'inventaire
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        character_id INTEGER,
        name TEXT NOT NULL,
        type_id INTEGER,
        quantity INTEGER DEFAULT 0,
        FOREIGN KEY (character_id) REFERENCES characters(id),
        FOREIGN KEY (type_id) REFERENCES item_types(id)
    )
    ''')

    # Table des objets spécifiques aux personnages
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS character_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        character_id INTEGER,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        effect TEXT,
        FOREIGN KEY (character_id) REFERENCES characters (id)
    )
    ''')

    # Table des sessions de jeu de plateau
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS board_game_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        character_id INTEGER NOT NULL,
        current_position INTEGER DEFAULT 0,
        board_length INTEGER DEFAULT 20,
        is_completed BOOLEAN DEFAULT 0,
        is_game_over BOOLEAN DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (character_id) REFERENCES characters(id)
    )
    ''')

    # Table des éléments du plateau de jeu
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS board_game_elements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        position INTEGER NOT NULL,
        element_type TEXT NOT NULL,
        element_data TEXT,
        is_consumed BOOLEAN DEFAULT 0,
        FOREIGN KEY (session_id) REFERENCES board_game_sessions(id)
    )
    ''')

    # Table pour les combats PvP
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pvp_battles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player1_id INTEGER NOT NULL,
        player2_id INTEGER NOT NULL,
        winner_id INTEGER,
        battle_data TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (player1_id) REFERENCES characters(id),
        FOREIGN KEY (player2_id) REFERENCES characters(id),
        FOREIGN KEY (winner_id) REFERENCES characters(id)
    )
    ''')

    # Table pour les quêtes complétées
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS completed_quests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        character_id INTEGER NOT NULL,
        quest_id INTEGER NOT NULL,
        success BOOLEAN DEFAULT 0,
        quest_data TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (character_id) REFERENCES characters(id)
    )
    ''')

    # Table pour les définitions des quêtes
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS quests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        difficulty INTEGER DEFAULT 1,
        recommended_level INTEGER DEFAULT 1,
        reward_experience INTEGER DEFAULT 10,
        reward_item_id INTEGER,
        monster_data TEXT,
        FOREIGN KEY (reward_item_id) REFERENCES item_types(id)
    )
    ''')

    # Vérifier si les quêtes existent déjà
    cursor.execute('SELECT COUNT(*) FROM quests')
    count = cursor.fetchone()[0]
    
    if count == 0:
        # Insérer quelques quêtes par défaut
        quests = [
            (1, 'La Forêt Sombre', 'Explorez la forêt sombre et affrontez les monstres qui s\'y cachent.', 1, 1, 50, 
             json.dumps({"name": "Forest Monster", "health": 50, "attack": 10})),
            (2, 'Les Grottes Mystérieuses', 'Descendez dans les grottes mystérieuses et découvrez leurs secrets.', 2, 2, 100, 
             json.dumps({"name": "Cave Troll", "health": 80, "attack": 15})),
            (3, 'Le Donjon du Dragon', 'Affrontez le terrible dragon qui terrorise la région.', 3, 3, 200, 
             json.dumps({"name": "Dragon", "health": 200, "attack": 40}))
        ]
        
        for quest in quests:
            cursor.execute('''
                INSERT INTO quests (id, name, description, difficulty, recommended_level, reward_experience, monster_data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', quest)

    conn.commit()
    cursor.close()
    conn.close()
    print("Base de données initialisée avec succès.")

if __name__ == '__main__':
    init_db()