"""Reportes PDF de la app.

Usa reportlab (puro Python, sin binarios del sistema) para generar PDFs en tono
corporativo ECO (colores exactos del libro de marca) para que se puedan llevar
impresos o por correo a una reunión con cliente.

Nota de alcance: usa las tipografías estándar de reportlab (Helvetica), NO
Montserrat/Dosis -- esas son fuentes de pago y embeberlas en el PDF requiere
archivos .ttf que hoy no están en el repositorio. Los COLORES sí son los
exactos de marca. Pendiente si se consigue el archivo .ttf real de Montserrat.
"""
import io
import math
import os
from datetime import date

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable, PageBreak,
    KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from engine.turbine_specs import SPECS_TURBINAS, RUTA_IMAGEN
from engine.price_calculator import (
    COSTO_FLETE_UNIDAD_USD, COSTO_FLETE_PALLET_USD, COSTO_FLETE_CONTENEDOR_USD,
    LIMITE_PESO_UNIDAD_KG, LIMITE_PESO_PALLET_KG, LIMITE_PESO_CONTENEDOR_KG,
    MARGIN_PCT,
)
from engine.i18n import tr, tr_modo_tarifa

AZUL = colors.HexColor("#173D4A")
VERDE = colors.HexColor("#66913E")
GRIS = colors.HexColor("#414549")
AMBAR = colors.HexColor("#B7791F")
FONDO_TABLA = colors.HexColor("#F0F2F6")
FONDO_KPI = colors.HexColor("#F4F6F8")
FONDO_INFO = colors.HexColor("#E8F0F3")
ANCHO_UTIL = letter[0] - 2 * 1.8 * cm


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
        "intro": ParagraphStyle(
            "intro", parent=base["Normal"], textColor=GRIS, fontName="Helvetica",
            fontSize=10.5, leading=15, spaceAfter=10,
        ),
        "kpi_valor": ParagraphStyle(
            "kpi_valor", parent=base["Normal"], textColor=AZUL, fontName="Helvetica-Bold",
            fontSize=17, alignment=TA_CENTER, leading=20,
        ),
        "kpi_label": ParagraphStyle(
            "kpi_label", parent=base["Normal"], textColor=GRIS, fontName="Helvetica",
            fontSize=8, alignment=TA_CENTER, leading=10,
        ),
        "img_caption": ParagraphStyle(
            "img_caption", parent=base["Normal"], textColor=GRIS, fontName="Helvetica-Oblique",
            fontSize=8.5, alignment=TA_CENTER, spaceBefore=2, spaceAfter=8,
        ),
        "info_box": ParagraphStyle(
            "info_box", parent=base["Normal"], textColor=AZUL, fontName="Helvetica",
            fontSize=9.5, leading=13,
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


def _tabla_specs(filas, idioma):
    """Tabla de 2 columnas (Especificación / Valor) con el mismo tono que la app -- los
    valores van en Paragraph (no texto plano) para que un dato largo sin espacios (ej. el
    nombre de un archivo EPW subido) envuelva dentro de la columna en vez de desbordar el
    margen de la página (encontrado probando el flujo real de subir un EPW)."""
    data = [[
        Paragraph(tr("pdf_tabla_header_especificacion", idioma), _estilo_celda_header),
        Paragraph(tr("pdf_tabla_header_valor", idioma), _estilo_celda_header),
    ]]
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


def _kpi_card(label, valor, accent=VERDE, ancho=4.0 * cm):
    """Una 'tarjeta' de KPI -- número grande + etiqueta chica, con una franja de color
    arriba. Reportlab no tiene bordes redondeados nativos; el efecto de tarjeta sale de
    fondo gris claro + franja de acento + padding generoso."""
    estilos = _estilos()
    inner = Table(
        [[Paragraph(str(valor), estilos["kpi_valor"])],
         [Paragraph(str(label), estilos["kpi_label"])]],
        colWidths=[ancho],
    )
    inner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), FONDO_KPI),
        ("LINEABOVE", (0, 0), (-1, 0), 2.5, accent),
        ("TOPPADDING", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
        ("TOPPADDING", (0, 1), (-1, 1), 0),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    return inner


def _fila_kpis(cards):
    """Una fila de tarjetas de KPI, centradas y con aire entre ellas."""
    ancho_card = ANCHO_UTIL / len(cards)
    t = Table([cards], colWidths=[ancho_card] * len(cards))
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


def _imagen_png(png_bytes, ancho, alto):
    """Imagen a partir de bytes PNG en memoria (gráficos Plotly exportados vía kaleido),
    con `kind='proportional'` para que nunca se deforme sea cual sea su relación de
    aspecto real."""
    return Image(io.BytesIO(png_bytes), width=ancho, height=alto, kind="proportional")


def _fila_imagenes(imgs_con_leyenda):
    """Una o dos imágenes lado a lado (gráficos), cada una con su leyenda chica debajo.
    `imgs_con_leyenda`: lista de (png_bytes, leyenda_str)."""
    estilos = _estilos()
    n = len(imgs_con_leyenda)
    ancho_col = ANCHO_UTIL / n
    fila_imgs, fila_leyendas = [], []
    for png_bytes, leyenda in imgs_con_leyenda:
        fila_imgs.append(_imagen_png(png_bytes, ancho_col - 0.3 * cm, 7.5 * cm))
        fila_leyendas.append(Paragraph(leyenda, estilos["img_caption"]))
    t = Table([fila_imgs, fila_leyendas], colWidths=[ancho_col] * n)
    t.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, 0), "BOTTOM"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _caja_info(texto, color_fondo=FONDO_INFO, color_borde=AZUL):
    """Caja destacada de una nota informativa/accionable -- NO para disculpas de alcance,
    para indicarle al lector qué falta cargar en la app para completar una sección."""
    estilos = _estilos()
    t = Table([[Paragraph(texto, estilos["info_box"])]], colWidths=[ANCHO_UTIL])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color_fondo),
        ("LINEBEFORE", (0, 0), (0, -1), 3, color_borde),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    return t


