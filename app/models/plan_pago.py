from app import db
from datetime import datetime

class PlanPago(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    venta_id = db.Column(db.Integer, db.ForeignKey('venta.id'), nullable=False)
    numero_cuota = db.Column(db.Integer, nullable=False)
    monto_capital = db.Column(db.Numeric(10, 2), nullable=False)
    monto_interes = db.Column(db.Numeric(10, 2), nullable=False)
    monto_total_cuota = db.Column(db.Numeric(10, 2), nullable=False)
    fecha_vencimiento = db.Column(db.DateTime, nullable=False)
    estado = db.Column(db.String(20), nullable=False, default='Pendiente')
    pago_id = db.Column(db.Integer, db.ForeignKey('pago.id'), nullable=True)

    pago = db.relationship('Pago')

    def __repr__(self):
        return f'<PlanPago Cuota {self.numero_cuota} de Venta {self.venta_id}>'