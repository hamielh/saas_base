from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, UserRole

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():

    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))
        
        if not email or not password:
            flash('Email e senha são obrigatórios!', 'error')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            user.update_last_login()
            
            flash(f'Bem-vindo, {user.get_full_name()}!', 'success')
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('main.dashboard'))
        else:
            flash('Email ou senha inválidos!', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    """Rota de logout do sistema"""
    user_name = current_user.get_full_name()
    logout_user()
    flash(f'Até logo, {user_name}!', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/user/switch-account', methods=['POST'])
@login_required
def switch_account():
    """Permite trocar de account (principalmente para super admin)"""
    try:
        data = request.get_json()
        account_id = data.get('account_id', type=int)
        
        if not account_id:
            return jsonify({'success': False, 'error': 'ID da account é obrigatório'})
        
        # Verificar se o usuário pode acessar esta account
        if not current_user.can_access_account(account_id):
            return jsonify({'success': False, 'error': 'Acesso negado a esta account'})
        
        # Buscar a account
        from models import Account
        account = Account.query.get(account_id)
        if not account:
            return jsonify({'success': False, 'error': 'Account não encontrada'})
        
        # Salvar na session
        session['current_account_id'] = account_id
        session['current_account_name'] = account.name
        
        return jsonify({
            'success': True, 
            'message': f'Trocado para account: {account.name}',
            'account_id': account_id,
            'account_name': account.name
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@auth_bp.route('/user/current-account', methods=['GET'])
@login_required
def get_current_account():
    """Retorna a account atual do usuário"""
    try:
        if current_user.is_super_admin():
            # Para super admin, usar da session ou padrão
            account_id = session.get('current_account_id')
            if account_id:
                from models import Account
                account = Account.query.get(account_id)
                if account:
                    return jsonify({
                        'account_id': account.id,
                        'account_name': account.name,
                        'is_super_admin': True
                    })
            
            return jsonify({
                'account_id': None,
                'account_name': 'Super Admin',
                'is_super_admin': True
            })
        else:
            # Usuário normal
            if current_user.account:
                return jsonify({
                    'account_id': current_user.account.id,
                    'account_name': current_user.account.name,
                    'is_super_admin': False
                })
            else:
                return jsonify({
                    'account_id': None,
                    'account_name': 'Sem account',
                    'is_super_admin': False
                })
                
    except Exception as e:
        return jsonify({'error': str(e)}), 500