from app import db
from datetime import datetime

class Gasto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descripcion = db.Column(db.String(255), nullable=False)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    fecha = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria_gasto.id'), nullable=False)
    categoria = db.relationship('CategoriaGasto', back_populates='gastos')
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    registrado_por = db.relationship('Usuario')

    def __repr__(self):
        return f'<Gasto {self.id}: {self.descripcion}>'