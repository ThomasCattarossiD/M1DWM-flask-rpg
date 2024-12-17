from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from init_db import get_db_connection
from models.game import Character, Item, Mage, Monster, Race, Warrior
from models.user import User

game_bp = Blueprint('game', __name__)

@game_bp.route('/create_character', methods=['GET', 'POST'])
@login_required
def create_character():
    if request.method == 'POST':
        name = request.form.get('name')
        race = request.form.get('race')
        character_class = request.form.get('class')
        
        # Créer l'instance temporaire du personnage (sans ID)
        if character_class == 'warrior':
            character = Warrior(name=name, race=Race[race.upper()])
        elif character_class == 'mage':
            character = Mage(name=name, race=Race[race.upper()])
        
        # Sauvegarder dans la base de données
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO characters (name, race, class, health, attack, defense, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (character.name, character.race.name, character.type, 
              character.health, character.attack, character.defense,
              current_user.id))
        
        character_id = cursor.lastrowid
        # Mettre à jour l'ID du personnage
        character.id = character_id
        
        # Mettre à jour l'active_character_id de l'utilisateur
        cursor.execute('''
            UPDATE user 
            SET active_character_id = ? 
            WHERE user_id = ?
        ''', (character_id, current_user.id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Personnage créé avec succès!', 'success')
        return redirect(url_for('game.character_profile'))
        
    return render_template('game/create_character.html')

@game_bp.route('/select_character/<int:character_id>', methods=['POST'])
@login_required
def select_character(character_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Vérifier que le personnage appartient bien à l'utilisateur
    cursor.execute('''
        SELECT * FROM characters 
        WHERE id = ? AND user_id = ?
    ''', (character_id, current_user.id))
    
    if cursor.fetchone():
        cursor.execute('''
            UPDATE user 
            SET active_character_id = ? 
            WHERE user_id = ?
        ''', (character_id, current_user.id))
        conn.commit()
        flash('Personnage sélectionné avec succès!', 'success')
    else:
        flash('Personnage non trouvé.', 'error')
    
    cursor.close()
    conn.close()
    return redirect(url_for('game.character_list'))

@game_bp.route('/versus')
@login_required
def versus_mode():
    characters = Character.get_all_by_user(current_user.id)
    return render_template('game/versus.html', characters=characters)

@game_bp.route('/quests')
@login_required
def quest_mode():
    if not current_user.active_character_id:
        flash('Veuillez d\'abord créer ou sélectionner un personnage.', 'warning')
        return redirect(url_for('game.create_character'))
    
    character = Character.get_by_id(current_user.active_character_id)
    return render_template('game/quests.html', character=character)

@game_bp.route('/board_game')
@login_required
def board_game():
    if not current_user.active_character_id:
        flash('Veuillez d\'abord créer ou sélectionner un personnage.', 'warning')
        return redirect(url_for('game.create_character'))
    
    character = Character.get_by_id(current_user.active_character_id)
    return render_template('game/board_game.html', character=character)

@game_bp.route('/character_profile')
@login_required
def character_profile():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM characters WHERE user_id = ? ORDER BY id DESC LIMIT 1', (current_user.id,))
    character_data = cursor.fetchone()
    cursor.close()
    conn.close()

    if character_data:
        character = Character(
            id=character_data['id'],
            name=character_data['name'],
            race=Race[character_data['race']],
            character_type=character_data['class'],
            health=character_data['health'],
            attack=character_data['attack'],
            defense=character_data['defense'],
            level=character_data['level']
        )
        return render_template('game/character_profile.html', character=character)
    
    flash('Aucun personnage trouvé.', 'warning')
    return redirect(url_for('game.create_character')) 

@game_bp.route('/characters')
@login_required
def character_list():
    characters = Character.get_all_by_user(current_user.id)
    return render_template('game/character_list.html', characters=characters) 