from app import db

class CategoriaGasto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)

    gastos = db.relationship('Gasto', back_populates='categoria', lazy='dynamic')

    def __repr__(self):
        return f'<CategoriaGasto {self.nombre}>'