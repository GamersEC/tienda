from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from wtforms.validators import DataRequired
from app import db
from app.admin import bp
from app.utils.decorators import admin_required
from app.models.producto import Producto
from app.models.cliente import Cliente
from app.models.venta import Venta
from app.models.pago import Pago
from app.models.venta_producto import VentaProducto
from app.models.usuario import Usuario
from app.admin.forms import (ProductoForm, ClienteForm, VentaForm, PagoForm,
                             AgregarProductoVentaForm, EditarVentaForm, UsuarioForm)
from sqlalchemy import func


#Redirigir al login en caso de no estar autenticado
@bp.before_request
@login_required
def before_request():
    pass

# Ruta para mostrar todos los productos
@bp.route('/productos')
def listar_productos():
    productos = Producto.query.all()
    return render_template('admin/productos.html', productos=productos)


# Ruta para añadir un nuevo producto
@bp.route('/productos/crear', methods=['GET', 'POST'])
@admin_required
def crear_producto():
    form = ProductoForm()
    if form.validate_on_submit():
        nuevo_producto = Producto(
            nombre=form.nombre.data,
            descripcion=form.descripcion.data,
            precio=form.precio.data,
            talla=form.talla.data,
            color=form.color.data,
            stock=form.stock.data
        )
        db.session.add(nuevo_producto)
        db.session.commit()
        flash('¡Producto creado exitosamente!', 'success')
        return redirect(url_for('admin.listar_productos'))
    return render_template('admin/crear_editar_producto.html', form=form, titulo='Crear Nuevo Producto')

