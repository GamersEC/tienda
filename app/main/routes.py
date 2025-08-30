from flask import render_template
from flask_login import current_user
from app.main import bp

@bp.route('/')
@bp.route('/index')
def index():
    # No se requiere login para esta ruta
    return render_template('index.html', title='Bienvenido')