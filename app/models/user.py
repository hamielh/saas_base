from flask_login import UserMixin
from flask_bcrypt import generate_password_hash, check_password_hash
from datetime import datetime
from enum import Enum
from flask import session
from . import db
from .user_account import user_accounts

class UserRole(Enum):
    SUPER_ADMIN = "super_admin" 
    ADMINISTRADOR = "administrador"
    USER = "user"

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    
    # Campo para preferência de tema
    theme_preference = db.Column(db.String(10), default='light')
    
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.USER)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relacionamento Many-to-Many com accounts (ATUALIZADO)
    accounts = db.relationship('Account', 
                              secondary=user_accounts, 
                              backref=db.backref('users', lazy='dynamic'),
                              lazy='dynamic')
    
    def __init__(self, email, password, first_name, last_name, role=UserRole.USER):
        self.email = email.lower().strip()
        self.set_password(password)
        self.first_name = first_name.strip()
        self.last_name = last_name.strip()
        self.role = role
        self.theme_preference = 'light'
    
    # =============================================================================
    # MÉTODOS DE SENHA E AUTENTICAÇÃO
    # =============================================================================
    
    def set_password(self, password):
        """Define a senha do usuário"""
        self.password_hash = generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        """Verifica se a senha está correta"""
        return check_password_hash(self.password_hash, password)
    
    def get_full_name(self):
        """Retorna nome completo"""
        return f"{self.first_name} {self.last_name}"
    
    def get_initials(self):
        """Retorna iniciais do nome"""
        return f"{self.first_name[0]}{self.last_name[0]}".upper()
    
    # =============================================================================
    # MÉTODOS DE ROLES E PERMISSÕES
    # =============================================================================
    
    def is_super_admin(self):
        """Verifica se é super admin"""
        return self.role == UserRole.SUPER_ADMIN
    
    def is_admin(self):
        """Verifica se é administrador (qualquer tipo)"""
        return self.role in [UserRole.SUPER_ADMIN, UserRole.ADMINISTRADOR]
    
    def is_regular_user(self):
        """Verifica se é usuário comum"""
        return self.role == UserRole.USER
    
    # =============================================================================
    # MÉTODOS DE ACCOUNTS - NOVOS PARA MULTI-TENANT
    # =============================================================================
    
    def get_accessible_accounts(self):
        """Retorna todas as accounts que o usuário pode acessar"""
        if self.is_super_admin():
            # Super admin vê todas as accounts ativas
            from .account import Account, AccountStatus
            return Account.query.filter(Account.status == AccountStatus.ACTIVE).all()
        else:
            # Usuário vê apenas suas accounts
            return self.accounts.filter_by(is_active=True).all()
    
    def can_access_account(self, account_id):
        """Verifica se o usuário pode acessar uma account específica"""
        if self.is_super_admin():
            return True
        
        # Verificar se está associado à account
        return self.accounts.filter_by(id=account_id).first() is not None
    
    def get_default_account(self):
        """Retorna a account padrão do usuário (primeira disponível)"""
        accessible_accounts = self.get_accessible_accounts()
        return accessible_accounts[0] if accessible_accounts else None
    
    def get_current_account_from_session(self):
        """Retorna a account atual baseada na session"""
        current_account_id = session.get('current_account_id')
        if current_account_id and self.can_access_account(current_account_id):
            from .account import Account
            return Account.query.get(current_account_id)
        return self.get_default_account()
    
    def set_current_account(self, account_id):
        """Define a account atual na session"""
        if self.can_access_account(account_id):
            session['current_account_id'] = account_id
            return True
        return False
    
    def get_role_in_account(self, account):
        """Retorna o role do usuário em uma account específica"""
        if self.is_super_admin():
            return 'super_admin'
        
        # Consultar role na tabela de associação
        result = db.session.execute(
            db.select([user_accounts.c.role_in_account]).where(
                (user_accounts.c.user_id == self.id) & 
                (user_accounts.c.account_id == account.id)
            )
        ).first()
        
        return result[0] if result else None
    
    def is_owner_of_account(self, account):
        """Verifica se é owner de uma account"""
        return account.owner_id == self.id
    
    def is_admin_of_account(self, account):
        """Verifica se é administrador de uma account específica"""
        if self.is_super_admin():
            return True
        
        role_in_account = self.get_role_in_account(account)
        return role_in_account in ['admin', 'owner'] or self.is_owner_of_account(account)
    
    # =============================================================================
    # MÉTODOS DE ASSOCIAÇÃO COM ACCOUNTS
    # =============================================================================
    
    def add_to_account(self, account, role_in_account='user'):
        """Adiciona usuário a uma account"""
        if not self.is_in_account(account):
            # Usar SQL direto para inserir na tabela de associação
            db.session.execute(
                user_accounts.insert().values(
                    user_id=self.id,
                    account_id=account.id,
                    role_in_account=role_in_account
                )
            )
            return True
        return False
    
    def remove_from_account(self, account):
        """Remove usuário de uma account"""
        if self.is_in_account(account):
            db.session.execute(
                user_accounts.delete().where(
                    (user_accounts.c.user_id == self.id) & 
                    (user_accounts.c.account_id == account.id)
                )
            )
            return True
        return False
    
    def is_in_account(self, account):
        """Verifica se usuário está em uma account"""
        return self.accounts.filter_by(id=account.id).first() is not None
    
    def update_role_in_account(self, account, new_role):
        """Atualiza o role do usuário em uma account"""
        if self.is_in_account(account):
            db.session.execute(
                user_accounts.update().where(
                    (user_accounts.c.user_id == self.id) & 
                    (user_accounts.c.account_id == account.id)
                ).values(role_in_account=new_role)
            )
            return True
        return False
    
    # =============================================================================
    # MÉTODOS DE SAÍDA E REPRESENTAÇÃO
    # =============================================================================
    
    def to_dict(self):
        """Converte usuário para dict"""
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.get_full_name(),
            'initials': self.get_initials(),
            'role': self.role.value,
            'theme_preference': self.theme_preference,
            'account_count': self.accounts.count(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
    
    def __repr__(self):
        return f'<User {self.email} ({self.role.value})>'