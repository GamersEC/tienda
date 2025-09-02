import os
from flask import render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, or_, cast, Date
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import uuid
from math import isclose
from decimal import Decimal
from weasyprint import HTML, CSS
from pdf2image import convert_from_bytes

#Importaciones de WTForms
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DecimalField, IntegerField, SelectField
from wtforms.validators import DataRequired, NumberRange

#Importaciones locales
from app import db
from app.admin import bp
from app.utils.decorators import admin_required

#Importación de todos los Modelos
from app.models.producto import Producto
from app.models.cliente import Cliente
from app.models.venta import Venta
from app.models.pago import Pago
from app.models.venta_producto import VentaProducto
from app.models.usuario import Usuario
from app.models.tipo_producto import TipoProducto
from app.models.atributo import Atributo, OpcionAtributo
from app.models.valor_atributo_producto import ValorAtributoProducto
from app.models.configuracion import Configuracion
from app.models.gasto import Gasto
from app.models.categoria_gasto import CategoriaGasto
from app.models.plan_pago import PlanPago
from app.models.devolucion import Devolucion
from app.models.devolucion_producto import DevolucionProducto

#Importación de todos los Formularios
from app.admin.forms import (
    ClienteForm, VentaForm, PagoForm, AgregarProductoVentaForm,
    EditarVentaForm, UsuarioForm, TipoProductoForm, AtributoForm,
    OpcionAtributoForm, EmptyForm, AnularVentaForm, ConfiguracionForm,
    GastoForm, CategoriaGastoForm, InteresForm, CreditoForm, PagoCuotaForm,
    DevolucionForm, DevolucionProductoForm
)

#Calcular el plan de pagos para ventas a crédito
def _calcular_plan_de_pagos(monto_venta, abono_inicial, numero_cuotas, frecuencia, config):
    if numero_cuotas == 0:
        return []

    capital_a_financiar = Decimal(monto_venta) - Decimal(abono_inicial)
    tasa_interes = Decimal('0.0')

    if frecuencia == 'Diaria':
        tasa_interes = config.interes_diario / Decimal('100.0')
    elif frecuencia == 'Semanal':
        tasa_interes = config.interes_semanal / Decimal('100.0')
    elif frecuencia == 'Mensual':
        tasa_interes = config.interes_mensual / Decimal('100.0')

    interes_total = capital_a_financiar * tasa_interes * Decimal(numero_cuotas)
    total_a_pagar = capital_a_financiar + interes_total

    monto_total_cuota = total_a_pagar / Decimal(numero_cuotas)
    capital_por_cuota = capital_a_financiar / Decimal(numero_cuotas)
    interes_por_cuota = interes_total / Decimal(numero_cuotas)

    plan_pagos = []
    fecha_actual = datetime.utcnow()

    for i in range(1, numero_cuotas + 1):
        fecha_vencimiento = fecha_actual
        if frecuencia == 'Diaria':
            fecha_vencimiento += timedelta(days=i)
        elif frecuencia == 'Semanal':
            fecha_vencimiento += timedelta(weeks=i)
        elif frecuencia == 'Mensual':
            fecha_vencimiento += timedelta(days=30 * i)

        cuota = {
            'numero_cuota': i,
            'monto_capital': capital_por_cuota,
            'monto_interes': interes_por_cuota,
            'monto_total_cuota': monto_total_cuota,
            'fecha_vencimiento': fecha_vencimiento
        }
        plan_pagos.append(cuota)

    return plan_pagos


@bp.route('/configuracion', methods=['GET', 'POST'])
@admin_required
def configuracion_tienda():
    config = Configuracion.obtener_config()
    if not config:
        config = Configuracion()
        db.session.add(config)
        db.session.commit()

    form = ConfiguracionForm(obj=config)
    if form.validate_on_submit():
        form.populate_obj(config)

        logo_file = form.logo.data
        if logo_file:
            if config.logo_path and os.path.exists(os.path.join(current_app.static_folder, config.logo_path)):
                os.remove(os.path.join(current_app.static_folder, config.logo_path))
            filename = secure_filename(f"{uuid.uuid4().hex}_{logo_file.filename}")
            upload_dir = os.path.join(current_app.static_folder, 'uploads', 'logos')
            os.makedirs(upload_dir, exist_ok=True)
            filepath = os.path.join(upload_dir, filename)
            logo_file.save(filepath)
            config.logo_path = f'uploads/logos/{filename}'

        db.session.commit()
        flash('La configuración de la tienda ha sido actualizada.', 'success')
        return redirect(url_for('admin.configuracion_tienda'))

    return render_template('admin/configuracion.html', form=form, config=config, titulo='Configuración de la Tienda')

@bp.route('/configuracion/intereses', methods=['GET', 'POST'])
@admin_required
def configuracion_intereses():
    config = Configuracion.obtener_config()
    if not config:
        #En el caso improbable de que no exista, la creamos
        config = Configuracion()
        db.session.add(config)
        db.session.commit()

    form = InteresForm(obj=config)
    if form.validate_on_submit():
        config.interes_diario = form.interes_diario.data
        config.interes_semanal = form.interes_semanal.data
        config.interes_mensual = form.interes_mensual.data
        db.session.commit()
        flash('Las tasas de interés han sido actualizadas exitosamente.', 'success')
        return redirect(url_for('admin.configuracion_intereses'))

    return render_template('admin/configuracion_intereses.html', form=form, titulo='Tasas de Interés para Créditos')


# -----------------------------------------------------------------------------
# --- CAPA DE SEGURIDAD GLOBAL PARA EL BLUEPRINT ---
# -----------------------------------------------------------------------------
@bp.before_request
@login_required
def before_request():
    pass


