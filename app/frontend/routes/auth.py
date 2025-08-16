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
            
            # NOVO: Definir account inicial na session
            accounts = user.get_accounts()
            if accounts:
                # Se tem accounts, definir a primeira como padrão
                first_account = accounts[0]
                session['current_account_id'] = first_account.id
                session['current_account_name'] = first_account.name
            elif user.is_super_admin():
                # Super admin inicia em modo global
                session.pop('current_account_id', None)
                session.pop('current_account_name', None)
            
            flash(f'Bem-vindo, {user.get_full_name()}!', 'success')
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('main.dashboard'))
        else:
            flash('Email ou senha inválidos!', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Rota de logout do sistema"""
    user_name = current_user.get_full_name()
    
    # Limpar session
    session.pop('current_account_id', None)
    session.pop('current_account_name', None)
    
    logout_user()
    flash(f'Até logo, {user_name}!', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/user/switch-account', methods=['POST'])
@login_required
def switch_account():
    """Permite trocar de account"""
    try:
        data = request.get_json()
        account_id = data.get('account_id')  # Pode ser None para modo global
        
        # Se account_id é None, entrar em modo super admin global
        if account_id is None:
            if current_user.is_super_admin():
                session.pop('current_account_id', None)
                session.pop('current_account_name', None)
                return jsonify({
                    'success': True, 
                    'message': 'Modo Super Admin Global ativado',
                    'account_id': None,
                    'account_name': 'Super Admin Global'
                })
            else:
                return jsonify({'success': False, 'error': 'Apenas super admin pode usar modo global'})
        
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
        current_account = current_user.get_current_account()
        
        if current_user.is_super_admin():
            if current_account:
                return jsonify({
                    'account_id': current_account.id,
                    'account_name': current_account.name,
                    'is_super_admin': True,
                    'mode': 'account_context'
                })
            else:
                return jsonify({
                    'account_id': None,
                    'account_name': 'Super Admin Global',
                    'is_super_admin': True,
                    'mode': 'global'
                })
        else:
            if current_account:
                return jsonify({
                    'account_id': current_account.id,
                    'account_name': current_account.name,
                    'is_super_admin': False,
                    'mode': 'account_context',
                    'role_in_account': current_user.get_role_in_account(current_account)
                })
            else:
                return jsonify({
                    'account_id': None,
                    'account_name': 'Sem account',
                    'is_super_admin': False,
                    'mode': 'no_account'
                })
                
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/user/accounts', methods=['GET'])
@login_required
def get_user_accounts():
    """Retorna todas as accounts do usuário"""
    try:
        accounts = current_user.get_accounts()
        current_account = current_user.get_current_account()
        
        accounts_data = []
        for account in accounts:
            accounts_data.append({
                'id': account.id,
                'name': account.name,
                'role': current_user.get_role_in_account(account) if not current_user.is_super_admin() else 'super_admin',
                'user_count': account.get_user_count(),
                'is_current': current_account and account.id == current_account.id
            })
        
        return jsonify({
            'accounts': accounts_data,
            'current_account_id': current_account.id if current_account else None,
            'is_super_admin': current_user.is_super_admin(),
            'total_accounts': len(accounts_data)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500