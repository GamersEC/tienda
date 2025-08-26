# 1. Usar una imagen oficial de Python como imagen base
FROM python:3.9-slim

# 2. Establece variables de entorno
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /app

# 3. Establecer el directorio de trabajo
WORKDIR /app

# 4. Copiar e instalar las dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiar el resto del código de la aplicación
COPY . .

# 6. Copia solo el entrypoint principal y dale permisos
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# 7. Exponer el puerto
EXPOSE 5000

# 8. Define el entrypoint
ENTRYPOINT ["docker-entrypoint.sh"]

# 9. Comando por defecto que ejecutará el entrypoint
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "manage:app"]