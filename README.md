# Backend Flask pour Jeu de Rôle

Ce projet est un backend Flask qui fournit une API REST pour une application de jeu de rôle. Il gère l'authentification, les personnages, les quêtes, les combats, et les inventaires.

## Table des matières

- [Prérequis](#prérequis)
- [Installation](#installation)
- [Configuration](#configuration)
- [Démarrage](#démarrage)
- [Structure du projet](#structure-du-projet)
- [API](#api)
  - [Authentification](#authentification)
  - [Utilisateurs](#utilisateurs)
  - [Personnages](#personnages)
  - [Quêtes](#quêtes)
  - [Inventaire](#inventaire)
  - [Combats](#combats)
  - [Jeu de plateau](#jeu-de-plateau)
- [Tests](#tests)
- [Déploiement](#déploiement)
- [Contribution](#contribution)
- [Licence](#licence)

## Prérequis

- Python 3.8+
- pip
- SQLite3
- Virtualenv (recommandé)

## Installation

1. Clonez le dépôt :

```bash
git clone https://github.com/votre-nom/jeu-de-role-backend.git
cd jeu-de-role-backend
```

2. Créez et activez un environnement virtuel (recommandé) :

```bash
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
```

3. Installez les dépendances :

```bash
pip install -r requirements.txt
```

4. Créez le fichier `.env` à partir du modèle :

```bash
cp .env.example .env
```

5. Initialisez la base de données :

```bash
python init_db.py
```

## Configuration

Modifiez le fichier `.env` pour personnaliser votre configuration :

```
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=votre_clé_secrète
DATABASE_PATH=database.db
```

## Démarrage

Pour lancer le serveur de développement :

```bash
flask run
```

Le serveur sera accessible à l'adresse http://127.0.0.1:5000/

Pour une utilisation en production, utilisez un serveur WSGI comme Gunicorn :

```bash
gunicorn "app:app"
```

## Structure du projet

- `app.py` : Point d'entrée de l'application Flask
- `init_db.py` : Script d'initialisation de la base de données
- `models/` : Modèles de données (User, Character, Item, etc.)
- `routes/` : Routes API regroupées par fonctionnalité
- `templates/` : Templates HTML (pour les vues rendues par le serveur)
- `static/` : Fichiers statiques (CSS, JS, images)

## API

### Authentification

| Méthode | Endpoint | Description | Paramètres | Réponse |
|---------|----------|-------------|------------|---------|
| POST | `/api/auth/login` | Se connecter | `email`, `password` | `{"success": true, "user": {...}}` |
| POST | `/api/auth/register` | Créer un compte | `email`, `password`, `username` | `{"success": true, "user": {...}}` |
| POST | `/api/auth/logout` | Se déconnecter | - | `{"success": true}` |

### Utilisateurs

| Méthode | Endpoint | Description | Paramètres | Réponse |
|---------|----------|-------------|------------|---------|
| GET | `/api/user/current` | Obtenir l'utilisateur connecté | - | `{"success": true, "user": {...}}` |

### Personnages

| Méthode | Endpoint | Description | Paramètres | Réponse |
|---------|----------|-------------|------------|---------|
| GET | `/api/characters` | Liste des personnages de l'utilisateur | - | `{"success": true, "characters": [...]}` |
| GET | `/api/characters/{id}` | Détails d'un personnage | - | `{"success": true, "character": {...}}` |
| POST | `/api/characters` | Créer un personnage | `name`, `race`, `class` | `{"success": true, "character": {...}}` |
| POST | `/api/characters/{id}/select` | Sélectionner comme personnage actif | - | `{"success": true}` |
| GET | `/api/characters/{id}/stats` | Statistiques d'un personnage | - | `{"success": true, "stats": {...}}` |

### Quêtes

| Méthode | Endpoint | Description | Paramètres | Réponse |
|---------|----------|-------------|------------|---------|
| GET | `/api/quests` | Liste des quêtes disponibles | - | `{"success": true, "quests": [...]}` |
| POST | `/api/quests/{id}/start` | Démarrer une quête | - | `{"success": true, "battle_result": {...}, "rewards": {...}}` |
| GET | `/api/characters/{id}/completed_quests` | Quêtes complétées par un personnage | - | `{"success": true, "quests": [...]}` |

### Inventaire

| Méthode | Endpoint | Description | Paramètres | Réponse |
|---------|----------|-------------|------------|---------|
| GET | `/api/inventory` | Inventaire du personnage actif | - | `{"success": true, "items": [...]}` |
| POST | `/api/inventory` | Ajouter un objet | `name`, `type_id`, `quantity`, `description` | `{"success": true, "item": {...}}` |
| PUT | `/api/inventory/{id}` | Modifier un objet | `name`, `type_id`, `quantity`, `description` | `{"success": true, "item": {...}}` |
| DELETE | `/api/inventory/{id}` | Supprimer un objet | - | `{"success": true}` |
| POST | `/api/inventory/{id}/use` | Utiliser un objet | - | `{"success": true, "effect": "..."}` |
| GET | `/api/items` | Types d'objets disponibles | - | `{"success": true, "item_types": [...]}` |

### Combats

| Méthode | Endpoint | Description | Paramètres | Réponse |
|---------|----------|-------------|------------|---------|
| POST | `/api/versus` | Combat PvP | `player1_id`, `player2_id` | `{"success": true, "battle_result": {...}}` |

### Jeu de plateau

| Méthode | Endpoint | Description | Paramètres | Réponse |
|---------|----------|-------------|------------|---------|
| POST | `/api/board_game/start` | Démarrer une partie | - | `{"success": true, "game": {...}}` |
| POST | `/api/board_game/move` | Effectuer un mouvement | `direction` | `{"success": true, "result": {...}, "new_position": {...}}` |

## Format des réponses

Toutes les réponses de l'API suivent le format suivant :

```json
{
  "success": true/false,
  "data": {...},  // Optionnel, présent en cas de succès
  "message": "..." // Optionnel, présent en cas d'erreur
}
```

## Codes d'état HTTP

- `200 OK` : Requête traitée avec succès
- `201 Created` : Ressource créée avec succès
- `400 Bad Request` : Erreur de validation des données
- `401 Unauthorized` : Authentification requise
- `403 Forbidden` : Accès non autorisé
- `404 Not Found` : Ressource non trouvée
- `500 Internal Server Error` : Erreur serveur

## CORS (Cross-Origin Resource Sharing)

L'API prend en charge CORS pour permettre les requêtes depuis d'autres domaines. Tous les endpoints répondent à la méthode `OPTIONS` pour les requêtes préliminaires (preflight).

## Authentification

L'API utilise l'authentification par session avec Flask-Login. Les cookies de session doivent être envoyés avec chaque requête. Lors de l'utilisation depuis une application frontend, assurez-vous que l'option `withCredentials: true` est activée dans vos requêtes AJAX/Fetch.

## Tests

Pour exécuter les tests :

```bash
pytest
```

## Déploiement

### Déploiement sur Heroku

1. Créez une application Heroku :

```bash
heroku create mon-app-backend
```

2. Ajoutez les buildpacks nécessaires :

```bash
heroku buildpacks:add heroku/python
```

3. Configurez les variables d'environnement :

```bash
heroku config:set SECRET_KEY=ma_cle_secrete
heroku config:set FLASK_ENV=production
```

4. Déployez l'application :

```bash
git push heroku main
```

## Contribution

1. Forkez le projet
2. Créez une branche pour votre fonctionnalité (`git checkout -b feature/amazing-feature`)
3. Committez vos changements (`git commit -m 'Add some amazing feature'`)
4. Poussez votre branche (`git push origin feature/amazing-feature`)
5. Ouvrez une Pull Request

## Licence

Distribué sous la licence MIT. Voir `LICENSE` pour plus d'informations.