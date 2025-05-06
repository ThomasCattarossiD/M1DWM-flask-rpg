PRAGMA foreign_keys = ON;

-- 1) Table des utilisateurs
CREATE TABLE IF NOT EXISTS user (
    user_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_login         TEXT    NOT NULL UNIQUE,
    user_mail          TEXT    NOT NULL UNIQUE,
    user_password      TEXT    NOT NULL,
    active_character_id INTEGER,
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2) Types d’objets
CREATE TABLE IF NOT EXISTS item_types (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    type_name  TEXT    NOT NULL UNIQUE
);

-- initialisation des types
INSERT OR IGNORE INTO item_types (id, type_name) VALUES
    (1, 'Weapon'),
    (2, 'Armor'),
    (3, 'Potion'),
    (4, 'Material');

-- 3) Table des races
CREATE TABLE IF NOT EXISTS races (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT    NOT NULL UNIQUE,
    description    TEXT,
    health_bonus   INTEGER DEFAULT 0,
    attack_bonus   INTEGER DEFAULT 0,
    defense_bonus  INTEGER DEFAULT 0
);

-- initialisation des races
INSERT OR IGNORE INTO races (id, name, description, health_bonus, attack_bonus, defense_bonus) VALUES
    (1, 'Human',    'Versatile and adaptable, balanced bonuses', 5, 5, 5),
    (2, 'Elf',      'Graceful and agile, precision attacks',   0, 10, 5),
    (3, 'Dwarf',    'Sturdy and resilient, superior defense', 10, 0, 15),
    (4, 'Orc',      'Fierce warriors with tremendous strength',5, 15, 0),
    (5, 'Halfling', 'Small but nimble, difficult to hit',       0, 5, 10);

-- 4) Table des personnages
CREATE TABLE IF NOT EXISTS characters (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL,
    race         TEXT    NOT NULL,
    class        TEXT    NOT NULL,
    health       INTEGER NOT NULL DEFAULT 100,
    attack       INTEGER NOT NULL DEFAULT 10,
    defense      INTEGER NOT NULL DEFAULT 5,
    level        INTEGER NOT NULL DEFAULT 1,
    experience   INTEGER NOT NULL DEFAULT 0,
    user_id      INTEGER NOT NULL,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 5) Inventaire des personnages
CREATE TABLE IF NOT EXISTS inventory (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id  INTEGER NOT NULL,
    name          TEXT    NOT NULL,
    type_id       INTEGER NOT NULL,
    quantity      INTEGER NOT NULL DEFAULT 1,
    description   TEXT,
    added_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(character_id) REFERENCES characters(id) ON DELETE CASCADE,
    FOREIGN KEY(type_id)      REFERENCES item_types(id) ON DELETE CASCADE
);

-- 6) Quêtes
CREATE TABLE IF NOT EXISTS quests (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    title              TEXT    NOT NULL,
    description        TEXT,
    level_required     INTEGER NOT NULL DEFAULT 1,
    experience_reward  INTEGER NOT NULL DEFAULT 50,
    gold_reward        INTEGER NOT NULL DEFAULT 10
);

-- 7) Monstres
CREATE TABLE IF NOT EXISTS monsters (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name     TEXT    NOT NULL,
    health   INTEGER NOT NULL DEFAULT 50,
    attack   INTEGER NOT NULL DEFAULT 8,
    defense  INTEGER NOT NULL DEFAULT 3,
    level    INTEGER NOT NULL DEFAULT 1
);

-- 8) Récompenses de quêtes (objets)
CREATE TABLE IF NOT EXISTS quest_rewards (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    quest_id   INTEGER NOT NULL,
    name       TEXT    NOT NULL,
    type_id    INTEGER NOT NULL,
    quantity   INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY(quest_id) REFERENCES quests(id) ON DELETE CASCADE,
    FOREIGN KEY(type_id)  REFERENCES item_types(id) ON DELETE CASCADE
);

