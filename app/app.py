from flask import Flask
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
import os
import sys

# Adicionar o diretório atual e o pai ao path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, current_dir)
sys.path.insert(0, parent_dir)

from models import db, User
login_manager = LoginManager()
bcrypt = Bcrypt()
migrate = Migrate()

def create_app():
    
    app = Flask(__name__, 
               template_folder='frontend/templates',
               static_folder='frontend/static',
               static_url_path='/static')
    
    app.config.from_object('config.DevelopmentConfig')
    
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor, faça login para acessar esta página.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # =============================================================================
    # REGISTRAR BLUEPRINTS - NOVA ESTRUTURA
    # =============================================================================
    
    # Blueprints de autenticação e principais (sem mudança)
    from frontend.routes.auth import auth_bp
    from frontend.routes.main import main_bp
    
    # NOVO: Blueprint de accounts (multi-tenant)
    from frontend.routes.account import account_bp
    
    # Blueprint de super admin (mantido)
    from frontend.routes.super_admin import super_admin_bp
    
    # APIs (mantidas)
    from api.user import api_user_bp
    from api.settings import api_settings_bp
    
    # Registrar blueprints na ordem correta
    app.register_blueprint(auth_bp)              # /login, /logout, /register
    app.register_blueprint(main_bp)              # /, /dashboard, /profile, etc
    app.register_blueprint(account_bp)           # /account/{id}/dashboard, etc
    app.register_blueprint(super_admin_bp)       # /super-admin/*
    app.register_blueprint(api_user_bp)          # /api/create-user, etc
    app.register_blueprint(api_settings_bp)      # /api/user/theme, etc
    
    # =============================================================================
    # CONTEXT PROCESSORS GLOBAIS
    # =============================================================================
    
    @app.context_processor
    def inject_globals():
        """Context processor global para toda a aplicação"""
        return {
            'app_name': 'CeoTur',
            'version': '2.0.0',  # Atualizada para v2 com multi-tenant
            'environment': app.config.get('FLASK_ENV', 'production')
        }
    
    # =============================================================================
    # ERROR HANDLERS GLOBAIS
    # =============================================================================
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handler para erro 500 - Erro interno"""
        db.session.rollback()
        from flask import render_template
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        """Handler para erro 403 - Acesso negado"""
        from flask import render_template
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(404)
    def not_found_error(error):
        """Handler para erro 404 - Página não encontrada"""
        from flask import render_template
        return render_template('errors/404.html'), 404
    
    # =============================================================================
    # HELPER FUNCTIONS GLOBAIS
    # =============================================================================
    
    @app.template_filter('account_url')
    def account_url_filter(endpoint, account_id=None, **values):
        """
        Template filter global para gerar URLs com account_id
        Uso nos templates: {{ 'account.dashboard'|account_url }}
        """
        from flask import g, url_for
        
        if account_id is None and hasattr(g, 'current_account'):
            account_id = g.current_account.id
        
        if account_id:
            values['account_id'] = account_id
        
        return url_for(endpoint, **values)
    
    @app.template_filter('user_can_access')
    def user_can_access_filter(account_id):
        """
        Template filter para verificar se usuário pode acessar account
        Uso: {% if account.id|user_can_access %}
        """
        from flask_login import current_user
        if current_user.is_authenticated:
            return current_user.can_access_account(account_id)
        return False
    
    @app.template_filter('format_date')
    def format_date_filter(date, format='%d/%m/%Y'):
        """
        Template filter para formatar datas
        Uso: {{ account.created_at|format_date }}
        """
        if date:
            return date.strftime(format)
        return 'N/A'
    
    @app.template_filter('time_ago')
    def time_ago_filter(date):
        """
        Template filter para mostrar tempo relativo
        Uso: {{ user.last_login|time_ago }}
        """
        if not date:
            return 'Nunca'
        
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        diff = now - date
        
        if diff.days > 7:
            return date.strftime('%d/%m/%Y')
        elif diff.days > 0:
            return f'{diff.days} dia{"s" if diff.days > 1 else ""} atrás'
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f'{hours} hora{"s" if hours > 1 else ""} atrás'
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f'{minutes} minuto{"s" if minutes > 1 else ""} atrás'
        else:
            return 'Agora mesmo'
    
    # =============================================================================
    # BEFORE REQUEST HANDLERS
    # =============================================================================
    
    @app.before_request
    def before_request():
        """Executado antes de cada request"""
        from flask import g, request
        from flask_login import current_user
        
        # Disponibilizar informações globais
        g.request_path = request.path
        g.is_account_route = request.path.startswith('/account/')
        
        if current_user.is_authenticated:
            g.user_is_super_admin = current_user.is_super_admin()
            g.user_accessible_accounts = current_user.get_accessible_accounts()
            g.user_has_multiple_accounts = len(g.user_accessible_accounts) > 1
    
    return app

app = create_app()

if __name__ == '__main__':
    print("🚀 Iniciando CeoTur SaaS Multi-Tenant...")
    print("📊 Database:", app.config.get('SQLALCHEMY_DATABASE_URI', 'Not configured'))
    print("🔐 Secret Key:", "Configured" if app.config.get('SECRET_KEY') else "Missing")
    print("🌐 Environment:", app.config.get('FLASK_ENV', 'production'))
    print("📱 Server: http://localhost:5000")
    print("🏢 Multi-Tenant: Enabled")
    print("🔄 URL Structure: /account/{id}/dashboard")
    
    with app.app_context():
        # Criar tabelas se não existirem
        try:
            db.create_all()
            print("✅ Database tables created/verified")
            
            # Verificar se existem accounts
            from models import Account
            account_count = Account.query.count()
            print(f"📋 Total accounts: {account_count}")
            
            # Verificar super admin
            from models import User, UserRole
            super_admin_count = User.query.filter_by(role=UserRole.SUPER_ADMIN).count()
            print(f"👑 Super admins: {super_admin_count}")
            
        except Exception as e:
            print(f"❌ Database error: {e}")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=app.config.get('DEBUG', False)
    )