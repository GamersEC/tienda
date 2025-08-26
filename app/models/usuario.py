from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256)) # Aumentado el tamaño por si acaso
    rol = db.Column(db.String(20), nullable=False, default='Vendedor') # Roles: 'Vendedor', 'Administrador'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.rol == 'Administrador'

    def __repr__(self):
        return f'<Usuario {self.nombre} ({self.rol})>'