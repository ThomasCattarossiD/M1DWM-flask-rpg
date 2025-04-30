from flask import Blueprint, flash, redirect, render_template, request, url_for, jsonify, current_app
from flask_login import current_user, login_required
from flask_cors import cross_origin

from init_db import get_db_connection
from models.game import Character, Item, Mage, Monster, Race, Warrior, Tableau

import json

game_bp = Blueprint('game', __name__)

# Fonction utilitaire pour répondre à la fois en JSON et HTML
def respond(is_json, json_data=None, html_template=None, html_data=None, html_redirect=None, flash_message=None, flash_category=None, status=200):
    if flash_message and flash_category:
        flash(flash_message, flash_category)
    
    if is_json:
        return jsonify(json_data), status
    
    if html_redirect:
        return redirect(html_redirect)
    
    return render_template(html_template, **html_data)

@game_bp.route('/create_character', methods=['GET', 'POST', 'OPTIONS'])
@cross_origin()
@login_required
def create_character():
    if request.method == 'OPTIONS':
        return '', 200
    
    is_json = request.is_json
    
    if request.method == 'POST':
        try:
            # Récupération des données
            if is_json:
                data = request.get_json()
                name = data.get('name')
                race = data.get('race')
                character_class = data.get('class')
            else:
                name = request.form.get('name')
                race = request.form.get('race')
                character_class = request.form.get('class')
            
            # Validation
            if not name or not race or not character_class:
                return respond(
                    is_json,
                    json_data={"success": False, "message": "Tous les champs sont obligatoires"},
                    html_template='game/create_character.html',
                    flash_message="Tous les champs sont obligatoires",
                    flash_category="danger",
                    status=400
                )
            
            # Création du personnage
            try:
                race_enum = Race[race.upper()]
            except KeyError:
                return respond(
                    is_json,
                    json_data={"success": False, "message": f"Race invalide: {race}"},
                    html_template='game/create_character.html',
                    flash_message=f"Race invalide: {race}",
                    flash_category="danger",
                    status=400
                )
            
            if character_class == 'warrior':
                character = Warrior(name=name, race=race_enum)
            elif character_class == 'mage':
                character = Mage(name=name, race=race_enum)
            else:
                return respond(
                    is_json,
                    json_data={"success": False, "message": f"Classe invalide: {character_class}"},
                    html_template='game/create_character.html',
                    flash_message=f"Classe invalide: {character_class}",
                    flash_category="danger",
                    status=400
                )
            
            # Sauvegarde en BDD
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT INTO characters (name, race, class, health, attack, defense, user_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (character.name, character.race.name, character.type,
                      character.health, character.attack, character.defense,
                      current_user.id))
                
                character_id = cursor.lastrowid
                character.id = character_id
                
                cursor.execute('''
                    UPDATE user 
                    SET active_character_id = ? 
                    WHERE user_id = ?
                ''', (character_id, current_user.id))
                
                conn.commit()
                
                return respond(
                    is_json,
                    json_data={"success": True, "message": "Personnage créé avec succès", "character_id": character_id},
                    html_redirect=url_for('game.character_profile'),
                    flash_message="Personnage créé avec succès",
                    flash_category="success"
                )
            except Exception as e:
                conn.rollback()
                current_app.logger.error(f"Database error: {str(e)}")
                
                return respond(
                    is_json,
                    json_data={"success": False, "message": f"Erreur de base de données: {str(e)}"},
                    html_template='game/create_character.html',
                    flash_message=f"Erreur de base de données: {str(e)}",
                    flash_category="danger",
                    status=500
                )
            finally:
                cursor.close()
                conn.close()
                
        except Exception as e:
            current_app.logger.error(f"Error in create_character: {str(e)}")
            
            return respond(
                is_json,
                json_data={"success": False, "message": f"Erreur serveur: {str(e)}"},
                html_template='game/create_character.html',
                flash_message=f"Erreur serveur: {str(e)}",
                flash_category="danger",
                status=500
            )
    
    # GET request
    return render_template('game/create_character.html')

# Le reste de vos routes game_bp avec le même modèle de gestion CORS et réponses