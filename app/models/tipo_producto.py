from app import db
from app.models.atributo import Atributo # <-- AÑADE ESTA IMPORTACIÓN

class TipoProducto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)

    productos = db.relationship('Producto', backref='tipo_producto', lazy='dynamic')

    # --- LA LÍNEA MODIFICADA ---
    atributos = db.relationship(
        'Atributo',
        backref='tipo_producto',
        lazy='dynamic',
        cascade="all, delete-orphan",
        order_by='Atributo.id' # Le decimos que siempre ordene por el ID del Atributo
    )

    def __repr__(self):
        return f'<TipoProducto {self.nombre}>'