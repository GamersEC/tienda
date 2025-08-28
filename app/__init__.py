from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import Config

# -----------------------------------------------------------
# Inicialización de Extensiones Globales
# -----------------------------------------------------------

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor, inicie sesión para acceder a esta página.'
login_manager.login_message_category = 'info'


# -----------------------------------------------------------
# Fábrica de Aplicaciones (Application Factory)
# -----------------------------------------------------------

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Inicializar extensiones con la aplicación
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)  # <-- 3. INICIALIZAR CSRFPROTECT CON LA APP

    # -----------------------------------------------------------
    # Importaciones y Registros Locales (DENTRO de la fábrica)
    # -----------------------------------------------------------
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from app import commands
    commands.init_app(app)

    from . import context_processors
    app.context_processor(context_processors.inject_config)

    # -----------------------------------------------------------
    # Importar modelos al final
    # -----------------------------------------------------------
    from app.models import (
        producto, cliente, venta, pago, venta_producto, usuario,
        tipo_producto, atributo, valor_atributo_producto, configuracion
    )

    return app


# -----------------------------------------------------------
# User Loader para Flask-Login
# -----------------------------------------------------------
from app.models.usuario import Usuario

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))