from app import db
from datetime import datetime

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    precio = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    tipo_producto_id = db.Column(db.Integer, db.ForeignKey('tipo_producto.id'), nullable=False)

    valores_atributos = db.relationship('ValorAtributoProducto', backref='producto', lazy='dynamic', cascade="all, delete-orphan")
    ventas_asociadas = db.relationship('VentaProducto', back_populates='producto')
    devoluciones_asociadas = db.relationship('DevolucionProducto', back_populates='producto', lazy='dynamic')

    def __repr__(self):
        return f'<Producto {self.nombre}>'


    def obtener_valor_atributo(self, nombre_atributo):
        from app.models.atributo import Atributo
        from app.models.valor_atributo_producto import ValorAtributoProducto

        attr = Atributo.query.filter_by(nombre_atributo=nombre_atributo, tipo_producto_id=self.tipo_producto_id).first()
        if not attr:
            return None

        valor_obj = ValorAtributoProducto.query.filter_by(producto_id=self.id, atributo_id=attr.id).first()
        return valor_obj.valor if valor_obj else None