from app import db
from datetime import datetime

class Pago(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    monto_pago = db.Column(db.Numeric(10, 2), nullable=False)
    fecha_pago = db.Column(db.DateTime, default=datetime.utcnow)
    metodo_pago = db.Column(db.String(50), nullable=True)
    venta_id = db.Column(db.Integer, db.ForeignKey('venta.id'))
    comprobante_path = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f'<Pago {self.id} de Venta {self.venta_id}>'