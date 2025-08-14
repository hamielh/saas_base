from datetime import datetime
from . import db

# Tabela de associação Many-to-Many entre User e Account
user_accounts = db.Table('user_accounts',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('account_id', db.Integer, db.ForeignKey('accounts.id'), primary_key=True),
    db.Column('role_in_account', db.String(20), nullable=False, default='user'),  # admin, user
    db.Column('created_at', db.DateTime, default=datetime.utcnow),
    db.Column('is_active', db.Boolean, default=True)
)