# Ruta para editar un producto existente
@bp.route('/productos/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def editar_producto(id):
    producto = Producto.query.get_or_404(id)
    form = ProductoForm(obj=producto) # Carga los datos del producto en el formulario
    if form.validate_on_submit():
        producto.nombre = form.nombre.data
        producto.descripcion = form.descripcion.data
        producto.precio = form.precio.data
        producto.talla = form.talla.data
        producto.color = form.color.data
        producto.stock = form.stock.data
        db.session.commit()
        flash('¡Producto actualizado exitosamente!', 'success')
        return redirect(url_for('admin.listar_productos'))
    return render_template('admin/crear_editar_producto.html', form=form, titulo='Editar Producto')

# Ruta para eliminar un producto
@bp.route('/productos/eliminar/<int:id>', methods=['POST'])
@admin_required
def eliminar_producto(id):
    producto = Producto.query.get_or_404(id)
    db.session.delete(producto)
    db.session.commit()
    flash('¡Producto eliminado exitosamente!', 'success')
    return redirect(url_for('admin.listar_productos'))


# --- RUTAS PARA CLIENTES ---

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
            email=form.email.data
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
        db.session.commit()
        flash('¡Cliente actualizado exitosamente!', 'success')
        return redirect(url_for('admin.listar_clientes'))
    return render_template('admin/crear_editar_cliente.html', form=form, titulo='Editar Cliente')

@bp.route('/clientes/eliminar/<int:id>', methods=['POST'])
@admin_required
def eliminar_cliente(id):
    cliente = Cliente.query.get_or_404(id)
    # Aquí podrías añadir lógica para verificar si el cliente tiene ventas asociadas
    # antes de permitir la eliminación. Por ahora, lo eliminamos directamente.
    db.session.delete(cliente)
    db.session.commit()
    flash('¡Cliente eliminado exitosamente!', 'success')
    return redirect(url_for('admin.listar_clientes'))


# --- RUTAS PARA VENTAS ---

@bp.route('/ventas')
def listar_ventas():
    ventas = Venta.query.order_by(Venta.fecha_venta.desc()).all()
    return render_template('admin/ventas.html', ventas=ventas)

@bp.route('/ventas/crear', methods=['GET', 'POST'])
def crear_venta():
    form = VentaForm()
    if form.validate_on_submit():
        nueva_venta = Venta(
            cliente_id=form.cliente.data.id,
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

    agregar_producto_form = AgregarProductoVentaForm()
    editar_venta_form = EditarVentaForm(obj=venta) # Carga las notas existentes

    # Llenar el campo de productos con aquellos que tienen stock
    agregar_producto_form.producto.query = Producto.query.filter(Producto.stock > 0).order_by(Producto.nombre).all()

    # Lógica para guardar las notas
    if editar_venta_form.validate_on_submit() and 'submit_notas' in request.form:
        venta.notas = editar_venta_form.notas.data
        db.session.commit()
        flash('Notas actualizadas.', 'success')
        return redirect(url_for('admin.editar_venta', id=id))

    # Lógica para añadir un producto
    if agregar_producto_form.validate_on_submit() and 'submit_producto' in request.form:
        producto = agregar_producto_form.producto.data
        cantidad = agregar_producto_form.cantidad.data

        if cantidad > producto.stock:
            flash(f'No hay suficiente stock para {producto.nombre}. Disponible: {producto.stock}', 'danger')
        else:
            asociacion = VentaProducto(
                venta_id=venta.id,
                producto_id=producto.id,
                cantidad=cantidad,
                precio_unitario=producto.precio
            )
            db.session.add(asociacion)
            producto.stock -= cantidad
            db.session.commit()
            flash(f'{producto.nombre} añadido a la venta.', 'success')

        return redirect(url_for('admin.editar_venta', id=id))

    # Recalcular el total
    total_calculado = db.session.query(func.sum(VentaProducto.precio_unitario * VentaProducto.cantidad)).filter_by(venta_id=id).scalar() or 0
    venta.monto_total = total_calculado
    db.session.commit()

    return render_template('admin/editar_venta.html', venta=venta,
                           agregar_producto_form=agregar_producto_form,
                           editar_venta_form=editar_venta_form)

@bp.route('/ventas/editar/<int:venta_id>/eliminar_producto/<int:producto_asociado_id>', methods=['POST'])
@admin_required
def eliminar_producto_venta(venta_id, producto_asociado_id):
    # Buscamos la asociación específica a eliminar
    asociacion = VentaProducto.query.get_or_404(producto_asociado_id)

    # Devolvemos el stock al producto original
    producto = Producto.query.get(asociacion.producto_id)
    producto.stock += asociacion.cantidad

    # Eliminamos la asociación y guardamos cambios
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

    # Calcular total pagado
    total_pagado = db.session.query(func.sum(Pago.monto_pago)).filter_by(venta_id=id).scalar() or 0

    return render_template('admin/ver_venta.html', venta=venta, pago_form=pago_form, total_pagado=total_pagado)

@bp.route('/ventas/<int:id>/pagar', methods=['POST'])
def agregar_pago(id):
    venta = Venta.query.get_or_404(id)
    pago_form = PagoForm()

    if pago_form.validate_on_submit():
        monto = pago_form.monto_pago.data

        # Calcular total pagado
        total_pagado = db.session.query(func.sum(Pago.monto_pago)).filter_by(venta_id=id).scalar() or 0

        if monto > (venta.monto_total - total_pagado):
            flash('El monto del pago no puede exceder el saldo pendiente.', 'danger')
        else:
            nuevo_pago = Pago(
                monto_pago=monto,
                metodo_pago=pago_form.metodo_pago.data,
                venta_id=venta.id
            )
            db.session.add(nuevo_pago)

            # Actualizar estado de la venta si se paga por completo
            if (total_pagado + monto) >= venta.monto_total:
                venta.estado = 'Pagada'

            db.session.commit()
            flash('Pago registrado exitosamente.', 'success')

    return redirect(url_for('admin.ver_venta', id=id))


# --- RUTAS PARA GESTIÓN DE USUARIOS ---

@bp.route('/usuarios')
@admin_required
def listar_usuarios():
    usuarios = Usuario.query.order_by(Usuario.nombre).all()
    return render_template('admin/usuarios.html', usuarios=usuarios)

@bp.route('/usuarios/crear', methods=['GET', 'POST'])
@admin_required
def crear_usuario():
    form = UsuarioForm()
    # Hacemos la contraseña obligatoria para usuarios nuevos
    form.password.validators.insert(0, DataRequired())
    form.password2.validators.insert(0, DataRequired())

    if form.validate_on_submit():
        # Verificar si el email ya existe
        if Usuario.query.filter_by(email=form.email.data).first():
            flash('Este email ya está registrado. Por favor, use otro.', 'danger')
        else:
            nuevo_usuario = Usuario(
                nombre=form.nombre.data,
                email=form.email.data,
                rol=form.rol.data
            )
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
        # Verificar si el nuevo email ya está en uso por OTRO usuario
        existing_user = Usuario.query.filter_by(email=form.email.data).first()
        if existing_user and existing_user.id != usuario.id:
            flash('Ese email ya está en uso por otro usuario.', 'danger')
        else:
            usuario.nombre = form.nombre.data
            usuario.email = form.email.data
            usuario.rol = form.rol.data
            # Solo actualizar la contraseña si el campo no está vacío
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