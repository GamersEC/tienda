from app import db

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(64), nullable=False)
    apellido = db.Column(db.String(64), nullable=True)
    telefono = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), index=True, unique=True, nullable=True)
    ventas = db.relationship('Venta', backref='cliente', lazy='dynamic')

    def __repr__(self):
        return f'<Cliente {self.nombre} {self.apellido}>'