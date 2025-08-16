from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user
from models import db, Account, User, UserRole, AccountStatus
from . import super_admin_required

accounts_bp = Blueprint('accounts', __name__, url_prefix='/accounts')

@accounts_bp.route('/')
@super_admin_required
def index():
    """Lista todos os accounts"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    
    query = Account.query
    
    # Filtro de busca
    if search:
        query = query.filter(
            (Account.name.contains(search)) |
            (Account.subdomain.contains(search))
        )
    
    # Filtro de status
    if status_filter:
        try:
            status_enum = AccountStatus(status_filter)
            query = query.filter(Account.status == status_enum)
        except ValueError:
            pass
    
    # Paginação
    accounts = query.order_by(Account.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('super_admin/accounts/index.html', 
                         accounts=accounts, 
                         search=search, 
                         status_filter=status_filter)

@accounts_bp.route('/create', methods=['GET', 'POST'])
@super_admin_required
def create():
    """Criar novo account"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        subdomain = request.form.get('subdomain', '').strip().lower()
        owner_email = request.form.get('owner_email', '').strip().lower()
        
        if not all([name, owner_email]):
            flash('Nome e email do owner são obrigatórios!', 'error')
            return render_template('super_admin/accounts/create.html')
        
        # Verificar se subdomain já existe
        if subdomain:
            existing_account = Account.query.filter_by(subdomain=subdomain).first()
            if existing_account:
                flash(f'Subdomínio {subdomain} já está em uso!', 'error')
                return render_template('super_admin/accounts/create.html')
        
        # Buscar owner
        owner = User.query.filter_by(email=owner_email).first()
        if not owner:
            flash(f'Usuário com email {owner_email} não encontrado!', 'error')
            return render_template('super_admin/accounts/create.html')
        
        try:
            account = Account(
                name=name,
                subdomain=subdomain if subdomain else None,
                owner_id=owner.id,
                created_by=current_user.id
            )
            
            db.session.add(account)
            db.session.commit()
            
            # Adicionar owner ao account usando relacionamento many-to-many
            owner.add_to_account(account, 'admin')
            
            # Atualizar role do owner para administrador (se não for super admin)
            if owner.role == UserRole.USER:
                owner.role = UserRole.ADMINISTRADOR
            
            db.session.commit()
            
            flash(f'Account {account.name} criado com sucesso!', 'success')
            return redirect(url_for('super_admin.accounts.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar account: {str(e)}', 'error')
    
    # Listar usuários disponíveis para ser owner
    available_users = User.query.filter(
        (User.role == UserRole.USER) | (User.role == UserRole.ADMINISTRADOR)
    ).all()
    
    return render_template('super_admin/accounts/create.html', users=available_users)

@accounts_bp.route('/<int:account_id>')
@super_admin_required
def view(account_id):
    """Ver detalhes do account"""
    account = Account.query.get_or_404(account_id)
    
    # Buscar todos os usuários do account
    users = account.users.all()
    
    return render_template('super_admin/accounts/view.html', 
                         account=account, 
                         users=users)

@accounts_bp.route('/<int:account_id>/edit', methods=['GET', 'POST'])
@super_admin_required
def edit(account_id):
    """Editar account"""
    account = Account.query.get_or_404(account_id)
    
    if request.method == 'POST':
        account.name = request.form.get('name', '').strip()
        subdomain = request.form.get('subdomain', '').strip().lower()
        status = request.form.get('status', 'active')
        
        # Verificar subdomain
        if subdomain and subdomain != account.subdomain:
            existing = Account.query.filter_by(subdomain=subdomain).first()
            if existing:
                flash(f'Subdomínio {subdomain} já está em uso!', 'error')
                return render_template('super_admin/accounts/edit.html', account=account)
        
        account.subdomain = subdomain if subdomain else None
        
        # Atualizar status
        status_map = {
            'active': AccountStatus.ACTIVE,
            'suspended': AccountStatus.SUSPENDED,
            'inactive': AccountStatus.INACTIVE
        }
        account.status = status_map.get(status, AccountStatus.ACTIVE)
        
        try:
            db.session.commit()
            flash(f'Account {account.name} atualizado!', 'success')
            return redirect(url_for('super_admin.accounts.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar: {str(e)}', 'error')
    
    return render_template('super_admin/accounts/edit.html', account=account)

@accounts_bp.route('/<int:account_id>/delete', methods=['POST'])
@super_admin_required
def delete(account_id):
    """Deletar account"""
    account = Account.query.get_or_404(account_id)
    
    try:
        account_name = account.name
        
        # Remover associação dos usuários usando relacionamento many-to-many
        users = account.users.all()
        for user in users:
            user.remove_from_account(account)
            # Se user era admin deste account apenas, rebaixar para user
            remaining_accounts = user.get_accounts()
            if user.role == UserRole.ADMINISTRADOR and len(remaining_accounts) == 0:
                user.role = UserRole.USER
        
        db.session.delete(account)
        db.session.commit()
        
        flash(f'Account {account_name} deletado!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao deletar: {str(e)}', 'error')
    
    return redirect(url_for('super_admin.accounts.index'))

@accounts_bp.route('/<int:account_id>/users')
@super_admin_required
def manage_users(account_id):
    """Gerenciar usuários do account"""
    account = Account.query.get_or_404(account_id)
    users = account.users.all()
    
    # Usuários disponíveis para adicionar (que NÃO estão neste account)
    available_users = User.query.filter(
        ~User.accounts.any(Account.id == account_id)
    ).all()
    
    return render_template('super_admin/accounts/manage_users.html', 
                         account=account, 
                         users=users, 
                         available_users=available_users)

@accounts_bp.route('/<int:account_id>/users/add', methods=['POST'])
@super_admin_required
def add_user(account_id):
    """Adicionar usuário ao account"""
    account = Account.query.get_or_404(account_id)
    
    try:
        user_id = request.form.get('user_id', type=int)
        role = request.form.get('role', 'user')
        
        if not user_id:
            flash('Usuário é obrigatório!', 'error')
            return redirect(url_for('super_admin.accounts.manage_users', account_id=account_id))
        
        user = User.query.get_or_404(user_id)
        
        # Verificar se usuário já está no account
        if user in account.users:
            flash(f'Usuário {user.get_full_name()} já está neste account!', 'error')
            return redirect(url_for('super_admin.accounts.manage_users', account_id=account_id))
        
        # Adicionar usuário ao account
        user.add_to_account(account, role)
        
        # Atualizar role global se necessário (não alterar super admin)
        if not user.is_super_admin():
            if role == 'admin':
                user.role = UserRole.ADMINISTRADOR
            # Manter role atual se já é admin ou deixar como está
        
        db.session.commit()
        
        flash(f'Usuário {user.get_full_name()} adicionado ao account!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao adicionar usuário: {str(e)}', 'error')
    
    return redirect(url_for('super_admin.accounts.manage_users', account_id=account_id))

@accounts_bp.route('/<int:account_id>/users/remove', methods=['POST'])
@super_admin_required
def remove_user(account_id):
    """Remover usuário do account"""
    account = Account.query.get_or_404(account_id)
    
    try:
        data = request.get_json()
        user_id = data.get('user_id', type=int)
        
        if not user_id:
            return jsonify({'success': False, 'error': 'ID do usuário é obrigatório'})
        
        user = User.query.get_or_404(user_id)
        
        # Não permitir remover o owner
        if user.id == account.owner_id:
            return jsonify({'success': False, 'error': 'Não é possível remover o administrador do account'})
        
        # Remover usuário do account usando relacionamento many-to-many
        user.remove_from_account(account)
        
        # Se não tem mais accounts e era admin, rebaixar para user
        remaining_accounts = user.get_accounts()
        if user.role == UserRole.ADMINISTRADOR and len(remaining_accounts) == 0:
            user.role = UserRole.USER
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Usuário {user.get_full_name()} removido do account'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@accounts_bp.route('/<int:account_id>/transfer-ownership', methods=['POST'])
@super_admin_required
def transfer_ownership(account_id):
    """Transferir ownership do account"""
    account = Account.query.get_or_404(account_id)
    
    try:
        new_owner_id = request.form.get('new_owner_id', type=int)
        
        if not new_owner_id:
            flash('Novo administrador é obrigatório!', 'error')
            return redirect(url_for('super_admin.accounts.manage_users', account_id=account_id))
        
        new_owner = User.query.get_or_404(new_owner_id)
        
        # Verificar se o usuário está no account
        if new_owner not in account.users:
            flash('O novo administrador deve pertencer ao account!', 'error')
            return redirect(url_for('super_admin.accounts.manage_users', account_id=account_id))
        
        # Demover o owner atual (se existir)
        if account.owner:
            old_owner = account.owner
            old_owner.role = UserRole.USER
        
        # Promover o novo owner
        new_owner.role = UserRole.ADMINISTRADOR
        account.owner_id = new_owner_id
        
        db.session.commit()
        
        flash(f'Administração transferida para {new_owner.get_full_name()}!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao transferir administração: {str(e)}', 'error')
    
    return redirect(url_for('super_admin.accounts.manage_users', account_id=account_id))

@accounts_bp.route('/<int:account_id>/users/<int:user_id>/promote', methods=['POST'])
@super_admin_required
def promote_user(account_id, user_id):
    """Promover usuário a administrador"""
    account = Account.query.get_or_404(account_id)
    user = User.query.get_or_404(user_id)
    
    try:
        # Verificar se usuário pertence ao account
        if user not in account.users:
            return jsonify({'success': False, 'error': 'Usuário não pertence a este account'})
        
        # Promover usuário
        user.role = UserRole.ADMINISTRADOR
        # Atualizar role na tabela de associação também
        account.update_user_role(user, 'admin')
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'{user.get_full_name()} promovido a administrador'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@accounts_bp.route('/<int:account_id>/users/<int:user_id>/demote', methods=['POST'])
@super_admin_required
def demote_user(account_id, user_id):
    """Rebaixar administrador a usuário comum"""
    account = Account.query.get_or_404(account_id)
    user = User.query.get_or_404(user_id)
    
    try:
        # Não permitir rebaixar o owner
        if user.id == account.owner_id:
            return jsonify({'success': False, 'error': 'Não é possível rebaixar o owner do account'})
        
        # Rebaixar usuário
        user.role = UserRole.USER
        # Atualizar role na tabela de associação também
        account.update_user_role(user, 'user')
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'{user.get_full_name()} rebaixado a usuário comum'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})