from flask import Blueprint, abort, flash, redirect, url_for
from flask_login import login_required, current_user
from functools import wraps
from models import UserRole

# Criar blueprint principal do super admin
super_admin_bp = Blueprint('super_admin', __name__, url_prefix='/super-admin')

def super_admin_required(f):
    """
    Middleware: Só permite acesso para super admin
    """
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Você precisa estar logado!', 'error')
            return redirect(url_for('auth.login'))
        
        if not current_user.is_super_admin():
            flash('Acesso negado! Área restrita para Super Admin.', 'error')
            return redirect(url_for('main.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

# Rota principal do painel super admin
@super_admin_bp.route('/')
@super_admin_required
def dashboard():
    """Dashboard do Super Admin"""
    from models import User, Account
    
    # Estatísticas básicas
    total_users = User.query.count()
    total_accounts = Account.query.count()
    super_admins = User.query.filter_by(role=UserRole.SUPER_ADMIN).count()
    admins = User.query.filter_by(role=UserRole.ADMINISTRADOR).count()
    
    stats = {
        'total_users': total_users,
        'total_accounts': total_accounts,
        'super_admins': super_admins,
        'admins': admins,
        'regular_users': total_users - super_admins - admins
    }
    
    return render_template('super_admin/dashboard.html', stats=stats)

# Importar outras rotas
from .accounts import accounts_bp
from .users import users_bp

# Registrar sub-blueprints
super_admin_bp.register_blueprint(accounts_bp)
super_admin_bp.register_blueprint(users_bp)

# Import necessário para template
from flask import render_template