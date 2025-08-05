from flask import Blueprint, render_template, request, redirect, url_for, flash
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
        
        # Buscar ou criar owner
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
            
            # Atualizar role do owner para administrador
            if owner.role == UserRole.USER:
                owner.role = UserRole.ADMINISTRADOR
                owner.account_id = account.id
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
    users = account.get_active_users().all()
    return render_template('super_admin/accounts/view.html', account=account, users=users)

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
        
        # Remover associação dos usuários
        users = account.users.all()
        for user in users:
            user.account_id = None
            if user.role == UserRole.ADMINISTRADOR:
                user.role = UserRole.USER
        
        db.session.delete(account)
        db.session.commit()
        
        flash(f'Account {account_name} deletado!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao deletar: {str(e)}', 'error')
    
    return redirect(url_for('super_admin.accounts.index'))