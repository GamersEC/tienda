import os
from flask import render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, or_
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

#Importación de todos los Formularios
from app.admin.forms import (
    ClienteForm, VentaForm, PagoForm, AgregarProductoVentaForm,
    EditarVentaForm, UsuarioForm, TipoProductoForm, AtributoForm,
    OpcionAtributoForm, EmptyForm, AnularVentaForm, ConfiguracionForm
)


@bp.route('/configuracion', methods=['GET', 'POST'])
@admin_required
def configuracion_tienda():
    #Obtenemos la primera fila de configuración, o creamos una si no existe
    config = Configuracion.obtener_config()
    if not config:
        config = Configuracion()
        db.session.add(config)
        db.session.commit()

    form = ConfiguracionForm(obj=config)
    if form.validate_on_submit():
        config.nombre_tienda = form.nombre_tienda.data
        config.ruc = form.ruc.data
        config.telefono = form.telefono.data
        config.direccion = form.direccion.data
        config.email = form.email.data
        logo_file = form.logo.data

        if logo_file:
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
    #Consultas para las estadísticas
    #Ventas de Hoy
    hoy_inicio = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    ventas_hoy = Venta.query.filter(Venta.fecha_venta >= hoy_inicio).count()
    ingresos_hoy = db.session.query(func.sum(Venta.monto_total)).filter(Venta.fecha_venta >= hoy_inicio).scalar() or 0

    #Total de Clientes y Productos
    total_clientes = Cliente.query.count()
    total_productos = Producto.query.count()

    #Productos con bajo stock
    productos_bajo_stock = Producto.query.filter(Producto.stock <= 5).order_by(Producto.stock.asc()).limit(5).all()

    #Últimas 5 ventas registradas
    ultimas_ventas = Venta.query.order_by(Venta.fecha_venta.desc()).limit(5).all()

    return render_template('admin/dashboard.html',
                           ventas_hoy=ventas_hoy,
                           ingresos_hoy=ingresos_hoy,
                           total_clientes=total_clientes,
                           total_productos=total_productos,
                           productos_bajo_stock=productos_bajo_stock,
                           ultimas_ventas=ultimas_ventas,
                           titulo='Dashboard')

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

#La ruta 'editar_producto' se deja para una futura implementación
@bp.route('/productos/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def editar_producto(id):
    flash('La edición de productos con atributos dinámicos es una funcionalidad avanzada pendiente de implementación.', 'info')
    return redirect(url_for('admin.listar_productos'))

@bp.route('/productos/eliminar/<int:id>', methods=['POST'])
@admin_required
def eliminar_producto(id):
    producto = Producto.query.get_or_404(id)
    #También eliminamos las asociaciones de ventas para mantener la integridad
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
        flash('Venta iniciada. Ahora añade productos.', 'success')
        return redirect(url_for('admin.editar_venta', id=nueva_venta.id))

    return render_template('admin/crear_venta.html', form=form)

@bp.route('/ventas/editar/<int:id>', methods=['GET', 'POST'])
def editar_venta(id):
    venta = Venta.query.get_or_404(id)
    if venta.estado != 'En Proceso':
        flash('Esta venta ya está finalizada y no se puede modificar.', 'warning')
        return redirect(url_for('admin.ver_venta', id=id))

    anular_venta_form = AnularVentaForm()
    agregar_producto_form = AgregarProductoVentaForm()
    editar_venta_form = EditarVentaForm(obj=venta)
    productos_disponibles = Producto.query.filter(Producto.stock > 0).order_by(Producto.nombre).all()
    agregar_producto_form.producto.query = productos_disponibles
    stock_data = {str(p.id): p.stock for p in productos_disponibles}

    if request.method == 'POST':
        if 'submit_notas' in request.form and editar_venta_form.validate():
            venta.notas = editar_venta_form.notas.data
            db.session.commit()
            flash('Notas actualizadas.', 'success')
            return redirect(url_for('admin.editar_venta', id=id))

        if 'submit_producto' in request.form and agregar_producto_form.validate():
            producto = agregar_producto_form.producto.data
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

    total_calculado = db.session.query(func.sum(VentaProducto.precio_unitario * VentaProducto.cantidad)).filter_by(venta_id=id).scalar() or 0
    venta.monto_total = total_calculado
    db.session.commit()

    return render_template('admin/editar_venta.html', venta=venta,
                           agregar_producto_form=agregar_producto_form,
                           editar_venta_form=editar_venta_form,
                           stock_data=stock_data,
                           anular_venta_form=anular_venta_form)

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
    venta = Venta.query.get_or_404(id)
    if venta.productos_asociados:
        venta.estado = 'Pendiente'
        db.session.commit()
        flash('Venta finalizada. Ahora está pendiente de pago.', 'success')
    else:
        flash('No se puede finalizar una venta sin productos.', 'danger')
    return redirect(url_for('admin.ver_venta', id=id))

@bp.route('/ventas/<int:id>')
def ver_venta(id):
    venta = Venta.query.get_or_404(id)
    pago_form = PagoForm()
    total_pagado = db.session.query(func.sum(Pago.monto_pago)).filter_by(venta_id=id).scalar() or 0
    return render_template('admin/ver_venta.html', venta=venta, pago_form=pago_form, total_pagado=total_pagado)

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

    html_out = render_template(
        'admin/receipts/receipt_template.html',
        venta=venta,
        total_pagado=total_pagado,
        pagos=pagos,
        tienda_config=config,
        logo_url=logo_url
    )

    receipts_dir = os.path.join(current_app.static_folder, 'receipts')
    os.makedirs(receipts_dir, exist_ok=True)
    filename = f'recibo_venta_{venta.id}.png'
    filepath = os.path.join(receipts_dir, filename)

    try:
        _generar_imagen_weasyprint(html_out, filepath)
    except Exception as e:
        flash(f'Error al generar la imagen del recibo: {e}', 'danger')
        current_app.logger.error(f"Error en generar_recibo_venta: {e}", exc_info=True)
        return redirect(url_for('admin.ver_venta', id=id))

    flash('¡Recibo en imagen generado exitosamente!', 'success')

    image_path = url_for('static', filename=os.path.join('receipts', filename))
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