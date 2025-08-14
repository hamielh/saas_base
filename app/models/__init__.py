from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Importar a tabela de associação primeiro
from .user_account import user_accounts

# Depois importar os modelos
from .user import User, UserRole
from .account import Account, AccountStatus

__all__ = [
    'db',
    'user_accounts',
    'User', 
    'UserRole',
    'Account',
    'AccountStatus'
]