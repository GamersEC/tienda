#!/bin/sh

set -e

echo "Aplicando migraciones de la base de datos..."
flask db upgrade

echo "Verificando/Creando usuario administrador por defecto..."
flask crear-admin-auto

echo "Iniciando el servidor Gunicorn..."

exec "$@"