-- 9) Monstres associés aux quêtes
CREATE TABLE IF NOT EXISTS quest_monsters (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    quest_id    INTEGER NOT NULL,
    monster_id  INTEGER NOT NULL,
    quantity    INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY(quest_id)   REFERENCES quests(id)    ON DELETE CASCADE,
    FOREIGN KEY(monster_id) REFERENCES monsters(id)  ON DELETE CASCADE
);

-- 10) Quêtes complétées
CREATE TABLE IF NOT EXISTS completed_quests (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id  INTEGER NOT NULL,
    quest_id      INTEGER NOT NULL,
    completed_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(character_id) REFERENCES characters(id) ON DELETE CASCADE,
    FOREIGN KEY(quest_id)     REFERENCES quests(id)      ON DELETE CASCADE,
    UNIQUE(character_id, quest_id)
);

-- 11) Équipements (objets équipés)
CREATE TABLE IF NOT EXISTS equipped_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER NOT NULL,
    inventory_id INTEGER NOT NULL,
    slot         TEXT    NOT NULL,  -- e.g. 'weapon', 'armor', 'accessory'
    equipped_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(character_id) REFERENCES characters(id) ON DELETE CASCADE,
    FOREIGN KEY(inventory_id) REFERENCES inventory(id) ON DELETE CASCADE,
    UNIQUE(character_id, slot)
);

-- 12) Statistiques des joueurs
CREATE TABLE IF NOT EXISTS player_stats (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id      INTEGER NOT NULL,
    battles_won       INTEGER NOT NULL DEFAULT 0,
    battles_lost      INTEGER NOT NULL DEFAULT 0,
    monsters_defeated INTEGER NOT NULL DEFAULT 0,
    quests_completed  INTEGER NOT NULL DEFAULT 0,
    items_collected   INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(character_id) REFERENCES characters(id) ON DELETE CASCADE,
    UNIQUE(character_id)
);

-- 13) Sessions de jeu
CREATE TABLE IF NOT EXISTS game_sessions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL,
    character_id     INTEGER,
    started_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at         TIMESTAMP,
    duration_seconds INTEGER,
    FOREIGN KEY(user_id)      REFERENCES users(user_id)  ON DELETE CASCADE,
    FOREIGN KEY(character_id) REFERENCES characters(id) ON DELETE SET NULL
);

-- ===== Données initiales =====

-- Quêtes
INSERT OR IGNORE INTO quests (id, title, description, level_required, experience_reward, gold_reward) VALUES
    (1, 'Forêt mystérieuse', 'Explorez la forêt mystérieuse et débarrassez-la de ses monstres.', 1,  50,  20),
    (2, 'Caverne des trolls','Nettoyez la caverne infestée de trolls.',                 2, 100,  50),
    (3, 'Nid du dragon',     'Affrontez un dragon et récupérez son trésor.',            5, 500, 200);

-- Monstres
INSERT OR IGNORE INTO monsters (id, name, health, attack, defense, level) VALUES
    (1, 'Gobelin',  40, 6,  2, 1),
    (2, 'Loup',     50, 8,  3, 1),
    (3, 'Troll',    80,12, 5, 2),
    (4, 'Ogre',    100,15, 7, 3),
    (5, 'Dragon',  200,25,15, 5);

-- Association monstres→quêtes
INSERT OR IGNORE INTO quest_monsters (quest_id, monster_id, quantity) VALUES
    (1, 1, 3),  -- 3 Gobelins
    (1, 2, 2),  -- 2 Loups
    (2, 3, 2),  -- 2 Trolls
    (2, 4, 1),  -- 1 Ogre
    (3, 5, 1);  -- 1 Dragon

-- Récompenses de quêtes
INSERT OR IGNORE INTO quest_rewards (quest_id, name, type_id, quantity) VALUES
    (1, 'Potion de soin',    3, 2),
    (1, 'Dague de gobelin',  1, 1),
    (2, 'Potion de force',   3, 1),
    (2, 'Armure de troll',   2, 1),
    (3, 'Épée de dragon',    1, 1),
    (3, 'Écaille de dragon', 4, 5);
