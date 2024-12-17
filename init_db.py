import os
import sqlite3

DATABASE_PATH = os.getenv('DATABASE_PATH', 'gestion_inventaire.db')

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

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

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS item_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type_name TEXT NOT NULL
    )
    ''')


    cursor.execute('''insert into item_types (type_name) values ('potion')''')
    cursor.execute('''insert into item_types (type_name) values ('plante')''')
    cursor.execute('''insert into item_types (type_name) values ('arme')''')
    cursor.execute('''insert into item_types (type_name) values ('clé')''')
    cursor.execute('''insert into item_types (type_name) values ('armure')''')


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
        user_id INTEGER,
        FOREIGN KEY (user_id) REFERENCES user (user_id)
    )
    ''')

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

    conn.commit()
    cursor.close()
    conn.close()
    print("Base de données initialisée avec succès.")

if __name__ == '__main__':
    init_db()