def _tabla_produccion(filas, idioma):
    """Tabla de producción por clúster: Modelo / N / Buje / kWh-año / V. media / % bajo cut-in."""
    encabezados = [
        tr("pdf_prod_header_modelo", idioma),
        tr("pdf_prod_header_n", idioma),
        tr("pdf_prod_header_buje", idioma),
        tr("pdf_prod_header_kwh_anio", idioma),
        tr("pdf_prod_header_v_media_buje", idioma),
        tr("pdf_prod_header_pct_cutin", idioma),
    ]
    data = [[Paragraph(h, _estilo_celda_header) for h in encabezados]]
    data += [[_celda(v) for v in fila] for fila in filas]
    t = Table(data, colWidths=[5.2 * cm, 1.4 * cm, 2.0 * cm, 2.6 * cm, 3.4 * cm, 2.8 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, FONDO_TABLA]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def _pie_pagina(canvas, doc, idioma):
    """Callback de reportlab (onFirstPage/onLaterPages): franja superior de marca +
    pie con número de página, dibujado en cada página del informe."""
    canvas.saveState()
    ancho_pagina, alto_pagina = letter
    canvas.setFillColor(AZUL)
    canvas.rect(0, alto_pagina - 0.35 * cm, ancho_pagina, 0.35 * cm, stroke=0, fill=1)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GRIS)
    canvas.drawString(1.8 * cm, 1.0 * cm, tr("pdf_pie_copyright", idioma, anio=date.today().year))
    canvas.drawCentredString(ancho_pagina / 2, 1.0 * cm, tr("pdf_meta_titulo_informe", idioma))
    canvas.drawRightString(ancho_pagina - 1.8 * cm, 1.0 * cm, tr("pdf_pie_numero_pagina", idioma, n=doc.page))
    canvas.restoreState()


