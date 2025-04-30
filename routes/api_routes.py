from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user, login_required
from flask_cors import cross_origin
import json

from init_db import get_db_connection
from models.game import Character, Monster

api_bp = Blueprint('api', __name__)

@api_bp.route('/characters', methods=['GET', 'OPTIONS'])
@cross_origin()
@login_required
def get_characters():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        characters = Character.get_all_by_user(current_user.id)
        characters_data = []
        
        for character in characters:
            characters_data.append({
                'id': character.id,
                'name': character.name,
                'race': character.race.name,
                'class': character.type,
                'health': character.health,
                'attack': character.attack,
                'defense': character.defense,
                'level': character.level,
                'isActive': character.id == current_user.active_character_id
            })
        
        return jsonify({
            'success': True,
            'characters': characters_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting characters: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Erreur serveur: {str(e)}"
        }), 500

@api_bp.route('/select_character/<int:character_id>', methods=['POST', 'OPTIONS'])
@cross_origin()
@login_required
def select_character(character_id):
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Vérifier que le personnage appartient bien à l'utilisateur
        cursor.execute('''
            SELECT * FROM characters 
            WHERE id = ? AND user_id = ?
        ''', (character_id, current_user.id))
        
        character = cursor.fetchone()
        
        if character:
            cursor.execute('''
                UPDATE user 
                SET active_character_id = ? 
                WHERE user_id = ?
            ''', (character_id, current_user.id))
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Personnage sélectionné avec succès',
                'character': {
                    'id': character['id'],
                    'name': character['name']
                }
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Personnage non trouvé'
            }), 404
            
    except Exception as e:
        current_app.logger.error(f"Error selecting character: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Erreur serveur: {str(e)}"
        }), 500
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@api_bp.route('/fight', methods=['POST', 'OPTIONS'])
@cross_origin()
@login_required
def fight():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        player1_id = int(data.get('player1'))
        player2_id = int(data.get('player2'))
        
        # Get all characters for this user
        characters = Character.get_all_by_user(current_user.id)
        player1 = next((c for c in characters if c.id == player1_id), None)
        player2 = next((c for c in characters if c.id == player2_id), None)
        
        if not player1 or not player2:
            return jsonify({
                'success': False,
                'message': 'Personnages invalides'
            }), 400
        
        # Fonction fight_logic du module game
        result_json = fight_logic(player1, player2)
        result = json.loads(result_json)
        
        return jsonify({
            'success': True,
            'fight_result': result
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error in fight: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Erreur serveur: {str(e)}"
        }), 500

@api_bp.route('/quest/<int:quest_id>', methods=['POST', 'OPTIONS'])
@cross_origin()
@login_required
def quest(quest_id):
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        if not current_user.active_character_id:
            return jsonify({
                'success': False,
                'message': "Veuillez d'abord sélectionner un personnage"
            }), 400
            
        # Get the active character
        character = Character.get_by_id(current_user.active_character_id)
        
        if not character:
            return jsonify({
                'success': False,
                'message': "Personnage actif non trouvé"
            }), 404
            
        # Get the monster for this quest
        opponent = get_opponent_for_quest(quest_id)
        
        if not opponent:
            return jsonify({
                'success': False,
                'message': f"Quête {quest_id} non trouvée"
            }), 404
            
        # Run the fight
        result_json = fight_hero_vs_monster(character, opponent)
        result = json.loads(result_json)
        
        return jsonify({
            'success': True,
            'quest_id': quest_id,
            'quest_result': result
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error in quest: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Erreur serveur: {str(e)}"
        }), 500

# Fonctions utilitaires modifiées pour fonctionner avec la nouvelle structure
def fight_logic(player1, player2):
    # Même contenu que votre fonction fight_logic existante
    # ...

def get_opponent_for_quest(quest_id):
    # Même contenu que votre fonction get_opponent_for_quest existante
    # ...

def fight_hero_vs_monster(hero, monster):
    # Même contenu que votre fonction fight_hero_vs_monster existante
    # ...
