from datetime import datetime
from enum import Enum
from . import db
from .user_account import user_accounts

class AccountStatus(Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"

class Account(db.Model):
    __tablename__ = 'accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    subdomain = db.Column(db.String(50), unique=True, nullable=True, index=True)
    
    status = db.Column(db.Enum(AccountStatus), nullable=False, default=AccountStatus.ACTIVE)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Owner continua sendo um relacionamento direto (1 owner por account)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    owner = db.relationship('User', foreign_keys=[owner_id], backref='owned_accounts')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_accounts')
    
    # Many-to-Many com users já definido no User model via backref 'members'
    
    def __init__(self, name, owner_id, created_by, subdomain=None):
        self.name = name.strip()
        self.owner_id = owner_id
        self.created_by = created_by
        self.subdomain = subdomain.lower().strip() if subdomain else None
    
    # =============================================================================
    # MÉTODOS DE USUÁRIOS (SAAS)
    # =============================================================================
    
    def get_user_count(self):
        """Retorna número de usuários na account"""
        return self.members.count()
    
    def get_users(self):
        """Retorna todos os usuários da account"""
        return self.members.all()
    
    def add_user(self, user, role_in_account='user'):
        """Adiciona usuário à account"""
        return user.add_to_account(self, role_in_account)
    
    def remove_user(self, user):
        """Remove usuário da account"""
        return user.remove_from_account(self)
    
    def get_admins(self):
        """Retorna usuários com role admin na account"""
        admin_user_ids = db.session.execute(
            db.select([user_accounts.c.user_id]).where(
                (user_accounts.c.account_id == self.id) & 
                (user_accounts.c.role_in_account == 'admin')
            )
        ).fetchall()
        
        if admin_user_ids:
            from . import User
            return User.query.filter(User.id.in_([uid[0] for uid in admin_user_ids])).all()
        return []
    
    def get_regular_users(self):
        """Retorna usuários com role user na account"""
        user_user_ids = db.session.execute(
            db.select([user_accounts.c.user_id]).where(
                (user_accounts.c.account_id == self.id) & 
                (user_accounts.c.role_in_account == 'user')
            )
        ).fetchall()
        
        if user_user_ids:
            from . import User
            return User.query.filter(User.id.in_([uid[0] for uid in user_user_ids])).all()
        return []
    
    def has_user(self, user):
        """Verifica se usuário está na account"""
        return user.is_in_account(self)
    
    def get_user_role(self, user):
        """Retorna o role do usuário na account"""
        return user.get_role_in_account(self)
    
    def update_user_role(self, user, new_role):
        """Atualiza o role do usuário na account"""
        if self.has_user(user):
            db.session.execute(
                user_accounts.update().where(
                    (user_accounts.c.user_id == user.id) & 
                    (user_accounts.c.account_id == self.id)
                ).values(role_in_account=new_role)
            )
            return True
        return False
    
    # =============================================================================
    # MÉTODOS DE STATUS E VALIDAÇÃO
    # =============================================================================
    
    def is_active_account(self):
        return self.is_active and self.status == AccountStatus.ACTIVE
    
    def activate(self):
        self.status = AccountStatus.ACTIVE
        self.is_active = True
    
    def suspend(self):
        self.status = AccountStatus.SUSPENDED
    
    def deactivate(self):
        self.status = AccountStatus.INACTIVE
        self.is_active = False
    
    def can_add_users(self, limit=None):
        if not limit:
            return True
        return self.get_user_count() < limit
    
    # =============================================================================
    # MÉTODOS DE SAÍDA E REPRESENTAÇÃO
    # =============================================================================
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'subdomain': self.subdomain,
            'status': self.status.value,
            'is_active': self.is_active,
            'owner_id': self.owner_id,
            'owner_name': self.owner.get_full_name() if self.owner else None,
            'user_count': self.get_user_count(),
            'admin_count': len(self.get_admins()),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Account {self.name} ({self.status.value})>'