def generar_pdf_informe_ejecutivo(datos, logo_path=None, idioma="es"):
    """Arma el informe ejecutivo completo (portada con KPIs, contexto climático,
    equipos y producción, análisis financiero) a partir del dict `datos` y devuelve los
    bytes ya listos para st.download_button. Pensado para imprimir/exportar y llevar
    a una reunión con cliente -- "efecto wow": KPIs grandes en tarjetas, gráficos de
    la app embebidos como imagen, y una franja de marca en cada página.

    `idioma`: "es" o "en" -- selecciona el idioma de todo el texto del informe
    (título, KPIs, secciones, tablas y pie de página), vía engine.i18n.tr().

    Estructura esperada de `datos`:
      {
        "sitio_nombre": str, "fecha_generado": str,
        "potencia_pico_kw": float, "energia_anual_kwh": float, "elevacion_m": float,
        "n_turbinas_total": int, "voltaje_bus_v": float,
        "clima": {"fuente_texto": str, "media_viento_ms": float,
                   "img_rosa": png_bytes, "img_heatmap": png_bytes o None,
                   "img_perfil": png_bytes},
        "turbinas": [{"nombre", "cantidad", "numero_parte", "filas": [(campo, valor), ...]}, ...],
        "produccion": {"filas_tabla": [(modelo, n, buje, kwh, v_media, pct_cutin), ...],
                        "correccion_densidad_pct": float,
                        "img_mensual": png_bytes, "img_duracion": png_bytes},
        "financiero": None o {
          "capex": float, "payback_years": float o None, "roi_percentage": float o None,
          "npv_usd": float o None, "ahorro_anual_USD": float, "mantenimiento_anual_USD": float,
          "viable": bool, "modo_tarifa": str, "vida_util_anos": int, "tasa_descuento_pct": float,
        },
      }
    """
    estilos = _estilos()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=1.8 * cm, rightMargin=1.8 * cm, topMargin=1.8 * cm, bottomMargin=1.8 * cm,
        title=tr("pdf_meta_titulo_informe", idioma),
    )
    story = []

    # --- Portada / Resumen ejecutivo ------------------------------------------------
    if logo_path:
        try:
            story.append(Image(logo_path, width=3.6 * cm, height=1.6 * cm, kind="proportional"))
        except Exception:
            pass

    story.append(Spacer(1, 8))
    story.append(Paragraph(tr("pdf_titulo_informe", idioma), estilos["titulo"]))
    story.append(Paragraph(
        tr(
            "pdf_subtitulo_informe", idioma,
            sitio_nombre=datos['sitio_nombre'],
            fecha=datos.get('fecha_generado') or date.today().strftime('%d/%m/%Y'),
        ),
        estilos["subtitulo"],
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=VERDE, spaceAfter=12))

    story.append(Paragraph(
        tr("pdf_intro_resumen", idioma, sitio_nombre=datos['sitio_nombre']),
        estilos["intro"],
    ))

    story.append(_fila_kpis([
        _kpi_card(tr("pdf_kpi_potencia_pico", idioma), f"{datos['potencia_pico_kw']:.2f} kW"),
        _kpi_card(tr("pdf_kpi_energia_anual", idioma), f"{datos['energia_anual_kwh']:,.0f} kWh"),
        _kpi_card(tr("pdf_kpi_turbinas_totales", idioma), f"{datos['n_turbinas_total']}"),
        _kpi_card(tr("pdf_kpi_elevacion_sitio", idioma), f"{datos['elevacion_m']:.0f} m"),
    ]))

    fin = datos.get("financiero")
    if fin:
        story.append(Spacer(1, 10))
        color_viabilidad = VERDE if fin["viable"] else AMBAR
        valor_payback = (
            tr("pdf_valor_anos", idioma, n=f"{fin['payback_years']:.1f}")
            if fin["payback_years"] is not None else tr("pdf_no_disponible", idioma)
        )
        valor_roi = (
            f"{fin['roi_percentage']:.0f}%" if fin["roi_percentage"] is not None
            else tr("pdf_no_disponible", idioma)
        )
        valor_viabilidad = tr("pdf_valor_viable", idioma) if fin["viable"] else tr("pdf_valor_a_evaluar", idioma)
        story.append(_fila_kpis([
            _kpi_card(tr("pdf_kpi_capex_precio_venta", idioma), f"${fin['capex']:,.0f}", accent=AZUL),
            _kpi_card(tr("pdf_kpi_payback", idioma), valor_payback, accent=color_viabilidad),
            _kpi_card(tr("pdf_kpi_roi_vida_util", idioma), valor_roi, accent=color_viabilidad),
            _kpi_card(tr("pdf_kpi_viabilidad_economica", idioma), valor_viabilidad, accent=color_viabilidad),
        ]))

    story.append(PageBreak())

    # --- Contexto climático -----------------------------------------------------------
    clima = datos["clima"]
    story.append(Paragraph(tr("pdf_titulo_contexto_climatico", idioma), estilos["seccion"]))
    story.append(Paragraph(clima["fuente_texto"], estilos["cuerpo"]))
    story.append(Spacer(1, 6))
    imgs_clima = [(clima["img_rosa"], tr("pdf_caption_rosa_vientos", idioma))]
    if clima.get("img_heatmap"):
        imgs_clima.append((clima["img_heatmap"], tr("pdf_caption_heatmap_mensual", idioma)))
    story.append(_fila_imagenes(imgs_clima))
    story.append(Spacer(1, 4))
    story.append(_imagen_png(clima["img_perfil"], ANCHO_UTIL * 0.75, 6.5 * cm))
    story.append(Paragraph(
        tr("pdf_caption_perfil_viento", idioma),
        estilos["img_caption"],
    ))

    story.append(PageBreak())

    # --- Equipos configurados ----------------------------------------------------------
    story.append(Paragraph(tr("pdf_titulo_equipos", idioma), estilos["seccion"]))
    story.append(Paragraph(
        tr("pdf_equipos_texto_bus", idioma, voltaje=datos['voltaje_bus_v']),
        estilos["cuerpo"],
    ))
    for t in datos["turbinas"]:
        bloque = [Paragraph(
            tr("pdf_equipo_nombre_cantidad", idioma, nombre=t['nombre'], cantidad=t['cantidad']),
            estilos["equipo"],
        )]
        bloque.append(Paragraph(
            tr("pdf_equipo_fabricante_parte", idioma, numero_parte=t['numero_parte']), estilos["cuerpo"]
        ))
        bloque.append(Spacer(1, 3))
        _ruta_img = RUTA_IMAGEN.get(t.get("clave"))
        if _ruta_img and os.path.exists(_ruta_img):
            fila = Table(
                [[Image(_ruta_img, width=3.2 * cm, height=3.2 * cm, kind="proportional"),
                  _tabla_specs(t["filas"], idioma)]],
                colWidths=[3.6 * cm, ANCHO_UTIL - 3.6 * cm],
            )
            fila.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
            bloque.append(fila)
        else:
            bloque.append(_tabla_specs(t["filas"], idioma))
        bloque.append(Spacer(1, 8))
        story.append(KeepTogether(bloque))

    # --- Resultados de producción -------------------------------------------------------
    prod = datos["produccion"]
    story.append(Paragraph(tr("pdf_titulo_resultados_produccion", idioma), estilos["seccion"]))
    story.append(_fila_kpis([
        _kpi_card(tr("pdf_kpi_produccion_anual_total", idioma), f"{datos['energia_anual_kwh']:,.0f} kWh"),
        _kpi_card(
            tr("pdf_kpi_correccion_densidad", idioma),
            tr("pdf_valor_pct_menos", idioma, pct=f"{prod['correccion_densidad_pct']:.1f}"),
            accent=AZUL,
        ),
    ]))
    story.append(Spacer(1, 8))
    story.append(_tabla_produccion(prod["filas_tabla"], idioma))
    story.append(Spacer(1, 10))
    # KeepTogether: que el caption de cierre nunca quede solo, huérfano, en la página
    # siguiente -- si las imágenes no entran completas en la página actual, se van
    # las dos juntas (imágenes + caption) a la próxima, no el texto solo.
    story.append(KeepTogether([
        _fila_imagenes([
            (prod["img_mensual"], tr("pdf_caption_produccion_mensual", idioma)),
            (prod["img_duracion"], tr("pdf_caption_curva_duracion", idioma)),
        ]),
        Paragraph(
            tr("pdf_texto_validacion_calculo", idioma),
            estilos["cuerpo"],
        ),
    ]))

    story.append(PageBreak())

    # --- Análisis financiero -------------------------------------------------------------
    story.append(Paragraph(tr("pdf_titulo_analisis_financiero", idioma), estilos["seccion"]))
    if fin:
        color_viabilidad = VERDE if fin["viable"] else AMBAR
        story.append(_fila_kpis([
            _kpi_card("CAPEX", f"${fin['capex']:,.0f}", accent=AZUL),
            _kpi_card(tr("pdf_kpi_ahorro_anual", idioma), f"${fin['ahorro_anual_USD']:,.0f}", accent=VERDE),
            _kpi_card(tr("pdf_kpi_mantenimiento_anual", idioma), f"${fin['mantenimiento_anual_USD']:,.0f}", accent=AZUL),
        ]))
        story.append(Spacer(1, 10))
        valor_payback = (
            tr("pdf_valor_anos", idioma, n=f"{fin['payback_years']:.1f}")
            if fin["payback_years"] is not None else tr("pdf_no_disponible", idioma)
        )
        valor_roi = (
            f"{fin['roi_percentage']:.0f}%" if fin["roi_percentage"] is not None
            else tr("pdf_no_disponible", idioma)
        )
        valor_npv = (
            f"${fin['npv_usd']:,.0f}" if fin.get("npv_usd") is not None
            else tr("pdf_no_disponible", idioma)
        )
        valor_viabilidad = tr("pdf_valor_viable", idioma) if fin["viable"] else tr("pdf_valor_a_evaluar", idioma)
        story.append(_fila_kpis([
            _kpi_card(tr("pdf_kpi_payback", idioma), valor_payback, accent=color_viabilidad),
            _kpi_card(tr("pdf_kpi_roi_vida_util", idioma), valor_roi, accent=color_viabilidad),
            _kpi_card("NPV", valor_npv, accent=color_viabilidad),
            _kpi_card(tr("pdf_kpi_viabilidad", idioma), valor_viabilidad, accent=color_viabilidad),
        ]))
        story.append(Spacer(1, 12))
        story.append(_tabla_specs([
            (tr("pdf_spec_modalidad_tarifa", idioma), tr_modo_tarifa(fin["modo_tarifa"], idioma)),
            (tr("pdf_spec_vida_util_proyecto", idioma), tr("pdf_valor_anos", idioma, n=fin['vida_util_anos'])),
            (tr("pdf_spec_tasa_descuento", idioma), f"{fin['tasa_descuento_pct']:.1f}%"),
        ], idioma))
        story.append(Spacer(1, 8))
        story.append(Paragraph(
            tr("pdf_texto_financiero_metodologia", idioma),
            estilos["cuerpo"],
        ))
    else:
        story.append(_caja_info(tr("pdf_caja_info_falta_financiero", idioma)))

    doc.build(
        story,
        onFirstPage=lambda c, d: _pie_pagina(c, d, idioma),
        onLaterPages=lambda c, d: _pie_pagina(c, d, idioma),
    )
    return buffer.getvalue()


