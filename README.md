# Gestion d'Inventaire avec Authentification

## Description

Ce projet est une application web développée avec **Flask**, **SQLite** et **Tailwind CSS**. Il permet aux utilisateurs de créer un compte, de se connecter, de gérer leur inventaire personnel, d'ajouter, modifier, consommer et supprimer des items.

## Fonctionnalités

- Système d'authentification avec inscription, connexion et déconnexion.
- Chaque utilisateur possède son propre inventaire.
- Gestion des items d'inventaire (ajouter, modifier, consommer, supprimer).
- Interface utilisateur moderne utilisant **Tailwind CSS**.

## Prérequis

Avant de commencer, assurez-vous d'avoir installé les logiciels suivants :

- Python 3.7+
- `pip` (gestionnaire de paquets Python)
- `virtualenv` (facultatif mais recommandé)

## Installation

1. **Cloner le dépôt :**

   ```bash
   git clone https://github.com/votre-utilisateur/gestion-inventaire.git
   cd gestion-inventaire
   ```

2. **Créer un environnement virtuel (recommandé) :**

   ```bash
    python -m venv .venv
   source .venv/bin/activate  # Sur Windows : .venv\Scripts\activate
   ```

3. **Installer les dépendances :**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configurer les variables d'environnement :**

   Créez un fichier `.env` à la racine du projet avec le contenu suivant :

   ```plaintext
   DATABASE_PATH=gestion_inventaire.db
   SECRET_KEY = "votre_clé_secrète"
   ```

   Pour générer votre clé secrète, vous pouvez utiliser la commande suivante :

   ```bash
   openssl rand -hex 32
   ```

5. **Initialiser la base de données :**
   ```bash
    python init_db.py
   ```

## Utilisation

1. **Lancer l'application :**

   ```bash
   python app.py
   ```

2. **Accéder à l'application :**

Ouvrez votre navigateur et accédez à l'URL suivante :

    http://127.0.0.1:5000

3. **Fonctionnalités disponibles :**
   - Inscrivez-vous pour créer un compte.
   - Connectez-vous pour accéder à votre inventaire.
   - Gérez vos items d'inventaire :
     - Ajouter un nouvel item.
     - Modifier les détails d'un item.
     - Consommer un item.
     - Supprimer un item.

## Structure du Projet

```bash
      gestion-inventaire/
      ├── app.py              # Fichier principal de l'application Flask
      ├── init_db.py          # Script pour initialiser la base de données SQLite
      ├── templates/
      │   ├── home.html       # Page d'accueil après connexion
      │   ├── login.html      # Page de connexion
      │   ├── register.html   # Page d'inscription
      │   ├── inventory.html  # Page d'affichage de l'inventaire
      │   └── edit_item.html  # Page pour ajouter/modifier un item
      ├── .env                # Variables d'environnement
      ├── requirements.txt    # Liste des dépendances Python
      └── README.md           # Documentation du projet
```

## Modèle de la Base de Données

La base de données contient les tables suivantes :

```js
    user
        user_id (INTEGER, clé primaire)
        user_login (TEXT)
        user_password (TEXT)
        user_mail (TEXT)
        user_date_new (DATETIME)
        user_date_login (DATETIME)

    item_types
        id (INTEGER, clé primaire)
        type_name (TEXT)

    inventory
        id (INTEGER, clé primaire)
        user_id (INTEGER, clé étrangère vers user)
        name (TEXT)
        type_id (INTEGER, clé étrangère vers item_types)
        quantity (INTEGER)
```

## Dépendances

Installez-les avec la commande suivante :

```bash
pip install -r requirements.txt
```
# M1-rpg
