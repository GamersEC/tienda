from app import db
from datetime import datetime
from decimal import Decimal

class NotaCredito(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    devolucion_id = db.Column(db.Integer, db.ForeignKey('devolucion.id'), nullable=True)
    monto_inicial = db.Column(db.Numeric(10, 2), nullable=False)
    saldo_restante = db.Column(db.Numeric(10, 2), nullable=False)
    estado = db.Column(db.String(20), default='Activa', nullable=False) #Activa, Agotada
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    #Relaciones
    devolucion = db.relationship('Devolucion', back_populates='nota_credito')
    cliente = db.relationship('Cliente', back_populates='notas_credito')

    def __init__(self, **kwargs):
        super(NotaCredito, self).__init__(**kwargs)
        if self.saldo_restante is None:
            self.saldo_restante = self.monto_inicial

    def __repr__(self):
        return f'<NotaCredito {self.id} para Cliente {self.cliente_id} - Saldo: {self.saldo_restante}>'