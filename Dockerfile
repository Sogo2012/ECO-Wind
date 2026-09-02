# syntax=docker/dockerfile:1
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

# Copiar código
COPY . .

# Crear directorio de configuración de Streamlit
RUN mkdir -p ~/.streamlit

# Crear archivo de configuración de Streamlit optimizado para Cloud Run
RUN cat > ~/.streamlit/config.toml << 'EOF'
[server]
port = 8080
headless = true
enableXsrfProtection = false
enableCORS = false
allowRunOnSave = false

[browser]
gatherUsageStats = false
serverAddress = "0.0.0.0"

[client]
showErrorDetails = false

[logger]
level = "info"

[theme]
primaryColor = "#003C52"
backgroundColor = "#E8F0F3"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"
EOF

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
