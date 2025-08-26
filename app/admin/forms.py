from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DecimalField, IntegerField, SubmitField, SelectField, PasswordField
from wtforms.validators import DataRequired, NumberRange, Email, EqualTo, Optional
from wtforms_sqlalchemy.fields import QuerySelectField
from app.models.cliente import Cliente


class ProductoForm(FlaskForm):
    nombre = StringField('Nombre del Producto', validators=[DataRequired()])
    descripcion = TextAreaField('Descripción')
    precio = DecimalField('Precio', validators=[DataRequired(), NumberRange(min=0)])
    talla = StringField('Talla')
    color = StringField('Color')
    stock = IntegerField('Stock Disponible', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Guardar Producto')


class ClienteForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired()])
    apellido = StringField('Apellido')
    telefono = StringField('Teléfono')
    email = StringField('Email')
    submit = SubmitField('Guardar Cliente')


# Función para obtener la lista de clientes para el formulario
def obtener_clientes():
    return Cliente.query.all()


class VentaForm(FlaskForm):
    cliente = QuerySelectField('Cliente', query_factory=obtener_clientes, get_label='nombre', allow_blank=False, validators=[DataRequired()])
    submit = SubmitField('Iniciar Venta')


class PagoForm(FlaskForm):
    monto_pago = DecimalField('Monto del Pago', validators=[DataRequired(), NumberRange(min=0.01)])
    metodo_pago = SelectField('Método de Pago', choices=[
        ('Efectivo', 'Efectivo'),
        ('Transferencia', 'Transferencia')
    ], validators=[DataRequired()])
    submit = SubmitField('Registrar Pago')


class AgregarProductoVentaForm(FlaskForm):
    # Este formulario es especial porque llenaremos los productos dinámicamente
    producto = QuerySelectField('Producto', get_label='nombre', allow_blank=False)
    cantidad = IntegerField('Cantidad', validators=[DataRequired(), NumberRange(min=1)], default=1)
    submit = SubmitField('Añadir Producto')


class EditarVentaForm(FlaskForm):
    notas = TextAreaField('Notas Adicionales')
    submit = SubmitField('Guardar Notas')


class UsuarioForm(FlaskForm):
    nombre = StringField('Nombre Completo', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    rol = SelectField('Rol', choices=[('Vendedor', 'Vendedor'), ('Administrador', 'Administrador')], validators=[DataRequired()])

    # Hacemos la contraseña opcional solo si el usuario ya existe (estamos editando)
    password = PasswordField('Contraseña', validators=[Optional(), EqualTo('password2', message='Las contraseñas deben coincidir.')])
    password2 = PasswordField('Confirmar Contraseña', validators=[Optional()])

    submit = SubmitField('Guardar Usuario')