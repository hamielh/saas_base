from flask_login import UserMixin
from flask_bcrypt import generate_password_hash, check_password_hash
from datetime import datetime
from enum import Enum
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
    
    # REMOVIDO: account_id (agora é Many-to-Many)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relacionamento Many-to-Many com accounts
    accounts = db.relationship('Account', 
                              secondary=user_accounts, 
                              backref=db.backref('members', lazy='dynamic'),
                              lazy='dynamic')
    
    def __init__(self, email, password, first_name, last_name, role=UserRole.USER):
        self.email = email.lower().strip()
        self.set_password(password)
        self.first_name = first_name.strip()
        self.last_name = last_name.strip()
        self.role = role
        self.theme_preference = 'light'
    
    # =============================================================================
    # MÉTODOS DE ACCOUNTS (SAAS)
    # =============================================================================
    
    def get_accounts(self):
        """Retorna todas as accounts que o usuário tem acesso"""
        if self.is_super_admin():
            # Super admin vê todas as accounts ativas
            from . import Account
            return Account.query.filter(Account.status == 'active').all()
        else:
            # Usuário vê apenas suas accounts
            return self.accounts.all()
    
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
    
    def get_current_account(self):
        """Retorna a account atual baseada na session"""
        from flask import session
        
        current_account_id = session.get('current_account_id')
        if current_account_id:
            from . import Account
            account = Account.query.get(current_account_id)
            
            # Verificar se tem acesso
            if account and (self.is_super_admin() or self.is_in_account(account)):
                return account
        
        # Se não tem na session ou não tem acesso, pegar a primeira account
        accounts = self.get_accounts()
        return accounts[0] if accounts else None
    
    def can_access_account(self, account_id):
        """Verifica se pode acessar uma account"""
        if self.is_super_admin():
            return True
        
        from . import Account
        account = Account.query.get(account_id)
        return account and self.is_in_account(account)
    
    def switch_to_account(self, account_id):
        """Troca para uma account específica"""
        if self.can_access_account(account_id):
            from flask import session
            from . import Account
            
            account = Account.query.get(account_id)
            session['current_account_id'] = account_id
            session['current_account_name'] = account.name
            return True
        return False
    
    # =============================================================================
    # MÉTODOS BÁSICOS
    # =============================================================================
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_authenticated(self):
        return True
    
    def is_active(self):
        return True
    
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return str(self.id)
    
    def is_super_admin(self):
        return self.role == UserRole.SUPER_ADMIN
    
    def is_account_owner(self):
        return self.role == UserRole.ADMINISTRADOR
    
    def can_manage_account(self):
        return self.role in [UserRole.SUPER_ADMIN, UserRole.ADMINISTRADOR]
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    def update_last_login(self):
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def to_dict(self):
        current_account = self.get_current_account()
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.get_full_name(),
            'role': self.role.value,
            'current_account_id': current_account.id if current_account else None,
            'current_account_name': current_account.name if current_account else None,
            'accounts_count': len(self.get_accounts()),
            'theme_preference': self.theme_preference,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
    
    def __repr__(self):
        return f'<User {self.email} ({self.role.value})>'