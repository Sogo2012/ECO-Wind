# ECO | Wind -- Fase 2, MVP de Streamlit (Hallazgo 16).
# Build de contexto = raiz del repo (la app importa engine/ y lee
# datos_clima/, que estan fuera de app/): docker build -t eco-wind-app .
#
# Respeta $PORT (default 8501 para docker local) para que la MISMA imagen
# sirva sin cambios el dia que se despliegue a Cloud Run (que inyecta PORT
# automaticamente, tipicamente 8080) -- no es una funcionalidad nueva sin
# pedir, es la ruta que el propio plan-tecnico-eco-wind.md senala
# (Docker + Cloud Build, mismo patron de Skyplus/DDP-Lite).
#
# COPY . . (no una lista de carpetas a mano) -- mismo patron que
# Skyplus/DDP-Lite. La version anterior copiaba engine/+app/+SOLO
# datos_clima/gwa_juan_santamaria/, una lista que quedo desactualizada
# apenas se agrego el catalogo global y los EPW reales (Hallazgo 18/19):
# epw_catalog_global.json y datos_clima/epw_real/ nunca se copiaban,
# causando un FileNotFoundError real en produccion al buscar cualquier
# sitio (ej. Heredia) que no fuera uno de los 4 ya precacheados. Confiar
# en .dockerignore (una sola lista de exclusiones, no dos listas
# separadas para incluir/excluir que se pueden desincronizar) evita que
# vuelva a pasar con el proximo archivo de datos que se agregue.

FROM python:3.11-slim

WORKDIR /app

# Capa de dependencias primero (cambia poco) para aprovechar cache de Docker
COPY app/requirements.txt ./app/requirements.txt
RUN pip install --no-cache-dir -r app/requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
EXPOSE 8501

CMD streamlit run app/app.py \
    --server.port=${PORT:-8501} \
    --server.address=0.0.0.0 \
    --server.headless=true
