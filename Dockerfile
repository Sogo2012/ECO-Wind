FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema (incluyendo glibc para ADC)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

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
