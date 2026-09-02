# Cambios Realizados para Cloud Run

## Resumen Ejecutivo

Se han corregido los problemas de despliegue en Google Cloud Run ajustando:
1. **Puerto dinámico**: Ahora usa la variable de entorno `$PORT` en lugar de hardcodear 8501
2. **Dirección de escucha**: Asegura que Streamlit escucha en `0.0.0.0` (todas las interfaces)
3. **Configuración de Streamlit**: Optimizada para entornos sin interfaz gráfica
4. **Dependencias**: Agregadas google-cloud-* para integración con GCP

---

## Cambios Detallados

### 1. Dockerfile (CRÍTICO)

#### ❌ ANTES (Problémático)
```dockerfile
EXPOSE 8501
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health
RUN mkdir -p ~/.streamlit && \
    echo "[server]" > ~/.streamlit/config.toml && \
    echo "port = 8501" >> ~/.streamlit/config.toml && \
    echo "headless = true" >> ~/.streamlit/config.toml && \
    echo "enableXsrfProtection = false" >> ~/.streamlit/config.toml && \
    echo "[browser]" >> ~/.streamlit/config.toml && \
    echo "gatherUsageStats = false" >> ~/.streamlit/config.toml

CMD ["streamlit", "run", "app/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

**Problemas**:
- 🔴 Puerto hardcodeado a 8501 (Cloud Run espera 8080 o variable $PORT)
- 🔴 No usa la variable de entorno $PORT
- 🔴 Configuración incompleta de Streamlit
- 🔴 CMD sin shell (variable $PORT no se expande)

#### ✅ DESPUÉS (Corregido)
```dockerfile
# Agregar dependencias de Google Cloud
RUN pip install --no-cache-dir \
    -r requirements.txt \
    google-cloud-secret-manager \
    google-auth \
    google-cloud-storage

# Configuración completa de Streamlit para Cloud Run
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
...
EOF

# Health check con puerto dinámico
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/_stcore/health || exit 1

EXPOSE 8080

# ENTRYPOINT permite variable $PORT en CMD
ENTRYPOINT ["sh", "-c"]
CMD ["streamlit run app/app.py --server.port=${PORT:-8080} --server.address=0.0.0.0 --logger.level=warning"]
```

**Mejoras**:
- ✅ Usa variable `${PORT:-8080}` (default 8080)
- ✅ Escucha en `0.0.0.0` (todas las interfaces)
- ✅ ENTRYPOINT con shell permite expansión de variables
- ✅ Health check dinámico
- ✅ Incluye dependencias de Google Cloud
- ✅ Configuración optimizada para Cloud Run

---

### 2. requirements.txt

#### ❌ ANTES
```
streamlit==1.35.0
pandas>=1.3.0
numpy>=1.21.0
matplotlib>=3.4.0
folium>=0.12.0
streamlit-folium>=0.6.0
scipy>=1.7.0
plotly>=5.0.0
```

#### ✅ DESPUÉS
```
streamlit==1.35.0
pandas>=1.3.0
numpy>=1.21.0
matplotlib>=3.4.0
folium>=0.12.0
streamlit-folium>=0.6.0
scipy>=1.7.0
plotly>=5.0.0
# Google Cloud integrations
google-cloud-secret-manager>=2.16.0
google-auth>=2.25.0
google-cloud-storage>=2.10.0
# Additional dependencies
requests>=2.31.0
```

**Por qué**:
- google-cloud-secret-manager: Para acceder a Secret Manager con ADC
- google-auth: Para Application Default Credentials
- google-cloud-storage: Para almacenamiento en GCS (futuro)
- requests: Para llamadas HTTP

---

### 3. Archivos Nuevos

#### 📄 `app/cloud_secrets.py`
Módulo helper para gestionar secretos desde Google Cloud:
```python
from app.cloud_secrets import load_env_from_secrets, is_cloud_run

if is_cloud_run():
    load_env_from_secrets({
        "GOOGLE_SHEETS_API_KEY": "google-sheets-api-key"
    })
```

**Características**:
- Detecta si está corriendo en Cloud Run
- Usa Application Default Credentials (ADC) automáticamente
- Accede a Secret Manager sin archivos .json locales
- Cache para mejorar performance

#### 📄 `cloudbuild.yaml`
Configuración para Cloud Build que:
1. Compila la imagen Docker
2. Hace push a Container Registry
3. Despliega en Cloud Run automáticamente

#### 📄 `.dockerignore`
Optimiza la compilación excluyendo archivos innecesarios:
- `__pycache__`, `*.pyc`
- `.git`, `.github`
- `tests/`, `.pytest_cache`
- `venv/`, `env/`
- Archivos de cache de Streamlit

#### 📄 `DEPLOY_CLOUD_RUN.md`
Guía completa de despliegue con:
- Pasos de configuración
- Comandos de despliegue
- Troubleshooting
- Integración con GitHub Actions

#### 📄 `test_streamlit_config.py`
Script de validación que verifica:
- Streamlit está instalado
- Dependencias disponibles
- app.py existe
- Puerto está disponible
- Streamlit puede iniciar correctamente

---

## Análisis de Errores Originales

### Error 1: "Build failed; check build logs for details"

**Causa probable**:
- La imagen Docker no podía ejecutarse correctamente
- CMD sin shell no expandía variables
- El healthcheck fallaba

**Solución**:
- ENTRYPOINT con shell permite variables
- Health check mejorado con variables dinámicas

### Error 2: "User-provided container failed to start and listen on port"

**Causa**:
- Streamlit estaba configurado para puerto 8501
- Cloud Run esperaba el puerto en variable $PORT
- No escuchaba en dirección correcta

**Solución**:
```dockerfile
# Ahora:
CMD ["streamlit run app/app.py --server.port=${PORT:-8080} --server.address=0.0.0.0"]

