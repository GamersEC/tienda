from app import db

class Atributo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre_atributo = db.Column(db.String(100), nullable=False)
    tipo_campo = db.Column(db.String(50), nullable=False, default='Texto')

    tipo_producto_id = db.Column(db.Integer, db.ForeignKey('tipo_producto.id'), nullable=False)

    #Relaciones
    opciones = db.relationship('OpcionAtributo', backref='atributo', lazy='dynamic', cascade="all, delete-orphan")
    valores = db.relationship('ValorAtributoProducto', backref='atributo', lazy='dynamic')

    def __repr__(self):
        return f'<Atributo {self.nombre_atributo}>'

class OpcionAtributo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    valor_opcion = db.Column(db.String(100), nullable=False)

    atributo_id = db.Column(db.Integer, db.ForeignKey('atributo.id'), nullable=False)

    def __repr__(self):
        return f'<OpcionAtributo {self.valor_opcion}>'