from app import db

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(64), nullable=False)
    apellido = db.Column(db.String(64), nullable=True)
    telefono = db.Column(db.String(20), nullable=True, index=True)
    email = db.Column(db.String(120), nullable=True, index=True)
    direccion = db.Column(db.String(255), nullable=True)
    ciudad = db.Column(db.String(64), nullable=True)
    identificacion = db.Column(db.String(20), nullable=True, unique=True, index=True)
    ventas = db.relationship('Venta', backref='cliente', lazy='dynamic')
    notas_credito = db.relationship('NotaCredito', back_populates='cliente', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Cliente {self.nombre} {self.apellido}>'