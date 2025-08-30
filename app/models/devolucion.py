from app import db
from datetime import datetime

class Devolucion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    venta_id = db.Column(db.Integer, db.ForeignKey('venta.id'), nullable=False)
    fecha_devolucion = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    motivo = db.Column(db.Text, nullable=True)
    monto_total_devolucion = db.Column(db.Numeric(10, 2), nullable=False)

    #Relaciones
    productos_devueltos = db.relationship('DevolucionProducto', back_populates='devolucion', lazy='dynamic', cascade="all, delete-orphan")
    nota_credito = db.relationship('NotaCredito', back_populates='devolucion', uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Devolucion {self.id} de Venta {self.venta_id}>'