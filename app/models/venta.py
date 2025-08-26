from app import db
from datetime import datetime

class Venta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha_venta = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    monto_total = db.Column(db.Numeric(10, 2), nullable=False)
    estado = db.Column(db.String(20), nullable=False, default='Pendiente') # Pendiente, Pagada
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'))
    notas = db.Column(db.Text, nullable=True)
    pagos = db.relationship('Pago', backref='venta', lazy='dynamic', order_by='Pago.fecha_pago.asc()')
    productos_asociados = db.relationship('VentaProducto', back_populates='venta', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Venta {self.id}>'