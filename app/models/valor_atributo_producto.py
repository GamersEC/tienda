from app import db

class ValorAtributoProducto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    valor = db.Column(db.String(255), nullable=False)

    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    atributo_id = db.Column(db.Integer, db.ForeignKey('atributo.id'), nullable=False)

    def __repr__(self):
        return f'<ValorAtributoProducto {self.valor}>'