from flask_login import UserMixin
from flask_bcrypt import generate_password_hash, check_password_hash
from datetime import datetime
from enum import Enum
from . import db

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
    # is_active removido - não existe na tabela atual
    
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.USER)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def __init__(self, email, password, first_name, last_name, role=UserRole.USER, account_id=None):
        self.email = email.lower().strip()
        self.set_password(password)
        self.first_name = first_name.strip()
        self.last_name = last_name.strip()
        self.role = role
        self.account_id = account_id
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_authenticated(self):
        return True
    
    def is_active(self):
        return True  # Por enquanto sempre ativo
    
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
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.get_full_name(),
            'role': self.role.value,
            'account_id': self.account_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
    
    def __repr__(self):
        return f'<User {self.email} ({self.role.value})>'