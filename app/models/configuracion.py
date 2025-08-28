from app import db

class Configuracion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre_tienda = db.Column(db.String(100), default='Mi Tienda')
    logo_path = db.Column(db.String(255), nullable=True)
    ruc = db.Column(db.String(13), nullable=True)
    telefono = db.Column(db.String(20), nullable=True)
    direccion = db.Column(db.String(255), nullable=True)
    email = db.Column(db.String(120), nullable=True)

    @staticmethod
    def obtener_config():
        return Configuracion.query.first()