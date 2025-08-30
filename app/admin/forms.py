from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed
from wtforms import StringField, TextAreaField, DecimalField, IntegerField, SubmitField, SelectField, PasswordField, FileField
from wtforms.validators import DataRequired, NumberRange, Email, EqualTo, Optional, InputRequired
from wtforms_sqlalchemy.fields import QuerySelectField
from app.models.cliente import Cliente
from app.models.categoria_gasto import CategoriaGasto


class ClienteForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired()])
    apellido = StringField('Apellido')
    identificacion = StringField('Cédula / RUC')
    telefono = StringField('Teléfono')
    email = StringField('Email')
    direccion = StringField('Dirección (Calles)')
    ciudad = StringField('Ciudad')
    submit = SubmitField('Guardar Cliente')


# Función para obtener la lista de clientes para el formulario
def obtener_clientes():
    return Cliente.query.all()


class VentaForm(FlaskForm):
    cliente = QuerySelectField('Cliente', query_factory=obtener_clientes, get_label='nombre', allow_blank=False, validators=[DataRequired()])
    submit = SubmitField('Iniciar Venta')


class PagoForm(FlaskForm):
    monto_pago = DecimalField('Monto del Pago', validators=[DataRequired(), NumberRange(min=0.01)])
    metodo_pago = SelectField('Método de Pago', choices=[('Efectivo', 'Efectivo'), ('Transferencia', 'Transferencia')], validators=[DataRequired()])
    comprobante = FileField('Comprobante de Pago (Imagen)', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], '¡Solo se permiten imágenes!')
    ])

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


class TipoProductoForm(FlaskForm):
    nombre = StringField('Nombre del Tipo de Producto', validators=[DataRequired()])
    submit = SubmitField('Guardar')


class AtributoForm(FlaskForm):
    nombre_atributo = StringField('Nombre del Atributo', validators=[DataRequired()])
    tipo_campo = SelectField('Tipo de Campo', choices=[
        ('Texto', 'Texto Corto'),
        ('Numero', 'Número'),
        ('Seleccion', 'Lista Desplegable (Selección)')
    ], validators=[DataRequired()])
    submit = SubmitField('Añadir Atributo')


class OpcionAtributoForm(FlaskForm):
    valor_opcion = StringField('Nueva Opción', validators=[DataRequired()])
    submit = SubmitField('Añadir Opción')


class EmptyForm(FlaskForm):
    submit = SubmitField('Submit')


class AnularVentaForm(FlaskForm):
    motivo_anulacion = TextAreaField('Motivo de la Anulación', validators=[DataRequired()])
    submit = SubmitField('Confirmar Anulación')


class ConfiguracionForm(FlaskForm):
    nombre_tienda = StringField('Nombre de la Tienda', validators=[DataRequired()])
    logo = FileField('Logo de la Tienda (Opcional)', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], '¡Solo se permiten imágenes!')
    ])
    ruc = StringField('RUC')
    telefono = StringField('Teléfono de Contacto')
    direccion = StringField('Dirección de la Tienda')
    email = StringField('Email de Contacto')

    submit = SubmitField('Guardar Configuración')


class CategoriaGastoForm(FlaskForm):
    nombre = StringField('Nombre de la Categoría', validators=[DataRequired()])
    submit = SubmitField('Guardar')

def categorias_query():
    return CategoriaGasto.query.order_by(CategoriaGasto.nombre)


class GastoForm(FlaskForm):
    descripcion = StringField('Descripción del Gasto', validators=[DataRequired()])
    monto = DecimalField('Monto', validators=[DataRequired(), NumberRange(min=0.01)])
    categoria = QuerySelectField('Categoría',
                                 query_factory=categorias_query,
                                 get_label='nombre',
                                 allow_blank=False,
                                 validators=[DataRequired()])
    submit = SubmitField('Guardar Gasto')


class InteresForm(FlaskForm):
    interes_diario = DecimalField('Interés Diario (%)', validators=[InputRequired(message="Este campo es requerido."), NumberRange(min=0)])
    interes_semanal = DecimalField('Interés Semanal (%)', validators=[InputRequired(message="Este campo es requerido."), NumberRange(min=0)])
    interes_mensual = DecimalField('Interés Mensual (%)', validators=[InputRequired(message="Este campo es requerido."), NumberRange(min=0)])
    submit = SubmitField('Guardar Tasas de Interés')