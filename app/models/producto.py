from app import db
from datetime import datetime

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    precio = db.Column(db.Numeric(10, 2), nullable=False)
    talla = db.Column(db.String(10), nullable=True)
    color = db.Column(db.String(50), nullable=True)
    stock = db.Column(db.Integer, nullable=False, default=0)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    ventas_asociadas = db.relationship('VentaProducto', back_populates='producto')

    def __repr__(self):
        return f'<Producto {self.nombre}>'