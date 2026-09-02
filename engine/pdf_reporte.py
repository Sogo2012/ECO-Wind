"""Reporte PDF de la ficha de especificación técnica (Hallazgo 49).

Usa reportlab (puro Python, sin binarios del sistema) para generar un PDF con el
mismo contenido que la pestaña "Especificación Técnica" de app.py, en tono
corporativo ECO (colores exactos del libro de marca) para que el cliente se lo
pueda llevar impreso o por correo después de la reunión.

Nota de alcance: usa las tipografías estándar de reportlab (Helvetica), NO
Montserrat/Dosis -- esas son fuentes de pago y embeberlas en el PDF requiere
archivos .ttf que hoy no están en el repositorio. Los COLORES sí son los
exactos de marca. Pendiente si se consigue el archivo .ttf real de Montserrat.
"""
import io
from datetime import date

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

AZUL = colors.HexColor("#173D4A")
VERDE = colors.HexColor("#66913E")
GRIS = colors.HexColor("#414549")
FONDO_TABLA = colors.HexColor("#F0F2F6")


def _estilos():
    base = getSampleStyleSheet()
    estilos = {
        "titulo": ParagraphStyle(
            "titulo", parent=base["Title"], textColor=AZUL, fontName="Helvetica-Bold",
            fontSize=18, spaceAfter=2,
        ),
        "subtitulo": ParagraphStyle(
            "subtitulo", parent=base["Normal"], textColor=GRIS, fontName="Helvetica",
            fontSize=10, spaceAfter=10,
        ),
        "seccion": ParagraphStyle(
            "seccion", parent=base["Heading2"], textColor=AZUL, fontName="Helvetica-Bold",
            fontSize=13, spaceBefore=14, spaceAfter=6,
        ),
        "equipo": ParagraphStyle(
            "equipo", parent=base["Heading3"], textColor=GRIS, fontName="Helvetica-Bold",
            fontSize=11, spaceBefore=8, spaceAfter=2,
        ),
        "cuerpo": ParagraphStyle(
            "cuerpo", parent=base["Normal"], textColor=GRIS, fontName="Helvetica",
            fontSize=9.5, leading=13,
        ),
        "pie": ParagraphStyle(
            "pie", parent=base["Normal"], textColor=GRIS, fontName="Helvetica",
            fontSize=7.5, alignment=TA_CENTER,
        ),
    }
    return estilos


_estilo_celda = ParagraphStyle(
    "celda_tabla", fontName="Helvetica", fontSize=9, textColor=GRIS, leading=11,
    wordWrap="CJK",  # CJK envuelve incluso una cadena larga sin espacios (ej. nombre de un EPW)
)
_estilo_celda_header = ParagraphStyle(
    "celda_tabla_header", parent=_estilo_celda, fontName="Helvetica-Bold", textColor=colors.white,
)


def _celda(valor):
    return Paragraph(str(valor), _estilo_celda)