# En lugar de:
CMD ["streamlit", "run", "app/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

---

## Cómo Probar Localmente

### 1. Verificar configuración
```bash
python test_streamlit_config.py
```

### 2. Probar con Docker localmente
```bash
# Compilar imagen
docker build -t eco-wind:test .

# Ejecutar contenedor
docker run -p 8080:8080 -e PORT=8080 eco-wind:test

# Acceder a http://localhost:8080
```

### 3. Probar sin Docker
```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar Streamlit
export PORT=8080
streamlit run app/app.py --server.port=$PORT --server.address=0.0.0.0
```

---

## Pasos de Despliegue

### Opción Rápida (usando Cloud Build)
```bash
export PROJECT_ID="tu-proyecto"
export REGION="us-central1"

# Habilitar APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com

# Desplegar
gcloud builds submit --config=cloudbuild.yaml
```

### Opción Manual
```bash
export PROJECT_ID="tu-proyecto"
export REGION="us-central1"

# Compilar y pushear
docker build -t gcr.io/$PROJECT_ID/eco-wind:latest .
docker push gcr.io/$PROJECT_ID/eco-wind:latest

# Desplegar
gcloud run deploy eco-wind \
  --image=gcr.io/$PROJECT_ID/eco-wind:latest \
  --region=$REGION \
  --port=8080 \
  --allow-unauthenticated
```

---

## Verificación Post-Despliegue

```bash
# Ver URL del servicio
gcloud run services describe eco-wind --region=$REGION --format='value(status.url)'

# Ver logs
gcloud run services logs read eco-wind --region=$REGION --limit=50 --follow

# Test de healthcheck
curl https://tu-servicio.run.app/_stcore/health
```

---

## Checklist de Validación

- [ ] Dockerfile compila sin errores
- [ ] `docker build -t eco-wind:test .` funciona localmente
- [ ] `docker run -p 8080:8080 eco-wind:test` inicia correctamente
- [ ] El puerto 8080 es accesible en http://localhost:8080
- [ ] `test_streamlit_config.py` pasa todas las pruebas
- [ ] CloudBuild logs muestran build exitoso
- [ ] Cloud Run muestra "OK" en el dashboard
- [ ] La URL pública es accesible
- [ ] Streamlit carga la aplicación sin errores

---

## Variables de Entorno Importantes

| Variable | Valor | Propósito |
|----------|-------|----------|
| `PORT` | 8080 (default) | Puerto que Cloud Run asigna dinámicamente |
| `GOOGLE_CLOUD_PROJECT` | tu-proyecto-id | ID del proyecto GCP |
| `K_SERVICE` | (automático) | Nombre del servicio en Cloud Run |

---

## Seguridad

### Application Default Credentials (ADC)
La aplicación ahora puede usar ADC automáticamente:
- No requiere archivos .json locales
- No requiere variable GOOGLE_APPLICATION_CREDENTIALS
- Cloud Run proporciona credenciales automáticamente

### Secret Manager
Para variables sensibles:
```bash
echo -n "valor-secreto" | \
  gcloud secrets create mi-secreto --data-file=-

# En despliegue:
gcloud run deploy eco-wind \
  --set-secrets=MI_VAR=mi-secreto:latest
```

---

## Próximos Pasos

1. ✅ Corregir Dockerfile ← HECHO
2. ✅ Actualizar requirements.txt ← HECHO
3. ✅ Crear cloud_secrets.py ← HECHO
4. ✅ Crear cloudbuild.yaml ← HECHO
5. 📋 Ejecutar test_streamlit_config.py
6. 📋 Hacer primer despliegue con `gcloud builds submit`
7. 📋 Monitorear logs en Cloud Run
8. 📋 Configurar custom domain (opcional)
9. 📋 Configurar CI/CD en GitHub Actions (opcional)

---

## Contacto y Soporte

Para issues específicos de Cloud Run: https://cloud.google.com/run/docs/troubleshooting

Logs más detallados:
```bash
gcloud run services logs read eco-wind --region=$REGION --limit=100 --sort-by=TIME_DESC
```
