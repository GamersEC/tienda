from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from app.auth import bp
from app.auth.forms import LoginForm
from app.models.usuario import Usuario
from app import db
from datetime import datetime, timedelta

#Constantes de seguridad
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_PERIOD_MINUTES = 15

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))

    form = LoginForm()

    if form.validate_on_submit():
        user = Usuario.query.filter_by(email=form.email.data).first()

        #Verificar si el usuario no existe
        if not user:
            flash('Email o contraseña inválidos.', 'danger')
            return redirect(url_for('auth.login'))

        #Verificar si la cuenta está actualmente bloqueada
        if user.lockout_until and user.lockout_until > datetime.utcnow():
            remaining_time = user.lockout_until - datetime.utcnow()
            minutes = int(remaining_time.total_seconds() / 60)
            flash(f'Demasiados intentos fallidos. Su cuenta está bloqueada temporalmente. '
                  f'Por favor, intente de nuevo en {minutes+1} minutos.', 'warning')
            return redirect(url_for('auth.login'))

        #Verificar si la contraseña es correcta
        if user.check_password(form.password.data):
            #Si el login es exitoso, resetear los contadores y loguear al usuario
            user.failed_login_attempts = 0
            user.lockout_until = None
            db.session.commit()

            login_user(user, remember=form.remember_me.data)
            flash(f'¡Bienvenido de nuevo, {user.nombre}!', 'success')

            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('admin.dashboard')
            return redirect(next_page)
        else:
            #Si el login falla, incrementar el contador y potencialmente bloquear la cuenta
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
                user.lockout_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_PERIOD_MINUTES)
                user.failed_login_attempts = 0 # Resetear contador tras bloqueo
                flash('Ha excedido el número máximo de intentos de inicio de sesión. '
                      'Su cuenta ha sido bloqueada por 15 minutos.', 'danger')
            else:
                flash('Email o contraseña inválidos.', 'danger')

            db.session.commit()
            return redirect(url_for('auth.login'))

    return render_template('login.html', title='Iniciar Sesión', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))