def _tabla_specs(filas):
    """Tabla de 2 columnas (Especificación / Valor) con el mismo tono que la app -- los
    valores van en Paragraph (no texto plano) para que un dato largo sin espacios (ej. el
    nombre de un archivo EPW subido) envuelva dentro de la columna en vez de desbordar el
    margen de la página (encontrado probando el flujo real de subir un EPW, Hallazgo 49)."""
    data = [[Paragraph("Especificación", _estilo_celda_header), Paragraph("Valor", _estilo_celda_header)]]
    data += [[_celda(f), _celda(v)] for f, v in filas]
    t = Table(data, colWidths=[7 * cm, 8.5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, FONDO_TABLA]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def generar_pdf_especificacion(datos, logo_path=None):
    """Arma el PDF completo a partir del dict `datos` (ver estructura abajo) y
    devuelve los bytes ya listos para st.download_button.

    Estructura esperada de `datos`:
      {
        "sitio_nombre": str, "potencia_pico_kw": float, "energia_anual_kwh": float,
        "elevacion_m": float, "voltaje_bus_v": float,
        "turbinas": [{"nombre", "cantidad", "numero_parte", "filas": [(campo, valor), ...],
                       "imagen": ruta_o_None}, ...],
        "inversor": {"nombre", "fabricante", "filas": [...]} o None,
        "inversor_no_compatible_msg": str o None,
        "bess": [{"nombre", "fabricante", "filas": [...]}, ...],
      }
    """
    estilos = _estilos()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=1.8 * cm, rightMargin=1.8 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        title="Especificación Técnica -- ECO | Wind",
    )
    story = []

    if logo_path:
        try:
            img = Image(logo_path, width=3.6 * cm, height=1.6 * cm, kind="proportional")
            story.append(img)
        except Exception:
            pass

    story.append(Spacer(1, 6))
    story.append(Paragraph("Especificación Técnica del Sistema", estilos["titulo"]))
    story.append(Paragraph(
        f"ECO | Wind -- Simulador de microgeneración eólica -- generado el "
        f"{date.today().strftime('%d/%m/%Y')}",
        estilos["subtitulo"],
    ))
    story.append(HRFlowable(width="100%", thickness=1.2, color=VERDE, spaceAfter=10))

    story.append(Paragraph("Datos generales del sistema", estilos["seccion"]))
    story.append(_tabla_specs([
        ("Sitio", datos["sitio_nombre"]),
        ("Potencia pico instalada", f"{datos['potencia_pico_kw']:.2f} kW"),
        ("Energía anual estimada", f"{datos['energia_anual_kwh']:,.0f} kWh/año"),
        ("Elevación del sitio", f"{datos['elevacion_m']:.0f} m"),
    ]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"<b>Arquitectura eléctrica:</b> bus de corriente continua a "
        f"{datos['voltaje_bus_v']}V -- cada turbina entrega su salida a través de un "
        "controlador individual de fábrica; todos los controladores se conectan en "
        "paralelo al mismo bus, que alimenta directamente el puerto de batería del "
        "inversor (no el puerto solar/MPPT).",
        estilos["cuerpo"],
    ))

    story.append(Paragraph("Turbinas eólicas", estilos["seccion"]))
    for t in datos["turbinas"]:
        story.append(Paragraph(f"{t['nombre']} -- cantidad: {t['cantidad']}", estilos["equipo"]))
        story.append(Paragraph(
            f"Fabricante: Flower Turbines -- N° de parte: {t['numero_parte']}", estilos["cuerpo"]
        ))
        story.append(Spacer(1, 3))
        story.append(_tabla_specs(t["filas"]))
        story.append(Spacer(1, 6))

    story.append(Paragraph("Inversor", estilos["seccion"]))
    if datos.get("inversor"):
        inv = datos["inversor"]
        story.append(Paragraph(inv["nombre"], estilos["equipo"]))
        story.append(Paragraph(f"Fabricante: {inv['fabricante']}", estilos["cuerpo"]))
        story.append(Spacer(1, 3))
        story.append(_tabla_specs(inv["filas"]))
    else:
        story.append(Paragraph(
            datos.get("inversor_no_compatible_msg")
            or "No se encontró un inversor residencial compatible con este arreglo.",
            estilos["cuerpo"],
        ))

    story.append(Paragraph("Banco de baterías (BESS)", estilos["seccion"]))
    if datos["bess"]:
        for b in datos["bess"]:
            story.append(Paragraph(b["nombre"], estilos["equipo"]))
            story.append(Paragraph(f"Fabricante: {b['fabricante']}", estilos["cuerpo"]))
            story.append(Spacer(1, 3))
            story.append(_tabla_specs(b["filas"]))
            story.append(Spacer(1, 6))
    else:
        story.append(Paragraph("No aplica.", estilos["cuerpo"]))

    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#CBD5E0"), spaceAfter=6))
    story.append(Paragraph(
        "Fuente de los datos: fichas técnicas oficiales de fábrica (Flower Turbines, Sol-Ark) "
        "y datasheets de distribuidor (EG4). ECO Consultor -- Energy Conservation Opportunities.",
        estilos["pie"],
    ))

    doc.build(story)
    return buffer.getvalue()
