from app import db
from datetime import datetime

class Venta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha_venta = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    monto_total = db.Column(db.Numeric(10, 2), nullable=False)
    estado = db.Column(db.String(20), nullable=False, default='En Proceso') #En Proceso, Pendiente, Pagada, Anulada, Credito, Con Devolución

    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'))
    notas = db.Column(db.Text, nullable=True)

    anulada_por_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    motivo_anulacion = db.Column(db.Text, nullable=True)
    fecha_anulacion = db.Column(db.DateTime, nullable=True)

    tipo_pago = db.Column(db.String(20), nullable=False, default='Contado') #Contado, Credito
    numero_cuotas = db.Column(db.Integer, nullable=True)
    frecuencia_cuotas = db.Column(db.String(20), nullable=True) #Diaria, Semanal, Mensual
    abono_inicial = db.Column(db.Numeric(10, 2), nullable=True)

    #Relaciones
    anulada_por = db.relationship('Usuario')
    pagos = db.relationship('Pago', backref='venta', lazy='dynamic')
    productos_asociados = db.relationship('VentaProducto', back_populates='venta', cascade="all, delete-orphan")

    plan_pagos = db.relationship('PlanPago', backref='venta', lazy='dynamic', cascade="all, delete-orphan")
    devoluciones = db.relationship('Devolucion', backref='venta', lazy='dynamic', cascade="all, delete-orphan")
    def __repr__(self):
        return f'<Venta {self.id}>'