from app import create_app
from config import Config

#Pasa la clase Config al crear la aplicación
app = create_app(Config)

if __name__ == '__main__':
    app.run(host='0.0.0.0')