from app import db

class VentaProducto(db.Model):
    __tablename__ = 'venta_producto'
    id = db.Column(db.Integer, primary_key=True)
    venta_id = db.Column(db.Integer, db.ForeignKey('venta.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Numeric(10, 2), nullable=False)

    venta = db.relationship('Venta', back_populates='productos_asociados')
    producto = db.relationship('Producto', back_populates='ventas_asociadas')