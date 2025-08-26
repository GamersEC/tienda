from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from app.auth import bp
from app.auth.forms import LoginForm
from app.models.usuario import Usuario

@bp.route('/login', methods=['GET', 'POST'])
def login():
    print("--- DEBUG: Petición recibida en la ruta /login ---", flush=True)

    if current_user.is_authenticated:
        return redirect(url_for('admin.listar_ventas'))
    print("--- DEBUG: A punto de instanciar LoginForm() ---", flush=True)

    try:
        form = LoginForm()
        print("--- DEBUG: LoginForm() instanciado exitosamente. ---", flush=True)
    except Exception as e:
        print(f"--- ERROR FATAL: Falló la creación de LoginForm(). Error: {e} ---", flush=True)
        return "Error interno al crear el formulario de login.", 500

    if form.validate_on_submit():
        user = Usuario.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Email o contraseña inválidos.', 'danger')
            return redirect(url_for('auth.login'))

        login_user(user, remember=form.remember_me.data)
        flash(f'¡Bienvenido de nuevo, {user.nombre}!', 'success')

        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('admin.listar_ventas')
        return redirect(next_page)
    print("--- DEBUG: A punto de llamar a render_template('login.html') ---", flush=True)

    return render_template('login.html', title='Iniciar Sesión', form=form)


@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))