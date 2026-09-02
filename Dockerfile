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

# Health check (opcional, pero útil para Cloud Run)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/_stcore/health || exit 1

# Exponer puerto (para documentación, Cloud Run asigna el puerto dinámicamente)
EXPOSE 8080

# Script de entrada para manejo dinámico del puerto
ENTRYPOINT ["sh", "-c"]
CMD ["streamlit run app/app.py --server.port=${PORT:-8080} --server.address=0.0.0.0 --logger.level=warning"]
