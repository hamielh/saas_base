from flask import Blueprint, request, jsonify
from models import db, User, UserRole

api_user_bp = Blueprint('api_user', __name__, url_prefix='/api')

@api_user_bp.route('/create-user', methods=['POST'])
def create_user():
    """Criar usuário via API"""
    try:
        data = request.get_json() if request.is_json else request.form
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        role = data.get('role', 'user')
        
        if not all([email, password, first_name, last_name]):
            return jsonify({
                'error': 'Email, password, first_name e last_name são obrigatórios'
            }), 400
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({
                'error': f'Usuário com email {email} já existe',
                'user_id': existing_user.id
            }), 409
        
        # Converter role para enum
        role_map = {
            'super_admin': UserRole.SUPER_ADMIN,
            'administrador': UserRole.ADMINISTRADOR,
            'user': UserRole.USER
        }
        user_role = role_map.get(role.lower(), UserRole.USER)
        
        user = User(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=user_role
        )
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Usuário criado com sucesso!',
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@api_user_bp.route('/create-test-user', methods=['GET'])
def create_test_user():
    """Criar usuário de teste para desenvolvimento"""
    try:
        existing_user = User.query.filter_by(email='hamielhenrique29@gmail.com').first()
        if existing_user:
            return jsonify({
                'message': 'Usuário de teste já existe!',
                'user': existing_user.to_dict()
            }), 200
        
        user = User(
            email='hamielhenrique29@gmail.com',
            password='123456',
            first_name='Hamiel',
            last_name='Henrique',
            role=UserRole.SUPER_ADMIN
        )
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Usuário de teste criado!',
            'user': user.to_dict(),
            'credentials': {
                'email': 'hamielhenrique29@gmail.com',
                'password': '123456'
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro: {str(e)}'}), 500