# 1. Usar una imagen oficial de Python, ligera y optimizada (basada en Debian)
FROM python:3.12-slim-bookworm

# 2. Establecer variables de entorno para un funcionamiento óptimo de Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /app

# 3. Actualizar el sistema e instalar dependencias
# Se instalan dependencias para WeasyPrint, psycopg2 Y pdf2image
RUN apt-get update && apt-get install -y \
    # Dependencias de WeasyPrint
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    # Dependencias para compilar psycopg2
    gcc \
    python3-dev \
    libpq-dev \
    # Dependencia para pdf2image
    poppler-utils \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# 4. Establecer el directorio de trabajo
WORKDIR /app

# 5. Copiar e instalar las dependencias de Python
# Se copia solo requirements.txt primero para aprovechar el caché de Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copiar el resto del código de la aplicación
COPY . .

# 7. Copia el entrypoint y dale permisos de ejecución
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# 8. Exponer el puerto que usará Gunicorn
EXPOSE 5000

# 9. Define el entrypoint que se ejecutará al iniciar el contenedor
ENTRYPOINT ["docker-entrypoint.sh"]

# 10. Comando por defecto que se pasa al entrypoint
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "manage:app"]