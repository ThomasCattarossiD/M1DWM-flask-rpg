-- Base de données pour l'application de jeu RPG
PRAGMA foreign_keys = ON;

-- Table des utilisateurs
CREATE TABLE IF NOT EXISTS user (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_login TEXT NOT NULL,
    user_mail TEXT NOT NULL UNIQUE,
    user_password TEXT NOT NULL,
    active_character_id INTEGER DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des types d'objets
CREATE TABLE IF NOT EXISTS item_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type_name TEXT NOT NULL UNIQUE
);

-- Table des personnages
CREATE TABLE IF NOT EXISTS characters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    race TEXT NOT NULL,
    class TEXT NOT NULL,
    health INTEGER NOT NULL DEFAULT 100,
    attack INTEGER NOT NULL DEFAULT 10,
    defense INTEGER NOT NULL DEFAULT 5,
    level INTEGER NOT NULL DEFAULT 1,
    experience INTEGER NOT NULL DEFAULT 0,
    user_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE CASCADE
);

-- Création de la table des races
CREATE TABLE IF NOT EXISTS races (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    health_bonus INTEGER DEFAULT 0,
    attack_bonus INTEGER DEFAULT 0,
    defense_bonus INTEGER DEFAULT 0
);


-- Table d'inventaire des personnages
CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    type_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    description TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE,
    FOREIGN KEY (type_id) REFERENCES item_types(id) ON DELETE CASCADE
);

-- Table des quêtes
CREATE TABLE IF NOT EXISTS quests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    level_required INTEGER NOT NULL DEFAULT 1,
    experience_reward INTEGER NOT NULL DEFAULT 50,
    gold_reward INTEGER NOT NULL DEFAULT 10
);

-- Table des monstres
CREATE TABLE IF NOT EXISTS monsters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    health INTEGER NOT NULL DEFAULT 50,
    attack INTEGER NOT NULL DEFAULT 8,
    defense INTEGER NOT NULL DEFAULT 3,
    level INTEGER NOT NULL DEFAULT 1
);

-- Table des récompenses de quête (objets)
CREATE TABLE IF NOT EXISTS quest_rewards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quest_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    type_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (quest_id) REFERENCES quests(id) ON DELETE CASCADE,
    FOREIGN KEY (type_id) REFERENCES item_types(id) ON DELETE CASCADE
);

-- Table des monstres par quête
CREATE TABLE IF NOT EXISTS quest_monsters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quest_id INTEGER NOT NULL,
    monster_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (quest_id) REFERENCES quests(id) ON DELETE CASCADE,
    FOREIGN KEY (monster_id) REFERENCES monsters(id) ON DELETE CASCADE
);

-- Table des quêtes complétées par les personnages
CREATE TABLE IF NOT EXISTS completed_quests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER NOT NULL,
    quest_id INTEGER NOT NULL,
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE,
    FOREIGN KEY (quest_id) REFERENCES quests(id) ON DELETE CASCADE,
    UNIQUE(character_id, quest_id)
);

-- Table des équipements (objets équipés)
CREATE TABLE IF NOT EXISTS equipped_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER NOT NULL,
    inventory_id INTEGER NOT NULL,
    slot TEXT NOT NULL, -- 'weapon', 'armor', 'accessory', etc.
    equipped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE,
    FOREIGN KEY (inventory_id) REFERENCES inventory(id) ON DELETE CASCADE,
    UNIQUE(character_id, slot)
);

-- Table des statistiques des joueurs
CREATE TABLE IF NOT EXISTS player_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER NOT NULL,
    battles_won INTEGER NOT NULL DEFAULT 0,
    battles_lost INTEGER NOT NULL DEFAULT 0,
    monsters_defeated INTEGER NOT NULL DEFAULT 0,
    quests_completed INTEGER NOT NULL DEFAULT 0,
    items_collected INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE,
    UNIQUE(character_id)
);

-- Table des sessions de jeu (suivi de l'activité)
CREATE TABLE IF NOT EXISTS game_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    character_id INTEGER,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    duration_seconds INTEGER,
    FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE CASCADE,
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE SET NULL
);

-- Données initiales pour les quêtes
INSERT OR IGNORE INTO quests (id, title, description, level_required, experience_reward, gold_reward) VALUES
(1, 'Forêt mystérieuse', 'Explorez la forêt mystérieuse et débarrassez-la de ses monstres.', 1, 50, 20),
(2, 'Caverne des trolls', 'Nettoyez la caverne infestée de trolls.', 2, 100, 50),
(3, 'Nid du dragon', 'Affrontez un dragon et récupérez son trésor.', 5, 500, 200);

-- Données initiales pour les monstres
INSERT OR IGNORE INTO monsters (id, name, health, attack, defense, level) VALUES
(1, 'Gobelin', 40, 6, 2, 1),
(2, 'Loup', 50, 8, 3, 1),
(3, 'Troll', 80, 12, 5, 2),
(4, 'Ogre', 100, 15, 7, 3),
(5, 'Dragon', 200, 25, 15, 5);

-- Association des monstres aux quêtes
INSERT OR IGNORE INTO quest_monsters (quest_id, monster_id, quantity) VALUES
(1, 1, 3), -- 3 Gobelins dans la Forêt mystérieuse
(1, 2, 2), -- 2 Loups dans la Forêt mystérieuse
(2, 3, 2), -- 2 Trolls dans la Caverne des trolls
(2, 4, 1), -- 1 Ogre dans la Caverne des trolls
(3, 5, 1); -- 1 Dragon dans le Nid du dragon

-- Récompenses des quêtes
INSERT OR IGNORE INTO quest_rewards (quest_id, name, type_id, quantity) VALUES
(1, 'Potion de soin', 3, 2),      -- 2 potions pour la quête 1
(1, 'Dague de gobelin', 1, 1),    -- 1 arme pour la quête 1
(2, 'Potion de force', 3, 1),     -- 1 potion pour la quête 2
(2, 'Armure de troll', 2, 1),     -- 1 armure pour la quête 2
(3, 'Épée de dragon', 1, 1),      -- 1 arme pour la quête 3
(3, 'Écaille de dragon', 4, 5);   -- 5 matériaux pour la quête 3


-- Insertion des races de base
INSERT INTO races (name, description, health_bonus, attack_bonus, defense_bonus) VALUES
('Human', 'Versatile and adaptable, humans receive balanced bonuses to all stats', 5, 5, 5),
('Elf', 'Graceful and agile, elves excel in precision attacks', 0, 10, 5),
('Dwarf', 'Sturdy and resilient, dwarves have superior defense', 10, 0, 15),
('Orc', 'Fierce warriors with tremendous strength', 5, 15, 0),
('Halfling', 'Small but nimble, halflings are difficult to hit', 0, 5, 10);