def _flete_por_unidad_optimo(peso_kg):
    """
    Costo de flete por unidad para UNA lista de precios de referencia -- asume
    pedir lo suficiente para llenar exactamente 1 pallet o 1 contenedor (lo que
    salga más barato por unidad), no el flete de comprar una sola unidad suelta.
    Es una referencia de ORDEN DE MAGNITUD para dar una idea de precio, NO el
    flete real de un pedido puntual (para eso ver
    price_calculator.calcular_flete_consolidado_usd() con el peso real del
    embarque completo, que es lo que usa el resto de la app).
    """
    if peso_kg is None or peso_kg <= 0:
        return None
    opciones = []
    if peso_kg <= LIMITE_PESO_UNIDAD_KG:
        opciones.append(COSTO_FLETE_UNIDAD_USD)
    unidades_por_pallet = max(1, math.floor(LIMITE_PESO_PALLET_KG / peso_kg))
    opciones.append(COSTO_FLETE_PALLET_USD / unidades_por_pallet)
    unidades_por_contenedor = max(1, math.floor(LIMITE_PESO_CONTENEDOR_KG / peso_kg))
    opciones.append(COSTO_FLETE_CONTENEDOR_USD / unidades_por_contenedor)
    return min(opciones)


def _tabla_precios(filas, idioma):
    """Tabla de 5 columnas: Modelo / Costo fábrica / Flete est. / Precio final / Fuente."""
    encabezados = [
        tr("pdf_precios_header_modelo", idioma),
        tr("pdf_precios_header_costo_fabrica", idioma),
        tr("pdf_precios_header_flete_unidad", idioma),
        tr("pdf_precios_header_precio_final", idioma),
        tr("pdf_precios_header_fuente_costo", idioma),
    ]
    data = [[Paragraph(h, _estilo_celda_header) for h in encabezados]]
    data += [[_celda(v) for v in fila] for fila in filas]
    t = Table(data, colWidths=[5.1 * cm, 2.6 * cm, 2.9 * cm, 2.9 * cm, 2.6 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, FONDO_TABLA]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def generar_pdf_lista_precios(logo_path=None, idioma="es"):
    """
    Lista de precios de referencia por modelo de turbina: costo de fábrica
    (turbine_specs.py) + flete estimado por el modelo de flete consolidado por
    peso (price_calculator.py) + margen comercial -- misma fórmula y mismos
    supuestos de flete que ya usa el resto de la app, aplicados por modelo
    individual en vez de a un proyecto específico, para darle al equipo
    comercial un precio de referencia por turbina que llevar a una reunión.

    `idioma`: "es" o "en" -- selecciona el idioma de todo el texto del PDF.

    ADVERTENCIA DE FUENTE (se repite también dentro del PDF): las tarifas de
    flete y los límites de peso son datos de mercado, NO una cotización de un
    forwarder real -- usar para dar una idea de magnitud, no para cotizar en
    firme. Los modelos marcados "No verificado" tienen su costo de fábrica de
    una fuente no confirmada contra datasheet/cotización real (ver
    turbine_specs.py) -- no repetirlos como precio firme frente a un cliente.
    """
    estilos = _estilos()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        title=tr("pdf_precios_meta_titulo", idioma),
    )
    story = []

    if logo_path:
        try:
            story.append(Image(logo_path, width=3.6 * cm, height=1.6 * cm, kind="proportional"))
        except Exception:
            pass

    story.append(Spacer(1, 6))
    story.append(Paragraph(tr("pdf_precios_titulo", idioma), estilos["titulo"]))
    story.append(Paragraph(
        tr("pdf_precios_subtitulo", idioma, fecha=date.today().strftime('%d/%m/%Y')),
        estilos["subtitulo"],
    ))
    story.append(HRFlowable(width="100%", thickness=1.2, color=VERDE, spaceAfter=10))

    story.append(Paragraph(
        tr("pdf_precios_texto_formula", idioma),
        estilos["cuerpo"],
    ))
    story.append(Spacer(1, 8))

    verificados, no_verificados = [], []
    for specs in SPECS_TURBINAS.values():
        costo = specs.get("costo_usd")
        if costo is None:
            continue
        peso = specs.get("peso_total_kg")
        flete_u = _flete_por_unidad_optimo(peso)
        precio_final = (costo + (flete_u or 0)) * (1 + MARGIN_PCT)
        fila = [
            specs["nombre"],
            f"${costo:,.2f}",
            f"${flete_u:,.2f}" if flete_u is not None else tr("pdf_no_disponible", idioma),
            f"${precio_final:,.2f}",
            tr("pdf_precios_valor_verificado", idioma) if specs.get("costo_usd_fuente") == "verificado"
            else tr("pdf_precios_valor_no_verificado", idioma),
        ]
        (verificados if specs.get("costo_usd_fuente") == "verificado" else no_verificados).append(fila)

    story.append(Paragraph(tr("pdf_precios_seccion_verificados", idioma), estilos["seccion"]))
    story.append(_tabla_precios(verificados, idioma))

    if no_verificados:
        story.append(Spacer(1, 10))
        story.append(Paragraph(tr("pdf_precios_seccion_no_verificados", idioma), estilos["seccion"]))
        story.append(Paragraph(
            tr("pdf_precios_texto_no_verificado_advertencia", idioma),
            estilos["cuerpo"],
        ))
        story.append(Spacer(1, 4))
        story.append(_tabla_precios(no_verificados, idioma))

    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#CBD5E0"), spaceAfter=6))
    story.append(Paragraph(
        tr("pdf_precios_pie_fuente", idioma),
        estilos["pie"],
    ))

    doc.build(story)
    return buffer.getvalue()
