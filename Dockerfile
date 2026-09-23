FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema (incluyendo glibc para ADC).
# chromium: kaleido>=1.0 (exporta los gráficos Plotly a PNG para el informe ejecutivo
# en PDF) necesita un Chrome/Chromium instalado -- ya no trae uno embebido en el
# paquete pip como las versiones <1.0. En Debian (esta imagen) el paquete "chromium"
# instala el binario nativo en /usr/bin/chromium, que es exactamente donde kaleido lo
# busca primero -- no hace falta configurar ninguna variable de entorno.
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    ca-certificates \
    chromium \
    && rm -rf /var/lib/apt/lists/*

# EnergyPlus 23.2.0 -- motor real de simulación del bloque solar del Eco-Roof Energy Hub
# (engine/eco_roof_solar.py: genera un modelo Honeybee mínimo con un generador
# Generator:PVWatts, lo traduce a IDF y corre este binario por subprocess -- ya no es
# una aproximación en Python puro). Mismo build oficial de NREL y mismo patrón de
# instalación (descargar tarball -> extraer -> symlink) que usa Sogo2012/Skyplus en
# producción. El build "Ubuntu22.04-x86_64" es el que corrió sin problema en el sandbox
# de desarrollo de este cambio (glibc de esa imagen, no la de este Dockerfile) -- OJO:
# esta imagen SÍ es Debian (python:3.11-slim), y el build real de esta imagen (docker
# build) NO se pudo probar acá (sin daemon de Docker disponible en ese sandbox) -- la
# compatibilidad glibc Ubuntu22.04-binario/Debian-base queda como supuesto razonable
# (mismo binario NREL, misma familia de distros, mismo patrón que usa Skyplus en
# producción), no como algo verificado end-to-end con un build real de esta imagen.
# Probar `docker build .` + `docker run ... energyplus --version` antes del primer
# despliegue a Cloud Run. Aumenta la imagen ~800MB-1GB -- costo aceptado a cambio de una
# simulación física real en vez de una reimplementación aparte.
ENV ENERGYPLUS_DIR=/usr/local/EnergyPlus-23-2-0
ENV ENERGYPLUS_EXEC=/usr/local/bin/energyplus
RUN curl -fsSL \
    "https://github.com/NREL/EnergyPlus/releases/download/v23.2.0/EnergyPlus-23.2.0-7636e6b3e9-Linux-Ubuntu22.04-x86_64.tar.gz" \
    -o /tmp/energyplus.tar.gz \
    && mkdir -p ${ENERGYPLUS_DIR} \
    && tar -xzf /tmp/energyplus.tar.gz -C ${ENERGYPLUS_DIR} --strip-components=1 \
    && ln -sf ${ENERGYPLUS_DIR}/energyplus ${ENERGYPLUS_EXEC} \
    && rm /tmp/energyplus.tar.gz \
    && ${ENERGYPLUS_EXEC} --version

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias Python incluyendo google-cloud para ADC
RUN pip install --no-cache-dir \
    -r requirements.txt \
    google-cloud-secret-manager \
    google-auth \
    google-cloud-storage

# Copiar código -- incluye .streamlit/config.toml (archivo normal del repo, ya no un
# heredoc "RUN cat > ... << EOF"): ese heredoc necesita BuildKit para que Docker lo
# interprete como contenido de archivo y no como instrucciones de Dockerfile línea por
# línea -- el builder que usa Cloud Build ("gcr.io/cloud-builders/docker") no lo trae
# activado por más que el Dockerfile declare "# syntax=docker/dockerfile:1", y eso
# rompía el build con "unknown instruction: [SERVER]" (leía "[server]" del TOML como si
# fuera una instrucción de Dockerfile). Un COPY normal no depende de BuildKit.
COPY . .

# Variable de entorno PORT: valor por defecto para pruebas locales
# (docker run sin --env PORT). Cloud Run la inyecta en tiempo de ejecución
# con el puerto real de la revisión, sobrescribiendo este valor.
ENV PORT=8080

# Exponer puerto (documentación de la imagen; Cloud Run enruta al puerto
# indicado por la variable $PORT, que coincide con --port en el despliegue)
EXPOSE 8080

# Health check (opcional, útil para pruebas locales con `docker run`;
# Cloud Run usa su propio probe de arranque, no esta instrucción)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/_stcore/health || exit 1

# Comando de arranque en una sola instrucción CMD con forma "sh -c":
# el shell expande ${PORT:-8080} en tiempo de ejecución (Cloud Run inyecta
# PORT dinámicamente) y Streamlit escucha en 0.0.0.0 (todas las interfaces),
# requisito indispensable para que el probe de salud de Cloud Run responda.
CMD ["sh", "-c", "streamlit run app/app.py --server.port=${PORT:-8080} --server.address=0.0.0.0 --server.enableCORS=false --server.enableXsrfProtection=false --logger.level=warning"]
