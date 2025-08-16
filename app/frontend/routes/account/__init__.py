from flask import Blueprint, request, redirect, url_for, flash, abort, g
from flask_login import login_required, current_user
from functools import wraps
from models import Account, AccountStatus

# Blueprint principal para rotas baseadas em account
account_bp = Blueprint('account', __name__, url_prefix='/account')

def account_required(f):
    """
    Middleware: Verifica se usuário tem acesso ao account_id da URL
    """
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        # Pegar account_id da URL
        account_id = kwargs.get('account_id')
        
        if not account_id:
            flash('Account não especificada!', 'error')
            return redirect(url_for('main.select_account'))
        
        # Verificar se account existe
        account = Account.query.get(account_id)
        if not account:
            flash(f'Account {account_id} não encontrada!', 'error')
            return redirect(url_for('main.select_account'))
        
        # Verificar se account está ativa
        if account.status != AccountStatus.ACTIVE:
            flash(f'Account {account.name} está inativa!', 'error')
            return redirect(url_for('main.select_account'))
        
        # Verificar se usuário tem acesso
        if not current_user.can_access_account(account_id):
            flash(f'Você não tem acesso à account {account.name}!', 'error')
            
            # Redirecionar para primeira account do usuário
            default_account = current_user.get_default_account()
            if default_account:
                return redirect(url_for('account.dashboard', account_id=default_account.id))
            else:
                return redirect(url_for('main.no_access'))
        
        # Definir account atual na session e no contexto global
        current_user.set_current_account(account_id)
        g.current_account = account
        
        return f(*args, **kwargs)
    
    return decorated_function

def admin_required(f):
    """
    Middleware: Requer que usuário seja admin da account atual
    """
    @wraps(f)
    @account_required
    def decorated_function(*args, **kwargs):
        account = g.current_account
        
        if not current_user.is_admin_of_account(account):
            flash(f'Você não tem privilégios de administrador na account {account.name}!', 'error')
            return redirect(url_for('account.dashboard', account_id=account.id))
        
        return f(*args, **kwargs)
    
    return decorated_function

def owner_required(f):
    """
    Middleware: Requer que usuário seja owner da account atual
    """
    @wraps(f)
    @account_required
    def decorated_function(*args, **kwargs):
        account = g.current_account
        
        if not current_user.is_owner_of_account(account) and not current_user.is_super_admin():
            flash(f'Você não é o proprietário da account {account.name}!', 'error')
            return redirect(url_for('account.dashboard', account_id=account.id))
        
        return f(*args, **kwargs)
    
    return decorated_function

# =============================================================================
# ROTAS PRINCIPAIS DA ACCOUNT
# =============================================================================

@account_bp.route('/<int:account_id>/dashboard')
@account_required
def dashboard(account_id):
    """Dashboard principal da account"""
    account = g.current_account
    
    # Estatísticas básicas da account
    stats = {
        'total_users': account.users.count(),
        'admin_users': len(account.get_admins()),
        'regular_users': len(account.get_regular_users()),
        'account_status': account.status.value,
        'created_at': account.created_at,
        'owner': account.owner.get_full_name() if account.owner else 'N/A'
    }
    
    # Role do usuário atual nesta account
    user_role_in_account = current_user.get_role_in_account(account)
    is_admin = current_user.is_admin_of_account(account)
    is_owner = current_user.is_owner_of_account(account)
    
    return render_template('account/dashboard.html',
                         account=account,
                         stats=stats,
                         user_role=user_role_in_account,
                         is_admin=is_admin,
                         is_owner=is_owner)

@account_bp.route('/<int:account_id>/settings')
@admin_required
def settings(account_id):
    """Configurações da account (só admins)"""
    account = g.current_account
    
    return render_template('account/settings.html', account=account)

@account_bp.route('/<int:account_id>/users')
@admin_required
def users(account_id):
    """Gestão de usuários da account (só admins)"""
    account = g.current_account
    users = account.users.all()
    
    return render_template('account/users.html', 
                         account=account, 
                         users=users)

@account_bp.route('/<int:account_id>/reports')
@account_required
def reports(account_id):
    """Relatórios da account"""
    account = g.current_account
    
    return render_template('account/reports.html', account=account)

# =============================================================================
# CONTEXT PROCESSORS E HELPERS
# =============================================================================

@account_bp.context_processor
def inject_account_context():
    """Injeta contexto da account em todos os templates"""
    return {
        'current_account': getattr(g, 'current_account', None),
        'user_accessible_accounts': current_user.get_accessible_accounts() if current_user.is_authenticated else [],
        'is_account_admin': current_user.is_admin_of_account(getattr(g, 'current_account', None)) if current_user.is_authenticated and hasattr(g, 'current_account') else False,
        'is_account_owner': current_user.is_owner_of_account(getattr(g, 'current_account', None)) if current_user.is_authenticated and hasattr(g, 'current_account') else False
    }

# =============================================================================
# TEMPLATE FILTERS
# =============================================================================

@account_bp.app_template_filter('account_url')
def account_url_filter(endpoint, account_id=None, **values):
    """
    Template filter para gerar URLs com account_id
    Uso: {{ 'account.dashboard'|account_url(account_id=1) }}
    """
    if account_id is None and hasattr(g, 'current_account'):
        account_id = g.current_account.id
    
    if account_id:
        values['account_id'] = account_id
    
    from flask import url_for
    return url_for(endpoint, **values)

# Import necessário para templates
from flask import render_template

# Registrar sub-blueprints se houver
# from .reports import reports_bp
# account_bp.register_blueprint(reports_bp)