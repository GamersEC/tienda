from app import db
from decimal import Decimal

class Configuracion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre_tienda = db.Column(db.String(100), default='Mi Tienda')
    logo_path = db.Column(db.String(255), nullable=True)
    ruc = db.Column(db.String(13), nullable=True)
    telefono = db.Column(db.String(20), nullable=True)
    direccion = db.Column(db.String(255), nullable=True)
    email = db.Column(db.String(120), nullable=True)

    interes_diario = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal('0.0'))
    interes_semanal = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal('0.0'))
    interes_mensual = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal('0.0'))

    dias_max_devolucion = db.Column(db.Integer, nullable=False, default=30)
    monto_minimo_credito = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.0'))

    cuotas_maximas_diario = db.Column(db.Integer, nullable=False, default=90)
    cuotas_maximas_semanal = db.Column(db.Integer, nullable=False, default=12)
    cuotas_maximas_mensual = db.Column(db.Integer, nullable=False, default=6)

    moneda_simbolo = db.Column(db.String(5), nullable=False, default='$')
    pie_pagina_recibo = db.Column(db.Text, nullable=True)

    @staticmethod
    def obtener_config():
        return Configuracion.query.first()