from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db

api_settings_bp = Blueprint('api_settings', __name__, url_prefix='/api')

@api_settings_bp.route('/user/theme', methods=['GET'])
@login_required
def get_user_theme():
    """Retorna a preferência de tema do usuário"""
    try:
        theme = getattr(current_user, 'theme_preference', 'light')
        return jsonify({'theme': theme}), 200
    except Exception as e:
        return jsonify({'error': 'Erro ao buscar preferência de tema'}), 500

@api_settings_bp.route('/user/theme', methods=['POST'])
@login_required
def set_user_theme():
    """Define a preferência de tema do usuário"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        theme = data.get('theme', '').strip().lower()
        
        # Validar tema
        if theme not in ['light', 'dark', 'system']:
            return jsonify({'error': 'Tema inválido. Use: light, dark ou system'}), 400
        
        # Salvar preferência do usuário
        current_user.theme_preference = theme
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Tema atualizado com sucesso!',
            'theme': theme
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro ao salvar tema: {str(e)}'}), 500