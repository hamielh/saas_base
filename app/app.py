from flask import Flask
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    
    # Registrar Blueprints
    from frontend.routes.auth import auth_bp
    from frontend.routes.main import main_bp
    from frontend.routes.super_admin import super_admin_bp
    from api.user import api_user_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp) 
    app.register_blueprint(super_admin_bp)
    app.register_blueprint(api_user_bp)
    
    pass
    
    @app.context_processor
    def inject_globals():
        return {
            'app_name': 'CeoTur',
            'version': '1.0.0'
        }
    
    return app

app = create_app()

if __name__ == '__main__':
    print("🚀 Iniciando CeoTur SaaS...")
    print("📊 Database:", app.config.get('SQLALCHEMY_DATABASE_URI', 'Not configured'))
    print("🔐 Secret Key:", "Configured" if app.config.get('SECRET_KEY') else "Missing")
    print("🌐 Environment:", app.config.get('FLASK_ENV', 'production'))
    print("📱 Server: http://localhost:5000")
    
    with app.app_context():
        # Criar tabelas se não existirem
        db.create_all()
        print("✅ Database tables created/verified")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=app.config.get('DEBUG', False)
    )