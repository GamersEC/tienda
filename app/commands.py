import click
import os # <-- Importar el módulo 'os'
from flask.cli import with_appcontext
from app import db
from app.models.usuario import Usuario

# --- NUEVO COMANDO AUTOMÁTICO ---
@click.command(name='crear-admin-auto')
@with_appcontext
def crear_admin_auto():
    """Crea el usuario administrador por defecto desde variables de entorno."""
    email = os.environ.get('ADMIN_EMAIL')
    password = os.environ.get('ADMIN_PASSWORD')
    nombre = os.environ.get('ADMIN_NOMBRE')

    # Salir si no se han definido las variables de entorno
    if not all([email, password, nombre]):
        click.echo('Las variables de entorno ADMIN_EMAIL, ADMIN_PASSWORD y ADMIN_NOMBRE deben estar definidas.')
        return

    # Comprobar si el administrador ya existe
    if Usuario.query.filter_by(email=email).first():
        click.echo(f'El administrador con email {email} ya existe.')
        return

    # Crear el nuevo administrador
    admin = Usuario(nombre=nombre, email=email, rol='Administrador')
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()

    click.echo(f'Administrador "{nombre}" creado exitosamente con el email {email}.')

# --- COMANDO INTERACTIVO EXISTENTE ---
@click.command(name='crear-admin-manual') # <-- Cambiado el nombre para evitar confusión
@with_appcontext
def crear_admin_manual():
    """Crea un nuevo usuario administrador de forma interactiva."""
    nombre = click.prompt('Nombre del administrador')
    email = click.prompt('Email del administrador')
    password = click.prompt('Contraseña', hide_input=True, confirmation_prompt=True)

    if Usuario.query.filter_by(email=email).first():
        click.echo('Este email ya está registrado.')
        return

    admin = Usuario(nombre=nombre, email=email, rol='Administrador')
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()

    click.echo(f'Administrador {nombre} creado exitosamente.')

def init_app(app):
    app.cli.add_command(crear_admin_auto)
    app.cli.add_command(crear_admin_manual)