# 1. Usar la imagen oficial de Playwright, que ya tiene navegadores y dependencias
FROM mcr.microsoft.com/playwright/python:v1.37.0-focal

# 2. Establece variables de entorno
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /app

# 3. Establecer el directorio de trabajo
WORKDIR /app

# 4. Copiar e instalar las dependencias de Python
# La imagen base ya tiene Playwright, pip instalará el resto
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiar el resto del código de la aplicación
COPY . .

# 6. Copia el entrypoint y dale permisos
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# 7. Exponer el puerto
EXPOSE 5000

# 8. Define el entrypoint
ENTRYPOINT ["docker-entrypoint.sh"]

# 9. Comando por defecto
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "manage:app"]