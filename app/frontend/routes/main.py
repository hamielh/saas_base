from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Página inicial - redireciona baseado no status do usuário"""
    if current_user.is_authenticated:
        # Se usuário logado, redirecionar para dashboard da account padrão
        default_account = current_user.get_default_account()
        if default_account:
            return redirect(url_for('account.dashboard', account_id=default_account.id))
        else:
            return redirect(url_for('main.no_access'))
    else:
        # Se não logado, redirecionar para login
        return redirect(url_for('auth.login'))

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """
    Rota legada do dashboard - redireciona para nova estrutura
    Mantida para compatibilidade
    """
    default_account = current_user.get_default_account()
    if default_account:
        return redirect(url_for('account.dashboard', account_id=default_account.id))
    else:
        return redirect(url_for('main.no_access'))

@main_bp.route('/select-account')
@login_required
def select_account():
    """Página para selecionar account quando usuário tem múltiplas"""
    accessible_accounts = current_user.get_accessible_accounts()
    
    # Se só tem uma account, redirecionar direto
    if len(accessible_accounts) == 1:
        return redirect(url_for('account.dashboard', account_id=accessible_accounts[0].id))
    
    # Se não tem nenhuma account
    if len(accessible_accounts) == 0:
        return redirect(url_for('main.no_access'))
    
    return render_template('main/select_account.html', accounts=accessible_accounts)

@main_bp.route('/no-access')
@login_required
def no_access():
    """Página quando usuário não tem acesso a nenhuma account"""
    return render_template('main/no_access.html')

@main_bp.route('/switch-account/<int:account_id>')
@login_required
def switch_account(account_id):
    """Trocar de account via URL"""
    if current_user.can_access_account(account_id):
        current_user.set_current_account(account_id)
        flash(f'Account alterada com sucesso!', 'success')
        return redirect(url_for('account.dashboard', account_id=account_id))
    else:
        flash('Você não tem acesso a esta account!', 'error')
        default_account = current_user.get_default_account()
        if default_account:
            return redirect(url_for('account.dashboard', account_id=default_account.id))
        else:
            return redirect(url_for('main.no_access'))

# =============================================================================
# ROTAS DE INFORMAÇÕES GERAIS (SEM ACCOUNT ESPECÍFICA)
# =============================================================================

@main_bp.route('/profile')
@login_required
def profile():
    """Perfil do usuário (global, não específico de account)"""
    user_accounts = current_user.get_accessible_accounts()
    return render_template('main/profile.html', accounts=user_accounts)

@main_bp.route('/help')
@login_required
def help():
    """Página de ajuda"""
    return render_template('main/help.html')

@main_bp.route('/notifications')
@login_required
def notifications():
    """Notificações do usuário (global)"""
    return render_template('main/notifications.html')

# =============================================================================
# ROTAS DE DESENVOLVIMENTO/DEBUG
# =============================================================================

@main_bp.route('/debug/accounts')
@login_required
def debug_accounts():
    """Debug: Mostrar todas as accounts do usuário"""
    if not current_user.is_super_admin():
        flash('Acesso negado!', 'error')
        return redirect(url_for('main.dashboard'))
    
    from models import Account
    all_accounts = Account.query.all()
    user_accounts = current_user.get_accessible_accounts()
    
    debug_info = {
        'user': current_user,
        'user_role': current_user.role.value,
        'is_super_admin': current_user.is_super_admin(),
        'total_accounts_in_system': len(all_accounts),
        'user_accessible_accounts': len(user_accounts),
        'accounts_list': user_accounts,
        'session_account_id': request.cookies.get('current_account_id', 'None')
    }
    
    return render_template('main/debug.html', debug=debug_info)

# =============================================================================
# CONTEXT PROCESSOR GLOBAL
# =============================================================================

@main_bp.context_processor
def inject_global_context():
    """Context processor para injetar dados globais em todos os templates"""
    context = {}
    
    if current_user.is_authenticated:
        context.update({
            'current_user_full_name': current_user.get_full_name(),
            'current_user_initials': current_user.get_initials(),
            'current_user_role': current_user.role.value,
            'is_super_admin': current_user.is_super_admin(),
            'user_account_count': len(current_user.get_accessible_accounts()),
            'has_multiple_accounts': len(current_user.get_accessible_accounts()) > 1
        })
    
    return context

# =============================================================================
# ERROR HANDLERS ESPECÍFICOS
# =============================================================================

@main_bp.errorhandler(403)
def forbidden(error):
    """Handler para erro 403 - Acesso negado"""
    return render_template('errors/403.html'), 403

@main_bp.errorhandler(404)
def not_found(error):
    """Handler para erro 404 - Não encontrado"""
    return render_template('errors/404.html'), 404