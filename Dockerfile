# ECO | Wind -- Fase 2, MVP de Streamlit (Hallazgo 16).
# Build de contexto = raiz del repo (la app importa engine/ y lee
# datos_clima/, que estan fuera de app/): docker build -t eco-wind-app .
#
# Respeta $PORT (default 8501 para docker local) para que la MISMA imagen
# sirva sin cambios el dia que se despliegue a Cloud Run (que inyecta PORT
# automaticamente, tipicamente 8080) -- no es una funcionalidad nueva sin
# pedir, es la ruta que el propio plan-tecnico-eco-wind.md senala
# (Docker + Cloud Build, mismo patron de Skyplus/DDP-Lite).

FROM python:3.11-slim

WORKDIR /app

# Capa de dependencias primero (cambia poco) para aprovechar cache de Docker
COPY app/requirements.txt ./app/requirements.txt
RUN pip install --no-cache-dir -r app/requirements.txt

# Codigo y datos que la app REALMENTE necesita en tiempo de ejecucion --
# no todo el repo (ver .dockerignore para lo excluido explicitamente:
# documentos_tecnicos/, notebooks/, .git/, EPWs sin usar todavia, etc.)
COPY engine/ ./engine/
COPY app/ ./app/
COPY datos_clima/gwa_juan_santamaria/ ./datos_clima/gwa_juan_santamaria/

ENV PYTHONUNBUFFERED=1
EXPOSE 8501

CMD streamlit run app/app.py \
    --server.port=${PORT:-8501} \
    --server.address=0.0.0.0 \
    --server.headless=true
