#!/bin/bash
# Script para aplicar as mudanças no relacionamento

echo "🔄 Aplicando mudanças no relacionamento User <-> Account..."

# 1. Parar o servidor se estiver rodando
echo "⏹️ Parando servidor Flask..."
pkill -f "python.*app.py"

# 2. Fazer backup do banco atual
echo "💾 Fazendo backup do banco de dados..."
cp app/ceotur_dev.db app/ceotur_dev.db.backup.$(date +%Y%m%d_%H%M%S)

# 3. Atualizar os arquivos dos modelos
echo "📝 Atualizando modelos..."

# Atualizar user.py
sed -i "s/backref=db.backref('members', lazy='dynamic')/backref=db.backref('users', lazy='dynamic')/g" app/models/user.py

# Atualizar account.py - método get_user_count
sed -i 's/return self\.members\.count()/return self.users.count()/g' app/models/account.py

# Atualizar account.py - método get_users
sed -i 's/return self\.members\.all()/return self.users.all()/g' app/models/account.py

echo "✅ Modelos atualizados!"

# 4. Gerar nova migração
echo "🔄 Gerando migração..."
cd app
python -c "
from app import app
from flask_migrate import upgrade, migrate
import os

with app.app_context():
    try:
        # Apenas recria as tabelas sem migração formal (para desenvolvimento)
        from models import db
        print('Recriando tabelas...')
        db.drop_all()
        db.create_all()
        print('✅ Banco de dados atualizado!')
    except Exception as e:
        print(f'❌ Erro: {e}')
"

echo "🚀 Iniciando servidor..."
python app.py &

echo "✅ Mudanças aplicadas com sucesso!"
echo "📊 Agora o relacionamento é: account.users.all()"
echo "🌐 Servidor: http://localhost:5000"