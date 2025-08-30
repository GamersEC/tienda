from app import db

class DevolucionProducto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    devolucion_id = db.Column(db.Integer, db.ForeignKey('devolucion.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    cantidad_devuelta = db.Column(db.Integer, nullable=False)
    devuelto_al_stock = db.Column(db.Boolean, default=True, nullable=False) #Para indicar si el producto volvió al inventario

    #Relaciones
    devolucion = db.relationship('Devolucion', back_populates='productos_devueltos')
    producto = db.relationship('Producto', back_populates='devoluciones_asociadas')

    def __repr__(self):
        return f'<DevolucionProducto {self.cantidad_devuelta}x Producto ID {self.producto_id}>'