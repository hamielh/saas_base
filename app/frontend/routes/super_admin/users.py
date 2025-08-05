from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import db, User, UserRole
from . import super_admin_required

users_bp = Blueprint('users', __name__, url_prefix='/users')

@users_bp.route('/')
@super_admin_required
def index():
    """Lista todos os usuários"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    role_filter = request.args.get('role', '')
    
    query = User.query
    
    # Filtro de busca
    if search:
        query = query.filter(
            (User.email.contains(search)) |
            (User.first_name.contains(search)) |
            (User.last_name.contains(search))
        )
    
    # Filtro de role
    if role_filter:
        try:
            role_enum = UserRole(role_filter)
            query = query.filter(User.role == role_enum)
        except ValueError:
            pass
    
    # Paginação
    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('super_admin/users/index.html', 
                         users=users, 
                         search=search, 
                         role_filter=role_filter)

@users_bp.route('/create', methods=['GET', 'POST'])
@super_admin_required
def create():
    """Criar novo usuário"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        role = request.form.get('role', 'user')
        
        if not all([email, password, first_name, last_name]):
            flash('Todos os campos são obrigatórios!', 'error')
            return render_template('super_admin/users/create.html')
        
        # Verificar se email já existe
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash(f'Email {email} já está em uso!', 'error')
            return render_template('super_admin/users/create.html')
        
        # Converter role
        role_map = {
            'super_admin': UserRole.SUPER_ADMIN,
            'administrador': UserRole.ADMINISTRADOR,
            'user': UserRole.USER
        }
        user_role = role_map.get(role, UserRole.USER)
        
        try:
            user = User(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=user_role
            )
            
            db.session.add(user)
            db.session.commit()
            
            flash(f'Usuário {user.get_full_name()} criado com sucesso!', 'success')
            return redirect(url_for('super_admin.users.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar usuário: {str(e)}', 'error')
    
    return render_template('super_admin/users/create.html')

@users_bp.route('/<int:user_id>')
@super_admin_required
def view(user_id):
    """Ver detalhes do usuário"""
    user = User.query.get_or_404(user_id)
    return render_template('super_admin/users/view.html', user=user)

@users_bp.route('/<int:user_id>/edit', methods=['GET', 'POST'])
@super_admin_required
def edit(user_id):
    """Editar usuário"""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.first_name = request.form.get('first_name', '').strip()
        user.last_name = request.form.get('last_name', '').strip()
        role = request.form.get('role', 'user')
        
        # Converter role
        role_map = {
            'super_admin': UserRole.SUPER_ADMIN,
            'administrador': UserRole.ADMINISTRADOR,
            'user': UserRole.USER
        }
        user.role = role_map.get(role, UserRole.USER)
        
        try:
            db.session.commit()
            flash(f'Usuário {user.get_full_name()} atualizado!', 'success')
            return redirect(url_for('super_admin.users.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar: {str(e)}', 'error')
    
    return render_template('super_admin/users/edit.html', user=user)

@users_bp.route('/<int:user_id>/delete', methods=['POST'])
@super_admin_required
def delete(user_id):
    """Deletar usuário"""
    user = User.query.get_or_404(user_id)
    
    # Não permitir deletar o próprio usuário
    if user.id == current_user.id:
        flash('Você não pode deletar sua própria conta!', 'error')
        return redirect(url_for('super_admin.users.index'))
    
    try:
        user_name = user.get_full_name()
        db.session.delete(user)
        db.session.commit()
        flash(f'Usuário {user_name} deletado!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao deletar: {str(e)}', 'error')
    
    return redirect(url_for('super_admin.users.index'))