# -----------------------------------------------------------------------------
# --- RUTA PRINCIPAL DEL DASHBOARD ---
# -----------------------------------------------------------------------------
@bp.route('/dashboard')
@login_required
def dashboard():
    # Fechas de referencia
    hoy_inicio = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    hace_30_dias = datetime.utcnow() - timedelta(days=30)

    # --- CÁLCULOS FINANCIEROS CLAROS ---

    # 1. INGRESOS BRUTOS (Total de ventas finalizadas en el período)
    ingresos_brutos_mes = db.session.query(func.sum(Venta.monto_total)).filter(
        Venta.fecha_venta >= hace_30_dias,
        Venta.estado.in_(['Pagada', 'Credito', 'Con Devolucion'])
    ).scalar() or Decimal('0.0')

    # 2. REEMBOLSOS (Total de dinero devuelto a clientes, registrado como gasto)
    reembolsos_mes = db.session.query(func.sum(Gasto.monto)).join(CategoriaGasto).filter(
        Gasto.fecha >= hace_30_dias,
        CategoriaGasto.nombre == 'Devoluciones'
    ).scalar() or Decimal('0.0')

    # 3. INGRESOS NETOS (Lo que realmente queda después de devoluciones)
    ingresos_netos_mes = ingresos_brutos_mes - reembolsos_mes

    # 4. GASTOS OPERATIVOS (Todos los gastos EXCEPTO devoluciones)
    gastos_operativos_mes = db.session.query(func.sum(Gasto.monto)).join(CategoriaGasto).filter(
        Gasto.fecha >= hace_30_dias,
        CategoriaGasto.nombre != 'Devoluciones'
    ).scalar() or Decimal('0.0')

    # 5. BENEFICIO NETO (La ganancia final)
    beneficio_neto_mes = ingresos_netos_mes - gastos_operativos_mes

    # Métricas del día (para vista rápida)
    ingresos_hoy = db.session.query(func.sum(Venta.monto_total)).filter(
        Venta.fecha_venta >= hoy_inicio,
        Venta.estado.in_(['Pagada', 'Pendiente', 'Credito', 'Con Devolucion'])
    ).scalar() or Decimal('0.0')
    ventas_hoy = Venta.query.filter(
        Venta.fecha_venta >= hoy_inicio,
        Venta.estado.in_(['Pagada', 'Pendiente', 'Credito', 'Con Devolucion'])
    ).count()

    # Gráfico de ventas (basado en Ingresos Brutos)
    ventas_por_dia = db.session.query(
        cast(Venta.fecha_venta, Date).label('dia'),
        func.sum(Venta.monto_total).label('total_vendido')
    ).filter(
        Venta.fecha_venta >= hace_30_dias,
        Venta.estado.in_(['Pagada', 'Pendiente', 'Credito', 'Con Devolucion'])
    ).group_by('dia').order_by('dia').all()
    chart_labels = [venta.dia.strftime('%d %b') for venta in ventas_por_dia]
    chart_data = [float(venta.total_vendido) for venta in ventas_por_dia]

    # Consultas "Top 5"
    top_productos = db.session.query(
        Producto,
        func.sum(VentaProducto.cantidad).label('total_cantidad')
    ).join(VentaProducto).join(Venta).filter(
        Venta.fecha_venta >= hace_30_dias,
        Venta.estado.in_(['Pagada', 'Pendiente','Credito', 'Con Devolucion'])
    ).group_by(Producto.id).order_by(func.sum(VentaProducto.cantidad).desc()).limit(5).all()

    top_clientes = db.session.query(
        Cliente,
        func.sum(Venta.monto_total).label('total_gastado')
    ).join(Venta).filter(
        Venta.fecha_venta >= hace_30_dias,
        Venta.estado.in_(['Pagada', 'Pendiente','Credito', 'Con Devolucion'])
    ).group_by(Cliente.id).order_by(func.sum(Venta.monto_total).desc()).limit(5).all()

    top_categorias_gasto = db.session.query(
        CategoriaGasto.nombre,
        func.sum(Gasto.monto).label('total_gastado')
    ).join(Gasto).filter(
        Gasto.fecha >= hace_30_dias
    ).group_by(CategoriaGasto.nombre).order_by(func.sum(Gasto.monto).desc()).limit(5).all()

    productos_bajo_stock = Producto.query.filter(Producto.stock <= 5).order_by(Producto.stock.asc()).limit(5).all()

    return render_template('admin/dashboard.html',
                           titulo='Dashboard Analítico',
                           ingresos_brutos_mes=ingresos_brutos_mes,
                           reembolsos_mes=reembolsos_mes,
                           ingresos_netos_mes=ingresos_netos_mes,
                           gastos_operativos_mes=gastos_operativos_mes,
                           beneficio_neto_mes=beneficio_neto_mes,
                           ingresos_hoy=ingresos_hoy,
                           ventas_hoy=ventas_hoy,
                           chart_labels=chart_labels,
                           chart_data=chart_data,
                           top_productos=top_productos,
                           top_clientes=top_clientes,
                           top_categorias_gasto=top_categorias_gasto,
                           productos_bajo_stock=productos_bajo_stock)

@bp.route('/')
@login_required
def index():
    return redirect(url_for('admin.dashboard'))


# -----------------------------------------------------------------------------
# --- FLUJO DE GESTIÓN DE PRODUCTOS CON ATRIBUTOS DINÁMICOS ---
# -----------------------------------------------------------------------------
@bp.route('/productos')
def listar_productos():
    productos = Producto.query.order_by(Producto.nombre).all()
    form = EmptyForm() # Para el token CSRF del botón de eliminar
    return render_template('admin/productos.html', productos=productos, form=form)

@bp.route('/productos/seleccionar-tipo', methods=['GET', 'POST'])
@admin_required
def seleccionar_tipo_producto():
    tipos = TipoProducto.query.order_by(TipoProducto.nombre).all()
    if not tipos:
        flash('Primero debes crear al menos un "Tipo de Producto" para poder añadir productos.', 'info')
        return redirect(url_for('admin.listar_tipos_producto'))

    form = EmptyForm()
    if form.validate_on_submit():
        tipo_id = request.form.get('tipo_producto')
        if tipo_id:
            return redirect(url_for('admin.crear_producto_dinamico', tipo_id=tipo_id))
        else:
            flash('Por favor, selecciona un tipo de producto.', 'warning')

    return render_template('admin/seleccionar_tipo_producto.html', tipos=tipos, form=form)

@bp.route('/productos/crear/tipo/<int:tipo_id>', methods=['GET', 'POST'])
@admin_required
def crear_producto_dinamico(tipo_id):
    tipo = TipoProducto.query.get_or_404(tipo_id)

    #Construcción dinámica del formulario
    class DynamicProductForm(FlaskForm):
        nombre = StringField('Nombre del Producto', validators=[DataRequired()])
        descripcion = TextAreaField('Descripción')
        precio = DecimalField('Precio', validators=[DataRequired(), NumberRange(min=0)])
        stock = IntegerField('Stock Disponible', validators=[DataRequired(), NumberRange(min=0)])

    for atributo in tipo.atributos:
        field_name = f'attr_{atributo.id}'
        validators = [DataRequired()]
        field = None

        if atributo.tipo_campo == 'Texto':
            field = StringField(atributo.nombre_atributo, validators=validators)
        elif atributo.tipo_campo == 'Numero':
            field = IntegerField(atributo.nombre_atributo, validators=validators)
        elif atributo.tipo_campo == 'Seleccion':
            choices = [(op.valor_opcion, op.valor_opcion) for op in atributo.opciones]
            field = SelectField(atributo.nombre_atributo, choices=choices, validators=validators)

        if field:
            setattr(DynamicProductForm, field_name, field)

    form = DynamicProductForm()

    if form.validate_on_submit():
        nuevo_producto = Producto(
            nombre=form.nombre.data,
            descripcion=form.descripcion.data,
            precio=form.precio.data,
            stock=form.stock.data,
            tipo_producto_id=tipo.id
        )
        db.session.add(nuevo_producto)
        db.session.flush()

        for atributo in tipo.atributos:
            field_name = f'attr_{atributo.id}'
            valor_data = form[field_name].data
            valor_atributo = ValorAtributoProducto(
                valor=str(valor_data),
                producto_id=nuevo_producto.id,
                atributo_id=atributo.id
            )
            db.session.add(valor_atributo)

        db.session.commit()
        flash('Producto creado exitosamente.', 'success')
        return redirect(url_for('admin.listar_productos'))

    return render_template('admin/crear_editar_producto_dinamico.html', form=form, tipo=tipo, titulo=f'Crear Nuevo {tipo.nombre}')

