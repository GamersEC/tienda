from app.models.configuracion import Configuracion

def inject_config():
    config = Configuracion.obtener_config()
    return dict(tienda_config=config)