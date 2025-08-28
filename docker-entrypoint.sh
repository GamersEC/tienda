#!/bin/sh

# Salir inmediatamente si un comando falla
set -e

echo "Aplicando migraciones de la base de datos..."
flask db upgrade

echo "Verificando/Creando usuario administrador por defecto..."
flask crear-admin-auto

echo "Iniciando el servidor Gunicorn..."
# exec "$@" permite que el comando que pones en el Dockerfile (CMD) se ejecute
# y se convierta en el proceso principal del contenedor.
exec "$@"