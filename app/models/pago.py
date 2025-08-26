from app import db
from datetime import datetime

class Pago(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    monto_pago = db.Column(db.Numeric(10, 2), nullable=False)
    fecha_pago = db.Column(db.DateTime, default=datetime.utcnow)
    metodo_pago = db.Column(db.String(50), nullable=True) # Efectivo, Tarjeta, etc.
    venta_id = db.Column(db.Integer, db.ForeignKey('venta.id'))

    def __repr__(self):
        return f'<Pago {self.id} de Venta {self.venta_id}>'