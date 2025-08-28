import os
from PIL import Image, ImageDraw, ImageFont
from flask import current_app
from app.models.pago import Pago

def generate_receipt_image(venta, total_pagado):
    width, height = 800, 1200
    background_color = (255, 255, 255)
    font_color = (50, 50, 50)
    primary_color = (13, 110, 253)

    img = Image.new('RGB', (width, height), color=background_color)
    draw = ImageDraw.Draw(img)

    try:
        font_bold_path = os.path.join(current_app.static_folder, 'fonts', 'DejaVuSans-Bold.ttf')
        font_reg_path = os.path.join(current_app.static_folder, 'fonts', 'DejaVuSans.ttf')
        font_h1 = ImageFont.truetype(font_bold_path, 42)
        font_h2 = ImageFont.truetype(font_bold_path, 28)
        font_body_bold = ImageFont.truetype(font_bold_path, 20)
        font_body = ImageFont.truetype(font_reg_path, 20)
        font_small = ImageFont.truetype(font_reg_path, 16)
    except IOError:
        print("ADVERTENCIA: Fuentes personalizadas no encontradas. El diseño puede no ser óptimo.")
        font_h1 = ImageFont.load_default()
        font_h2 = ImageFont.load_default()
        font_body_bold = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # --- DIBUJAR EL CONTENIDO ---
    margin = 50
    y_pos = 50

    draw.text((margin, y_pos), "Detalle de Venta", font=font_h1, fill=primary_color)
    draw.text((width - margin - 250, y_pos + 10), f"Venta #{venta.id}", font=font_h2, fill=font_color)
    y_pos += 80

    draw.text((margin, y_pos), "Cliente:", font=font_body_bold, fill=font_color)
    draw.text((margin + 100, y_pos), f"{venta.cliente.nombre} {venta.cliente.apellido or ''}", font=font_body, fill=font_color)
    draw.text((width - margin - 250, y_pos), f"Fecha: {venta.fecha_venta.strftime('%Y-%m-%d')}", font=font_body, fill=font_color)
    y_pos += 40
    draw.line([(margin, y_pos), (width - margin, y_pos)], fill=(220, 220, 220), width=2)
    y_pos += 20

    draw.text((margin, y_pos), "Resumen de Productos", font=font_h2, fill=font_color)
    y_pos += 40
    for item in venta.productos_asociados:
        subtotal = item.cantidad * item.precio_unitario
        line_item = f"{item.cantidad}x {item.producto.nombre} (@ ${item.precio_unitario:.2f})"
        draw.text((margin, y_pos), line_item, font=font_body, fill=font_color)
        draw.text((width - margin - 100, y_pos), f"${subtotal:.2f}", font=font_body, fill=font_color, anchor="ra")
        y_pos += 30

    y_pos += 10
    draw.line([(margin, y_pos), (width - margin, y_pos)], fill=(220, 220, 220), width=2)
    y_pos += 20

    draw.text((margin, y_pos), "Historial de Pagos", font=font_h2, fill=font_color)
    y_pos += 40
    pagos = venta.pagos.order_by(Pago.fecha_pago.asc()).all()
    if pagos:
        for pago in pagos:
            line_pago = f"Pago ({pago.metodo_pago}) - {pago.fecha_pago.strftime('%Y-%m-%d')}"
            draw.text((margin, y_pos), line_pago, font=font_body, fill=font_color)
            draw.text((width - margin - 100, y_pos), f"${pago.monto_pago:.2f}", font=font_body, fill=(0, 128, 0), anchor="ra")
            y_pos += 30
    else:
        draw.text((margin, y_pos), "Aún no se han registrado pagos.", font=font_body, fill=(150, 150, 150))
        y_pos += 30

    y_pos += 20
    draw.line([(margin, y_pos), (width - margin, y_pos)], fill=(220, 220, 220), width=2)
    y_pos += 30

    saldo_pendiente = venta.monto_total - total_pagado
    draw.text((width - margin - 250, y_pos), "Total Venta:", font=font_body_bold, fill=font_color, anchor="ra")
    draw.text((width - margin - 100, y_pos), f"${venta.monto_total:.2f}", font=font_body, fill=font_color, anchor="ra")
    y_pos += 35
    draw.text((width - margin - 250, y_pos), "Total Pagado:", font=font_body_bold, fill=(0, 128, 0), anchor="ra")
    draw.text((width - margin - 100, y_pos), f"${total_pagado:.2f}", font=font_body, fill=(0, 128, 0), anchor="ra")
    y_pos += 35
    draw.text((width - margin - 250, y_pos), "Saldo Pendiente:", font=font_h2, fill=(255, 0, 0), anchor="ra")
    draw.text((width - margin - 100, y_pos), f"${saldo_pendiente:.2f}", font=font_h2, fill=(255, 0, 0), anchor="ra")
    y_pos += 80

    draw.text((margin, y_pos), "¡Gracias por su confianza!", font=font_body_bold, fill=primary_color)

    receipts_dir = os.path.join(current_app.static_folder, 'receipts')
    os.makedirs(receipts_dir, exist_ok=True)
    filename = f'recibo_venta_{venta.id}.png'
    filepath = os.path.join(receipts_dir, filename)
    img.save(filepath)

    return os.path.join('receipts', filename)