@bp.route('/productos/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def editar_producto(id):
    producto = Producto.query.get_or_404(id)
    tipo = producto.tipo_producto

    class DynamicProductForm(FlaskForm):
        nombre = StringField('Nombre del Producto', validators=[DataRequired()])
        descripcion = TextAreaField('Descripción')
        precio = DecimalField('Precio', validators=[DataRequired(), NumberRange(min=0)])
        stock = IntegerField('Stock Disponible', validators=[DataRequired(), NumberRange(min=0)])

    for atributo in tipo.atributos:
        field_name = f'attr_{atributo.id}'
        validators = [DataRequired()]
        field = None

        if atributo.tipo_campo == 'Texto':
            field = StringField(atributo.nombre_atributo, validators=validators)
        elif atributo.tipo_campo == 'Numero':
            field = IntegerField(atributo.nombre_atributo, validators=validators)
        elif atributo.tipo_campo == 'Seleccion':
            choices = [(op.valor_opcion, op.valor_opcion) for op in atributo.opciones]
            field = SelectField(atributo.nombre_atributo, choices=choices, validators=validators)

        if field:
            setattr(DynamicProductForm, field_name, field)

    form = DynamicProductForm(obj=producto)

    if form.validate_on_submit():
        #Actualizar los datos principales del producto
        producto.nombre = form.nombre.data
        producto.descripcion = form.descripcion.data
        producto.precio = form.precio.data
        producto.stock = form.stock.data

        #Actualizar los valores de los atributos dinámicos
        for atributo in tipo.atributos:
            field_name = f'attr_{atributo.id}'
            valor_data = form[field_name].data

            #Busca el valor existente para este atributo y producto
            valor_atributo_existente = ValorAtributoProducto.query.filter_by(
                producto_id=producto.id,
                atributo_id=atributo.id
            ).first()

            if valor_atributo_existente:
                valor_atributo_existente.valor = str(valor_data)
            else:
                #En el caso improbable de que no exista, lo creamos
                nuevo_valor = ValorAtributoProducto(
                    valor=str(valor_data),
                    producto_id=producto.id,
                    atributo_id=atributo.id
                )
                db.session.add(nuevo_valor)

        db.session.commit()
        flash('Producto actualizado exitosamente.', 'success')
        return redirect(url_for('admin.listar_productos'))

    #Logica para precargar el formulario con los datos existentes
    for atributo in tipo.atributos:
        field_name = f'attr_{atributo.id}'
        valor_existente = ValorAtributoProducto.query.filter_by(
            producto_id=producto.id,
            atributo_id=atributo.id
        ).first()
        if valor_existente:
            #Obtiene el campo del formulario y asigna su valor
            form_field = getattr(form, field_name)
            form_field.data = valor_existente.valor

    return render_template('admin/crear_editar_producto_dinamico.html',
                           form=form,
                           tipo=tipo,
                           titulo=f'Editar Producto: {producto.nombre}')

@bp.route('/productos/eliminar/<int:id>', methods=['POST'])
@admin_required
def eliminar_producto(id):
    producto = Producto.query.get_or_404(id)
    #Eliminamos las asociaciones de ventas para mantener la integridad
    VentaProducto.query.filter_by(producto_id=id).delete()
    ValorAtributoProducto.query.filter_by(producto_id=id).delete()
    db.session.delete(producto)
    db.session.commit()
    flash('¡Producto eliminado exitosamente!', 'success')
    return redirect(url_for('admin.listar_productos'))


# -----------------------------------------------------------------------------
# --- RUTAS PARA CLIENTES ---
# -----------------------------------------------------------------------------
@bp.route('/clientes')
def listar_clientes():
    clientes = Cliente.query.all()
    return render_template('admin/clientes.html', clientes=clientes)

@bp.route('/clientes/crear', methods=['GET', 'POST'])
def crear_cliente():
    form = ClienteForm()
    if form.validate_on_submit():
        nuevo_cliente = Cliente(
            nombre=form.nombre.data,
            apellido=form.apellido.data,
            telefono=form.telefono.data,
            email=form.email.data,
            identificacion=form.identificacion.data,
            direccion=form.direccion.data,
            ciudad=form.ciudad.data
        )
        db.session.add(nuevo_cliente)
        db.session.commit()
        flash('¡Cliente creado exitosamente!', 'success')
        return redirect(url_for('admin.listar_clientes'))
    return render_template('admin/crear_editar_cliente.html', form=form, titulo='Crear Nuevo Cliente')

@bp.route('/clientes/editar/<int:id>', methods=['GET', 'POST'])
def editar_cliente(id):
    cliente = Cliente.query.get_or_404(id)
    form = ClienteForm(obj=cliente)
    if form.validate_on_submit():
        cliente.nombre = form.nombre.data
        cliente.apellido = form.apellido.data
        cliente.telefono = form.telefono.data
        cliente.email = form.email.data
        cliente.identificacion = form.identificacion.data
        cliente.direccion = form.direccion.data
        cliente.ciudad = form.ciudad.data
        db.session.commit()
        flash('¡Cliente actualizado exitosamente!', 'success')
        return redirect(url_for('admin.listar_clientes'))
    return render_template('admin/crear_editar_cliente.html', form=form, titulo='Editar Cliente')

@bp.route('/clientes/eliminar/<int:id>', methods=['POST'])
@admin_required
def eliminar_cliente(id):
    cliente = Cliente.query.get_or_404(id)
    db.session.delete(cliente)
    db.session.commit()
    flash('¡Cliente eliminado exitosamente!', 'success')
    return redirect(url_for('admin.listar_clientes'))

@bp.route('/api/clientes/buscar')
@login_required
def buscar_clientes():
    search_term = request.args.get('q', '', type=str)
    if not search_term:
        return jsonify([])

    #Buscamos por nombre, apellido o identificación
    clientes = Cliente.query.filter(
        or_(
            (Cliente.nombre + ' ' + Cliente.apellido).ilike(f'%{search_term}%'),
            Cliente.identificacion.ilike(f'%{search_term}%')
        )
    ).limit(10).all()

    #Devolvemos los resultados en formato JSON
    return jsonify([
        {'id': c.id, 'text': f"{c.nombre} {c.apellido or ''} ({c.identificacion or 'Sin ID'})"}
        for c in clientes
    ])


# -----------------------------------------------------------------------------
# --- RUTAS PARA GESTIÓN DE GASTOS ---
# -----------------------------------------------------------------------------
@bp.route('/gastos')
@login_required
def listar_gastos():
    gastos = Gasto.query.order_by(Gasto.fecha.desc()).all()
    return render_template('admin/gastos.html', gastos=gastos, titulo='Registro de Gastos')

@bp.route('/gastos/crear', methods=['GET', 'POST'])
@admin_required
def crear_gasto():
    form = GastoForm()
    if not CategoriaGasto.query.first():
        flash('Primero debes crear al menos una categoría de gasto.', 'warning')
        return redirect(url_for('admin.listar_categorias_gasto'))
    if form.validate_on_submit():
        nuevo_gasto = Gasto(
            descripcion=form.descripcion.data,
            monto=form.monto.data,
            categoria=form.categoria.data, # form.categoria.data ahora es un objeto CategoriaGasto
            usuario_id=current_user.id
        )
        db.session.add(nuevo_gasto)
        db.session.commit()
        flash('Gasto registrado exitosamente.', 'success')
        return redirect(url_for('admin.listar_gastos'))
    return render_template('admin/crear_editar_gasto.html', form=form, titulo='Registrar Nuevo Gasto')

@bp.route('/gastos/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def editar_gasto(id):
    gasto = Gasto.query.get_or_404(id)
    form = GastoForm(obj=gasto)
    if form.validate_on_submit():
        gasto.descripcion = form.descripcion.data
        gasto.monto = form.monto.data
        gasto.categoria = form.categoria.data
        db.session.commit()
        flash('Gasto actualizado exitosamente.', 'success')
        return redirect(url_for('admin.listar_gastos'))
    return render_template('admin/crear_editar_gasto.html', form=form, titulo='Editar Gasto')

@bp.route('/gastos/eliminar/<int:id>', methods=['POST'])
@admin_required
def eliminar_gasto(id):
    gasto = Gasto.query.get_or_404(id)
    db.session.delete(gasto)
    db.session.commit()
    flash('Gasto eliminado exitosamente.', 'success')
    return redirect(url_for('admin.listar_gastos'))


# -----------------------------------------------------------------------------
# --- RUTAS PARA CATEGORÍAS DE GASTO ---
# -----------------------------------------------------------------------------
@bp.route('/gastos/categorias')
@admin_required
def listar_categorias_gasto():
    categorias = CategoriaGasto.query.order_by(CategoriaGasto.nombre).all()
    return render_template('admin/categorias_gasto.html', categorias=categorias, titulo='Categorías de Gasto')

@bp.route('/gastos/categorias/crear', methods=['GET', 'POST'])
@admin_required
def crear_categoria_gasto():
    form = CategoriaGastoForm()
    if form.validate_on_submit():
        nueva_categoria = CategoriaGasto(nombre=form.nombre.data)
        db.session.add(nueva_categoria)
        db.session.commit()
        flash('Categoría creada exitosamente.', 'success')
        return redirect(url_for('admin.listar_categorias_gasto'))
    return render_template('admin/crear_editar_categoria.html', form=form, titulo='Crear Categoría de Gasto')

@bp.route('/gastos/categorias/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def editar_categoria_gasto(id):
    categoria = CategoriaGasto.query.get_or_404(id)
    form = CategoriaGastoForm(obj=categoria)
    if form.validate_on_submit():
        categoria.nombre = form.nombre.data
        db.session.commit()
        flash('Categoría actualizada exitosamente.', 'success')
        return redirect(url_for('admin.listar_categorias_gasto'))
    return render_template('admin/crear_editar_categoria.html', form=form, titulo='Editar Categoría de Gasto')

@bp.route('/gastos/categorias/eliminar/<int:id>', methods=['POST'])
@admin_required
def eliminar_categoria_gasto(id):
    categoria = CategoriaGasto.query.get_or_404(id)
    if categoria.gastos.first():
        flash('No se puede eliminar la categoría porque tiene gastos asociados.', 'danger')
    else:
        db.session.delete(categoria)
        db.session.commit()
        flash('Categoría eliminada exitosamente.', 'success')
    return redirect(url_for('admin.listar_categorias_gasto'))


# -----------------------------------------------------------------------------
# --- RUTAS PARA VENTAS ---
# -----------------------------------------------------------------------------
@bp.route('/ventas')
def listar_ventas():
    ventas = Venta.query.order_by(Venta.fecha_venta.desc()).all()
    return render_template('admin/ventas.html', ventas=ventas)

@bp.route('/ventas/crear', methods=['GET', 'POST'])
def crear_venta():
    form = EmptyForm()
    if form.validate_on_submit():
        cliente_id = request.form.get('cliente_id')
        if not cliente_id:
            flash('Debes seleccionar un cliente.', 'danger')
            return redirect(url_for('admin.crear_venta'))

        nueva_venta = Venta(
            cliente_id=cliente_id,
            monto_total=0,
            estado='En Proceso'
        )
        db.session.add(nueva_venta)
        db.session.commit()
        flash('Venta iniciada. Ahora añade productos y define los términos de pago.', 'success')
        return redirect(url_for('admin.editar_venta', id=nueva_venta.id))

    return render_template('admin/crear_venta.html', form=form, titulo='Iniciar Nueva Venta')


@bp.route('/ventas/editar/<int:id>', methods=['GET', 'POST'])
def editar_venta(id):
    venta = Venta.query.get_or_404(id)
    config = Configuracion.obtener_config()

    if venta.estado != 'En Proceso':
        flash('Esta venta ya está finalizada y no se puede modificar.', 'warning')
        return redirect(url_for('admin.ver_venta', id=id))

    anular_venta_form = AnularVentaForm()
    agregar_producto_form = AgregarProductoVentaForm()
    credito_form = CreditoForm(obj=venta)

    productos_disponibles = Producto.query.filter(Producto.stock > 0).order_by(Producto.nombre).all()
    opciones_productos = []
    for p in productos_disponibles:
        atributos_str = ", ".join(f"{val.atributo.nombre_atributo}: {val.valor}" for val in p.valores_atributos)
        texto_opcion = f"{p.nombre} ({atributos_str})" if atributos_str else p.nombre
        opciones_productos.append((p.id, texto_opcion))
    agregar_producto_form.producto.choices = opciones_productos

    stock_data = {str(p.id): p.stock for p in productos_disponibles}

    config_data_for_js = {
        'montoMinimoCredito': float(config.monto_minimo_credito or 0),
        'cuotasMaximas': {
            'Diaria': config.cuotas_maximas_diario,
            'Semanal': config.cuotas_maximas_semanal,
            'Mensual': config.cuotas_maximas_mensual
        }
    }

    if 'submit_producto' in request.form and agregar_producto_form.validate():
        producto_id = agregar_producto_form.producto.data
        producto = Producto.query.get(producto_id)
        cantidad_a_vender = agregar_producto_form.cantidad.data
        if cantidad_a_vender > producto.stock:
            flash(f'No se puede añadir. Solo quedan {producto.stock} unidades de "{producto.nombre}".', 'danger')
        else:
            asociacion_existente = VentaProducto.query.filter_by(venta_id=venta.id, producto_id=producto.id).first()
            if asociacion_existente:
                asociacion_existente.cantidad += cantidad_a_vender
            else:
                asociacion_existente = VentaProducto(venta_id=venta.id, producto_id=producto.id, cantidad=cantidad_a_vender, precio_unitario=producto.precio)
                db.session.add(asociacion_existente)
            producto.stock -= cantidad_a_vender
            db.session.commit()
            flash(f'{cantidad_a_vender} x "{producto.nombre}" añadido(s) a la venta.', 'success')
        return redirect(url_for('admin.editar_venta', id=id))

    if 'submit_credito' in request.form and credito_form.validate():
        if not venta.productos_asociados:
            flash('No se puede finalizar una venta sin productos.', 'danger')
            return redirect(url_for('admin.editar_venta', id=id))

        if credito_form.tipo_pago.data == 'Credito':
            if config and venta.monto_total < config.monto_minimo_credito:
                flash(f'El monto de la venta (${venta.monto_total}) es menor al mínimo requerido (${config.monto_minimo_credito}) para ofrecer crédito.', 'danger')
                return redirect(url_for('admin.editar_venta', id=id))

        venta.tipo_pago = credito_form.tipo_pago.data
        if venta.tipo_pago == 'Credito':
            if not credito_form.numero_cuotas.data or not credito_form.frecuencia_cuotas.data:
                flash('El número y la frecuencia de cuotas son requeridos para ventas a crédito.', 'danger')
                return redirect(url_for('admin.editar_venta', id=id))
            venta.numero_cuotas = credito_form.numero_cuotas.data
            venta.frecuencia_cuotas = credito_form.frecuencia_cuotas.data
            venta.abono_inicial = credito_form.abono_inicial.data or 0
            plan_calculado = _calcular_plan_de_pagos(venta.monto_total, venta.abono_inicial, venta.numero_cuotas, venta.frecuencia_cuotas, config)
            for cuota_data in plan_calculado:
                nueva_cuota = PlanPago(venta_id=venta.id, numero_cuota=cuota_data['numero_cuota'], monto_capital=cuota_data['monto_capital'], monto_interes=cuota_data['monto_interes'], monto_total_cuota=cuota_data['monto_total_cuota'], fecha_vencimiento=cuota_data['fecha_vencimiento'])
                db.session.add(nueva_cuota)
            if venta.abono_inicial > 0:
                abono = Pago(monto_pago=venta.abono_inicial, metodo_pago=credito_form.metodo_pago_abono.data, venta_id=venta.id)
                comprobante_file = credito_form.comprobante_abono.data
                if comprobante_file:
                    filename = secure_filename(f"{uuid.uuid4().hex}_{comprobante_file.filename}")
                    upload_dir = os.path.join(current_app.static_folder, 'uploads', 'comprobantes')
                    os.makedirs(upload_dir, exist_ok=True)
                    filepath = os.path.join(upload_dir, filename)
                    comprobante_file.save(filepath)
                    abono.comprobante_path = os.path.join('uploads', 'comprobantes', filename)
                db.session.add(abono)
            venta.estado = 'Credito'
            flash('Venta a crédito finalizada. Plan de pagos generado.', 'success')
        else:
            venta.estado = 'Pendiente'
            flash('Venta de contado finalizada. Pendiente de pago.', 'success')
        db.session.commit()
        return redirect(url_for('admin.ver_venta', id=id))

    total_calculado = db.session.query(func.sum(VentaProducto.precio_unitario * VentaProducto.cantidad)).filter_by(venta_id=id).scalar() or 0
    venta.monto_total = total_calculado
    db.session.commit()

    return render_template('admin/editar_venta.html',
                           venta=venta,
                           agregar_producto_form=agregar_producto_form,
                           credito_form=credito_form,
                           anular_venta_form=anular_venta_form,
                           stock_data=stock_data,
                           config=config,
                           config_data=config_data_for_js)

@bp.route('/ventas/editar/<int:venta_id>/eliminar_producto/<int:producto_asociado_id>', methods=['POST'])
@admin_required
def eliminar_producto_venta(venta_id, producto_asociado_id):
    asociacion = VentaProducto.query.get_or_404(producto_asociado_id)
    producto = Producto.query.get(asociacion.producto_id)
    producto.stock += asociacion.cantidad
    db.session.delete(asociacion)
    db.session.commit()
    flash('Producto eliminado de la venta.', 'success')
    return redirect(url_for('admin.editar_venta', id=venta_id))

@bp.route('/ventas/finalizar/<int:id>', methods=['POST'])
def finalizar_venta(id):
    flash('Esta acción ha sido movida a la página de edición de venta.', 'info')
    return redirect(url_for('admin.editar_venta', id=id))


@bp.route('/ventas/<int:id>')
def ver_venta(id):
    venta = Venta.query.get_or_404(id)
    config = Configuracion.obtener_config()
    pago_form = PagoForm()
    pago_cuota_form = PagoCuotaForm()
    total_pagado = db.session.query(func.sum(Pago.monto_pago)).filter_by(venta_id=id).scalar() or 0
    pagos_ordenados = venta.pagos.order_by(Pago.fecha_pago.asc()).all()

    productos_activos_en_venta = []
    for item_venta in venta.productos_asociados:
        cantidad_devuelta = db.session.query(func.sum(DevolucionProducto.cantidad_devuelta)).join(Devolucion).filter(
            Devolucion.venta_id == venta.id,
            DevolucionProducto.producto_id == item_venta.producto_id
        ).scalar() or 0

        cantidad_activa = item_venta.cantidad - cantidad_devuelta
        if cantidad_activa > 0:
            #Creamos un objeto temporal para pasarlo a la plantilla con la cantidad correcta
            item_activo = {
                'producto': item_venta.producto,
                'cantidad': cantidad_activa,
                'precio_unitario': item_venta.precio_unitario,
                'subtotal': cantidad_activa * item_venta.precio_unitario
            }
            productos_activos_en_venta.append(item_activo)

    devolucion_permitida = False
    mensaje_devolucion = ""
    if config:
        dias_desde_venta = (datetime.utcnow() - venta.fecha_venta).days
        if dias_desde_venta <= config.dias_max_devolucion:
            devolucion_permitida = True
        else:
            mensaje_devolucion = f"El período de {config.dias_max_devolucion} días para devoluciones ha expirado."

    resumen_credito = None
    if venta.tipo_pago == 'Credito':
        monto_capital_total = venta.monto_total - (venta.abono_inicial or 0)
        monto_intereses_total = sum(c.monto_interes for c in venta.plan_pagos)
        monto_total_credito = monto_capital_total + monto_intereses_total

        pagado_a_capital = 0
        pagado_a_interes = 0
        cuotas_pagadas = venta.plan_pagos.filter_by(estado='Pagada').all()
        for cuota in cuotas_pagadas:
            pagado_a_capital += cuota.monto_capital
            pagado_a_interes += cuota.monto_interes

        saldo_pendiente_credito = monto_total_credito - (pagado_a_capital + pagado_a_interes)

        resumen_credito = {
            'monto_capital_total': monto_capital_total,
            'monto_intereses_total': monto_intereses_total,
            'monto_total_credito': monto_total_credito,
            'pagado_a_capital': pagado_a_capital,
            'pagado_a_interes': pagado_a_interes,
            'saldo_pendiente_credito': saldo_pendiente_credito,
            'abono_inicial': (venta.abono_inicial or 0)
        }

    historial_devoluciones = venta.devoluciones.order_by(Devolucion.fecha_devolucion.asc()).all()

    return render_template('admin/ver_venta.html',
                           venta=venta,
                           pago_form=pago_form,
                           total_pagado=total_pagado,
                           pago_cuota_form=pago_cuota_form,
                           resumen_credito=resumen_credito,
                           devolucion_permitida=devolucion_permitida,
                           mensaje_devolucion=mensaje_devolucion,
                           historial_devoluciones=historial_devoluciones,
                           pagos_ordenados=pagos_ordenados,
                           productos_activos=productos_activos_en_venta)

@bp.route('/ventas/<int:id>/pagar', methods=['POST'])
def agregar_pago(id):
    venta = Venta.query.get_or_404(id)
    pago_form = PagoForm()

    if pago_form.validate_on_submit():
        monto_pago_actual = Decimal(pago_form.monto_pago.data)
        monto_total_venta = Decimal(venta.monto_total)

        total_pagado_anterior = Decimal(db.session.query(func.sum(Pago.monto_pago)).filter_by(venta_id=id).scalar() or 0)

        saldo_pendiente = monto_total_venta - total_pagado_anterior

        if monto_pago_actual > saldo_pendiente and not isclose(monto_pago_actual, saldo_pendiente):
            flash('El monto del pago no puede exceder el saldo pendiente.', 'danger')
        else:
            #Creamos el nuevo pago
            nuevo_pago = Pago(
                monto_pago=monto_pago_actual,
                metodo_pago=pago_form.metodo_pago.data,
                venta_id=venta.id
            )

            comprobante_file = pago_form.comprobante.data
            if comprobante_file:
                filename = secure_filename(f"{uuid.uuid4().hex}_{comprobante_file.filename}")
                upload_dir = os.path.join(current_app.static_folder, 'uploads', 'comprobantes')
                os.makedirs(upload_dir, exist_ok=True)
                filepath = os.path.join(upload_dir, filename)
                comprobante_file.save(filepath)
                nuevo_pago.comprobante_path = os.path.join('uploads', 'comprobantes', filename)

            db.session.add(nuevo_pago)

            nuevo_total_pagado = total_pagado_anterior + monto_pago_actual
            if nuevo_total_pagado >= monto_total_venta or isclose(nuevo_total_pagado, monto_total_venta):
                venta.estado = 'Pagada'

            db.session.commit()
            flash('Pago registrado exitosamente.', 'success')

    return redirect(url_for('admin.ver_venta', id=id))

@bp.route('/ventas/<int:id>/anular', methods=['POST'])
@admin_required
def anular_venta(id):
    venta = Venta.query.get_or_404(id)
    form = AnularVentaForm()

    if form.validate_on_submit():
        #Devolver el stock de los productos al inventario
        for item in venta.productos_asociados:
            producto = Producto.query.get(item.producto_id)
            if producto:
                producto.stock += item.cantidad

        #Marcar la venta como anulada
        venta.estado = 'Anulada'
        venta.motivo_anulacion = form.motivo_anulacion.data
        venta.anulada_por_id = current_user.id
        venta.fecha_anulacion = datetime.utcnow()

        db.session.commit()
        flash(f'Venta #{venta.id} ha sido anulada exitosamente.', 'success')
    else:
        flash('Es necesario proporcionar un motivo para la anulación.', 'danger')

    return redirect(url_for('admin.listar_ventas'))

@bp.route('/plan_pago/<int:cuota_id>/pagar', methods=['POST'])
@login_required
def pagar_cuota(cuota_id):
    cuota = PlanPago.query.get_or_404(cuota_id)
    venta = cuota.venta
    form = PagoCuotaForm()

    if form.validate_on_submit():
        monto_pagado = form.monto_pago.data
        monto_original_cuota = cuota.monto_total_cuota

        # Validar que el pago no sea mayor ni menor al valor de la cuota
        if not isclose(monto_pagado, monto_original_cuota):
            flash(f'El monto a pagar (${monto_pagado}) debe ser exactamente igual al valor de la cuota (${monto_original_cuota}).', 'danger')
            return redirect(url_for('admin.ver_venta', id=venta.id))

        # Crear el nuevo registro de pago
        nuevo_pago = Pago(
            monto_pago=monto_pagado,
            metodo_pago=form.metodo_pago.data,
            venta_id=venta.id
        )

        comprobante_file = form.comprobante.data
        if comprobante_file:
            filename = secure_filename(f"{uuid.uuid4().hex}_{comprobante_file.filename}")
            upload_dir = os.path.join(current_app.static_folder, 'uploads', 'comprobantes')
            os.makedirs(upload_dir, exist_ok=True)
            filepath = os.path.join(upload_dir, filename)
            comprobante_file.save(filepath)
            nuevo_pago.comprobante_path = os.path.join('uploads', 'comprobantes', filename)

        db.session.add(nuevo_pago)
        db.session.flush()

        # Actualizar el estado de la cuota y enlazarla al pago
        cuota.estado = 'Pagada'
        cuota.pago_id = nuevo_pago.id

        # Verificar si todas las cuotas ya están pagadas para actualizar la venta
        if all(c.estado == 'Pagada' for c in venta.plan_pagos):
            venta.estado = 'Pagada'

        db.session.commit()
        flash(f'Pago para la cuota #{cuota.numero_cuota} registrado exitosamente.', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error en el campo '{getattr(form, field).label.text}': {error}", 'danger')

    return redirect(url_for('admin.ver_venta', id=venta.id))

def _generar_imagen_weasyprint(html_string, output_path):
    try:
        #La URL base es necesaria para que WeasyPrint pueda encontrar archivos
        base_url = request.url_root
        html_doc = HTML(string=html_string, base_url=base_url)

        #CREAR REGLA CSS
        css_style = CSS(string='@page { size: A4; margin: 0; }')

        #GENERAR PDF EN MEMORIA
        pdf_in_memory = html_doc.write_pdf(stylesheets=[css_style])

        #CONVERTIR PDF A IMAGEN
        images = convert_from_bytes(pdf_in_memory)

        #GUARDAR LA IMAGEN
        if images:
            images[0].save(output_path, 'PNG')

    except Exception as e:
        current_app.logger.error(f"Error al generar imagen con WeasyPrint/pdf2image: {e}", exc_info=True)
        raise

@bp.route('/ventas/<int:id>/generar_recibo')
@login_required
def generar_recibo_venta(id):
    venta = Venta.query.get_or_404(id)
    pagos = venta.pagos.order_by(Pago.fecha_pago.asc()).all()
    total_pagado = db.session.query(func.sum(Pago.monto_pago)).filter_by(venta_id=id).scalar() or 0
    config = Configuracion.obtener_config()

    logo_url = None
    if config and config.logo_path:
        path_absoluto = os.path.join(current_app.static_folder, config.logo_path)
        logo_url = f"file://{path_absoluto}"

    #Lógica condicional para elegir la plantilla correcta
    if venta.tipo_pago == 'Credito':
        template_name = 'admin/receipts/estado_cuenta_template.html'
        document_name = f'estado_cuenta_venta_{venta.id}.png'
        flash_message = '¡Estado de cuenta generado exitosamente!'
    else:
        template_name = 'admin/receipts/receipt_template.html'
        document_name = f'recibo_venta_{venta.id}.png'
        flash_message = '¡Recibo en imagen generado exitosamente!'

    html_out = render_template(
        template_name,
        venta=venta,
        total_pagado=total_pagado,
        pagos=pagos,
        tienda_config=config,
        logo_url=logo_url,
        now=datetime.utcnow()
    )

    output_dir = os.path.join(current_app.static_folder, 'receipts')
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, document_name)

    try:
        _generar_imagen_weasyprint(html_out, filepath)
    except Exception as e:
        flash(f'Error al generar la imagen del documento: {e}', 'danger')
        current_app.logger.error(f"Error en generar_recibo_venta: {e}", exc_info=True)
        return redirect(url_for('admin.ver_venta', id=id))

    flash(flash_message, 'success')

    image_path = url_for('static', filename=os.path.join('receipts', document_name))
    timestamp = datetime.utcnow().timestamp()
    destination_url = f"{url_for('admin.ver_venta', id=id)}?generated_image_url={image_path}&v={timestamp}"

    return redirect(destination_url)

@bp.route('/ventas/<int:id>/generar_factura')
@login_required
def generar_factura_venta(id):
    venta = Venta.query.get_or_404(id)
    if venta.estado != 'Pagada':
        flash('Solo se pueden generar facturas finales para ventas pagadas.', 'warning')
        return redirect(url_for('admin.ver_venta', id=id))

    pagos = venta.pagos.order_by(Pago.fecha_pago.asc()).all()
    config = Configuracion.obtener_config()
    total_pagado = db.session.query(func.sum(Pago.monto_pago)).filter_by(venta_id=id).scalar() or 0

    logo_url = None
    if config and config.logo_path:
        path_absoluto = os.path.join(current_app.static_folder, config.logo_path)
        logo_url = f"file://{path_absoluto}"

    html_out = render_template(
        'admin/receipts/invoice_template.html',
        venta=venta,
        pagos=pagos,
        total_pagado=total_pagado,
        tienda_config=config,
        logo_url=logo_url,
        now=datetime.utcnow()
    )

    receipts_dir = os.path.join(current_app.static_folder, 'receipts')
    os.makedirs(receipts_dir, exist_ok=True)
    filename = f'factura_venta_{venta.id}.png'
    filepath = os.path.join(receipts_dir, filename)

    try:
        _generar_imagen_weasyprint(html_out, filepath)
    except Exception as e:
        flash(f'Error al generar la imagen de la factura: {e}', 'danger')
        current_app.logger.error(f"Error en generar_factura_venta: {e}", exc_info=True)
        return redirect(url_for('admin.ver_venta', id=id))

    flash('¡Factura final generada exitosamente!', 'success')

    image_path = url_for('static', filename=os.path.join('receipts', filename))
    timestamp = datetime.utcnow().timestamp()

    destination_url = f"{url_for('admin.ver_venta', id=id)}?generated_image_url={image_path}&v={timestamp}"

    return redirect(destination_url)

@bp.route('/ventas/<int:id>/generar_plan_pago')
@login_required
def generar_plan_pago(id):
    venta = Venta.query.get_or_404(id)
    if venta.tipo_pago != 'Credito':
        flash('Esta función solo está disponible para ventas a crédito.', 'warning')
        return redirect(url_for('admin.ver_venta', id=id))

    config = Configuracion.obtener_config()

    #Cálculos para el resumen
    monto_a_financiar = venta.monto_total - (venta.abono_inicial or 0)
    total_intereses = sum(cuota.monto_interes for cuota in venta.plan_pagos)
    valor_total_credito = monto_a_financiar + total_intereses
    tasa_interes = 0
    if venta.frecuencia_cuotas == 'Diaria':
        tasa_interes = config.interes_diario
    elif venta.frecuencia_cuotas == 'Semanal':
        tasa_interes = config.interes_semanal
    elif venta.frecuencia_cuotas == 'Mensual':
        tasa_interes = config.interes_mensual

    logo_url = None
    if config and config.logo_path:
        path_absoluto = os.path.join(current_app.static_folder, config.logo_path)
        logo_url = f"file://{path_absoluto}"

    html_out = render_template(
        'admin/credit/plan_pago_template.html',
        venta=venta,
        tienda_config=config,
        logo_url=logo_url,
        now=datetime.utcnow(),
        monto_a_financiar=monto_a_financiar,
        total_intereses=total_intereses,
        valor_total_credito=valor_total_credito,
        tasa_interes=tasa_interes
    )

    #Generación de la imagen
    output_dir = os.path.join(current_app.static_folder, 'credit_plans')
    os.makedirs(output_dir, exist_ok=True)
    filename = f'plan_pago_venta_{venta.id}.png'
    filepath = os.path.join(output_dir, filename)

    try:
        _generar_imagen_weasyprint(html_out, filepath)
    except Exception as e:
        flash(f'Error al generar la imagen del plan de pagos: {e}', 'danger')
        current_app.logger.error(f"Error en generar_plan_pago: {e}", exc_info=True)
        return redirect(url_for('admin.ver_venta', id=id))

    flash('¡Imagen del plan de pagos generada exitosamente!', 'success')

    #Redirigir de vuelta a la vista de la venta con la URL de la imagen para mostrarla
    image_path = url_for('static', filename=os.path.join('credit_plans', filename))
    timestamp = datetime.utcnow().timestamp()
    destination_url = f"{url_for('admin.ver_venta', id=id)}?generated_image_url={image_path}&v={timestamp}"

    return redirect(destination_url)


# -----------------------------------------------------------------------------
# --- RUTAS PARA GESTIÓN DE USUARIOS ---
# -----------------------------------------------------------------------------
@bp.route('/usuarios')
@admin_required
def listar_usuarios():
    usuarios = Usuario.query.order_by(Usuario.nombre).all()
    return render_template('admin/usuarios.html', usuarios=usuarios)

@bp.route('/usuarios/crear', methods=['GET', 'POST'])
@admin_required
def crear_usuario():
    form = UsuarioForm()
    form.password.validators.insert(0, DataRequired())
    form.password2.validators.insert(0, DataRequired())
    if form.validate_on_submit():
        if Usuario.query.filter_by(email=form.email.data).first():
            flash('Este email ya está registrado. Por favor, use otro.', 'danger')
        else:
            nuevo_usuario = Usuario(nombre=form.nombre.data, email=form.email.data, rol=form.rol.data)
            nuevo_usuario.set_password(form.password.data)
            db.session.add(nuevo_usuario)
            db.session.commit()
            flash('Usuario creado exitosamente.', 'success')
            return redirect(url_for('admin.listar_usuarios'))
    return render_template('admin/crear_editar_usuario.html', form=form, titulo='Crear Nuevo Usuario')

@bp.route('/usuarios/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def editar_usuario(id):
    usuario = Usuario.query.get_or_404(id)
    form = UsuarioForm(obj=usuario)
    if form.validate_on_submit():
        existing_user = Usuario.query.filter_by(email=form.email.data).first()
        if existing_user and existing_user.id != usuario.id:
            flash('Ese email ya está en uso por otro usuario.', 'danger')
        else:
            usuario.nombre = form.nombre.data
            usuario.email = form.email.data
            usuario.rol = form.rol.data
            if form.password.data:
                usuario.set_password(form.password.data)
            db.session.commit()
            flash('Usuario actualizado exitosamente.', 'success')
            return redirect(url_for('admin.listar_usuarios'))
    return render_template('admin/crear_editar_usuario.html', form=form, titulo='Editar Usuario')

@bp.route('/usuarios/eliminar/<int:id>', methods=['POST'])
@admin_required
def eliminar_usuario(id):
    usuario = Usuario.query.get_or_404(id)
    if usuario.id == current_user.id:
        flash('No puedes eliminar tu propia cuenta.', 'danger')
        return redirect(url_for('admin.listar_usuarios'))
    db.session.delete(usuario)
    db.session.commit()
    flash('Usuario eliminado exitosamente.', 'success')
    return redirect(url_for('admin.listar_usuarios'))


# -----------------------------------------------------------------------------
# --- RUTAS PARA TIPOS DE PRODUCTO Y ATRIBUTOS DINÁMICOS ---
# -----------------------------------------------------------------------------
@bp.route('/tipos-producto')
@admin_required
def listar_tipos_producto():
    tipos = TipoProducto.query.order_by(TipoProducto.nombre).all()
    form = TipoProductoForm()
    return render_template('admin/tipos_producto.html', tipos=tipos, form=form)

@bp.route('/tipos-producto/crear', methods=['GET', 'POST'])
@admin_required
def crear_tipo_producto():
    form = TipoProductoForm()
    if form.validate_on_submit():
        nuevo_tipo = TipoProducto(nombre=form.nombre.data)
        db.session.add(nuevo_tipo)
        db.session.commit()
        flash('Tipo de producto creado exitosamente.', 'success')
        return redirect(url_for('admin.detalle_tipo_producto', id=nuevo_tipo.id))
    return render_template('admin/crear_editar_tipo_producto.html', form=form, titulo='Crear Tipo de Producto')

@bp.route('/tipos-producto/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def editar_tipo_producto(id):
    tipo = TipoProducto.query.get_or_404(id)
    form = TipoProductoForm(obj=tipo)
    if form.validate_on_submit():
        tipo.nombre = form.nombre.data
        db.session.commit()
        flash('Tipo de producto actualizado exitosamente.', 'success')
        return redirect(url_for('admin.listar_tipos_producto'))
    return render_template('admin/crear_editar_tipo_producto.html', form=form, titulo='Editar Tipo de Producto')

@bp.route('/tipos-producto/eliminar/<int:id>', methods=['POST'])
@admin_required
def eliminar_tipo_producto(id):
    tipo = TipoProducto.query.get_or_404(id)
    if tipo.productos.first():
        flash('No se puede eliminar este tipo porque tiene productos asociados.', 'danger')
        return redirect(url_for('admin.listar_tipos_producto'))
    db.session.delete(tipo)
    db.session.commit()
    flash('Tipo de producto eliminado exitosamente.', 'success')
    return redirect(url_for('admin.listar_tipos_producto'))

@bp.route('/tipos-producto/<int:id>')
@admin_required
def detalle_tipo_producto(id):
    tipo = TipoProducto.query.get_or_404(id)
    atributo_form = AtributoForm()
    opcion_form = OpcionAtributoForm()
    return render_template('admin/detalle_tipo_producto.html', tipo=tipo, atributo_form=atributo_form, opcion_form=opcion_form)

@bp.route('/tipos-producto/<int:id>/atributos/crear', methods=['POST'])
@admin_required
def crear_atributo(id):
    tipo = TipoProducto.query.get_or_404(id)
    form = AtributoForm()
    if form.validate_on_submit():
        nuevo_atributo = Atributo(nombre_atributo=form.nombre_atributo.data, tipo_campo=form.tipo_campo.data, tipo_producto_id=tipo.id)
        db.session.add(nuevo_atributo)
        db.session.commit()
        flash(f'Atributo "{nuevo_atributo.nombre_atributo}" añadido.', 'success')
    return redirect(url_for('admin.detalle_tipo_producto', id=id))

@bp.route('/atributos/<int:id>/opciones/crear', methods=['POST'])
@admin_required
def crear_opcion_atributo(id):
    atributo = Atributo.query.get_or_404(id)
    form = OpcionAtributoForm()
    if form.validate_on_submit():
        nueva_opcion = OpcionAtributo(valor_opcion=form.valor_opcion.data, atributo_id=atributo.id)
        db.session.add(nueva_opcion)
        db.session.commit()
        flash(f'Opción "{nueva_opcion.valor_opcion}" añadida a {atributo.nombre_atributo}.', 'success')
    return redirect(url_for('admin.detalle_tipo_producto', id=atributo.tipo_producto_id))

@bp.route('/atributos/eliminar/<int:id>', methods=['POST'])
@admin_required
def eliminar_atributo(id):
    atributo = Atributo.query.get_or_404(id)
    tipo_producto_id = atributo.tipo_producto_id
    db.session.delete(atributo)
    db.session.commit()
    flash('Atributo eliminado.', 'success')
    return redirect(url_for('admin.detalle_tipo_producto', id=tipo_producto_id))

@bp.route('/opciones-atributo/eliminar/<int:id>', methods=['POST'])
@admin_required
def eliminar_opcion_atributo(id):
    opcion = OpcionAtributo.query.get_or_404(id)
    tipo_producto_id = opcion.atributo.tipo_producto_id
    db.session.delete(opcion)
    db.session.commit()
    flash('Opción eliminada.', 'success')
    return redirect(url_for('admin.detalle_tipo_producto', id=tipo_producto_id))


# -----------------------------------------------------------------------------
# --- RUTAS API ADICIONALES ---
# -----------------------------------------------------------------------------
@bp.route('/api/calcular-cuotas', methods=['POST'])
@login_required
def api_calcular_cuotas():
    data = request.get_json()
    monto_total = Decimal(data.get('monto_total', 0))
    abono_inicial = Decimal(data.get('abono_inicial', 0))
    numero_cuotas = int(data.get('numero_cuotas', 0))
    frecuencia = data.get('frecuencia', '')

    if monto_total <= 0 or numero_cuotas <= 0 or not frecuencia:
        return jsonify({'error': 'Datos incompletos'}), 400

    config = Configuracion.obtener_config()
    if not config:
        return jsonify({'error': 'Configuración de intereses no encontrada'}), 500

    plan = _calcular_plan_de_pagos(monto_total, abono_inicial, numero_cuotas, frecuencia, config)

    if not plan:
        return jsonify({'valor_cuota': 0, 'total_financiado': 0, 'total_interes': 0})

    valor_cuota = plan[0]['monto_total_cuota']
    total_financiado = sum(c['monto_total_cuota'] for c in plan)
    total_interes = sum(c['monto_interes'] for c in plan)

    return jsonify({
        'valor_cuota': float(valor_cuota),
        'total_financiado': float(total_financiado),
        'total_interes': float(total_interes)
    })


# -----------------------------------------------------------------------------
# --- RUTAS PARA DEVOLUCIONES ---
# -----------------------------------------------------------------------------
@bp.route('/ventas/<int:venta_id>/devolucion', methods=['GET', 'POST'])
@admin_required
def procesar_devolucion(venta_id):
    venta = Venta.query.get_or_404(venta_id)
    config = Configuracion.obtener_config()

    dias_desde_venta = (datetime.utcnow() - venta.fecha_venta).days
    if config and dias_desde_venta > config.dias_max_devolucion:
        flash(f"No se puede procesar la operación. El período de {config.dias_max_devolucion} días ha expirado.", 'danger')
        return redirect(url_for('admin.ver_venta', id=venta.id))

    if venta.estado not in ['Pagada', 'Credito', 'Con Devolucion']:
        flash('Solo se pueden procesar devoluciones o cambios de ventas ya finalizadas.', 'danger')
        return redirect(url_for('admin.ver_venta', id=venta.id))

    form = DevolucionForm()
    agregar_producto_form = AgregarProductoVentaForm()
    productos_disponibles = Producto.query.filter(Producto.stock > 0).order_by(Producto.nombre).all()
    opciones_productos = []
    for p in productos_disponibles:
        atributos_str = ", ".join(f"{val.atributo.nombre_atributo}: {val.valor}" for val in p.valores_atributos)
        texto_opcion = f"{p.nombre} ({atributos_str})" if atributos_str else p.nombre
        opciones_productos.append((p.id, texto_opcion))
    agregar_producto_form.producto.choices = opciones_productos

    #Crear un diccionario de datos para JavaScript
    product_data_for_js = {
        str(p.id): {
            'texto': opciones_productos[i][1],
            'precio': float(p.precio)
        } for i, p in enumerate(productos_disponibles)
    }

    if form.validate_on_submit():
        monto_total_devolucion = Decimal('0.0')
        productos_devueltos_data = []
        for i, producto_form in enumerate(form.productos):
            cantidad_a_devolver = producto_form.cantidad_a_devolver.data or 0
            if cantidad_a_devolver > 0:
                item_original = venta.productos_asociados[i]
                devoluciones_previas = db.session.query(func.sum(DevolucionProducto.cantidad_devuelta)).join(Devolucion).filter(
                    Devolucion.venta_id == venta.id,
                    DevolucionProducto.producto_id == item_original.producto_id
                ).scalar() or 0
                if cantidad_a_devolver > (item_original.cantidad - devoluciones_previas):
                    flash(f"Error: La cantidad a devolver para '{item_original.producto.nombre}' excede la cantidad restante.", 'danger')
                    return redirect(url_for('admin.procesar_devolucion', venta_id=venta.id))
                monto_total_devolucion += cantidad_a_devolver * item_original.precio_unitario
                productos_devueltos_data.append({'form_data': producto_form, 'item_original': item_original})

        monto_nuevo_cargo = Decimal('0.0')
        nuevos_productos_data = []
        nuevos_productos_ids = request.form.getlist('nuevo_producto_id')
        nuevas_cantidades = request.form.getlist('nueva_cantidad')
        for prod_id, cantidad_str in zip(nuevos_productos_ids, nuevas_cantidades):
            cantidad = int(cantidad_str)
            if cantidad > 0:
                producto = Producto.query.get(prod_id)
                monto_nuevo_cargo += producto.precio * cantidad
                nuevos_productos_data.append({'producto': producto, 'cantidad': cantidad})

        if not productos_devueltos_data and not nuevos_productos_data:
            flash('Debes devolver o añadir al menos un producto para procesar la operación.', 'warning')
            return redirect(url_for('admin.procesar_devolucion', venta_id=venta.id))

        balance = monto_nuevo_cargo - monto_total_devolucion

        if productos_devueltos_data:
            nueva_devolucion = Devolucion(venta_id=venta.id, motivo=form.motivo.data, monto_total_devolucion=monto_total_devolucion)
            db.session.add(nueva_devolucion)
            db.session.flush()
            for data in productos_devueltos_data:
                dev_prod = DevolucionProducto(devolucion_id=nueva_devolucion.id, producto_id=data['item_original'].producto_id, cantidad_devuelta=data['form_data'].cantidad_a_devolver.data, devuelto_al_stock=data['form_data'].devuelto_al_stock.data)
                if dev_prod.devuelto_al_stock:
                    producto = Producto.query.get(dev_prod.producto_id)
                    producto.stock += dev_prod.cantidad_devuelta
                db.session.add(dev_prod)

        if nuevos_productos_data:
            for data in nuevos_productos_data:
                asociacion = VentaProducto(venta_id=venta.id, producto_id=data['producto'].id, cantidad=data['cantidad'], precio_unitario=data['producto'].precio)
                db.session.add(asociacion)
                data['producto'].stock -= data['cantidad']

        if balance > 0:
            nuevo_pago = Pago(monto_pago=balance, metodo_pago=form.metodo_reembolso.data, venta_id=venta.id, fecha_pago=datetime.utcnow())
            db.session.add(nuevo_pago)
            flash(f'El cliente debe pagar una diferencia de ${balance:.2f}. Pago registrado.', 'success')
        elif balance < 0:
            monto_a_reembolsar = abs(balance)
            categoria_devoluciones = CategoriaGasto.query.filter_by(nombre='Devoluciones').first()
            if not categoria_devoluciones:
                categoria_devoluciones = CategoriaGasto(nombre='Devoluciones')
                db.session.add(categoria_devoluciones)
                db.session.flush()
            reembolso = Gasto(descripcion=f'Reembolso por devolución/cambio Venta #{venta.id}', monto=monto_a_reembolsar, categoria_id=categoria_devoluciones.id, usuario_id=current_user.id, fecha=datetime.utcnow())
            db.session.add(reembolso)
            flash(f'Se ha reembolsado al cliente ${monto_a_reembolsar:.2f}. Gasto registrado.', 'info')

        venta.monto_total += balance
        venta.estado = 'Con Devolucion'

        # En el futuro, aquí podría ir la lógica para recalcular el plan de pagos si es a crédito

        db.session.commit()

        flash('La operación de cambio/devolución se ha procesado exitosamente.', 'success')
        return redirect(url_for('admin.ver_venta', id=venta.id))

    if request.method == 'GET':
        while len(form.productos) > 0:
            form.productos.pop_entry()
        for item in venta.productos_asociados:
            devoluciones_previas = db.session.query(func.sum(DevolucionProducto.cantidad_devuelta)).join(Devolucion).filter(Devolucion.venta_id == venta.id, DevolucionProducto.producto_id == item.producto_id).scalar() or 0
            producto_form = DevolucionProductoForm()
            producto_form.producto_id = item.producto_id
            producto_form.cantidad_a_devolver = item.cantidad - devoluciones_previas
            form.productos.append_entry(producto_form)

    return render_template('admin/devolucion.html',
                           titulo='Procesar Devolución o Cambio',
                           venta=venta,
                           form=form,
                           agregar_producto_form=agregar_producto_form,
                           product_data=product_data_for_js)

@bp.route('/devoluciones')
@login_required
def listar_devoluciones():
    devoluciones = Devolucion.query.order_by(Devolucion.fecha_devolucion.desc()).all()
    return render_template('admin/devoluciones.html', devoluciones=devoluciones, titulo='Historial de Devoluciones')

@bp.route('/devoluciones/<int:id>')
@login_required
def ver_devolucion(id):
    devolucion = Devolucion.query.get_or_404(id)
    return render_template('admin/ver_devolucion.html', devolucion=devolucion, titulo=f'Detalle de Devolución #{devolucion.id}')
