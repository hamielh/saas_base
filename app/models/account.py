from datetime import datetime
from enum import Enum
from . import db

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
    
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    users = db.relationship('User', foreign_keys='User.account_id', backref='account', lazy='dynamic')
    owner = db.relationship('User', foreign_keys=[owner_id], backref='owned_accounts')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_accounts')
    
    def __init__(self, name, owner_id, created_by, subdomain=None):
        self.name = name.strip()
        self.owner_id = owner_id
        self.created_by = created_by
        self.subdomain = subdomain.lower().strip() if subdomain else None
    
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
    
    def get_active_users(self):
        return self.users.filter_by(is_active=True)
    
    def get_user_count(self):
        return self.users.filter_by(is_active=True).count()
    
    def can_add_users(self, limit=None):
        if not limit:
            return True
        return self.get_user_count() < limit
    
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
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Account {self.name} ({self.status.value})>'