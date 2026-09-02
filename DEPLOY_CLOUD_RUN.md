# Guía de Despliegue de ECO-Wind en Google Cloud Run

## Requisitos previos

1. **Proyecto GCP**: Debes tener un proyecto activo en Google Cloud
2. **gcloud CLI**: Instala [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
3. **Autenticación**: Configura tu autenticación local con `gcloud auth login`
4. **Permisos**: Tu cuenta debe tener permisos para:
   - Cloud Run Admin
   - Service Account Admin
   - Cloud Build Service Account
   - Secret Manager (si usas secretos)

## Paso 1: Configurar el Proyecto GCP

```bash
# Establecer tu PROJECT_ID
export PROJECT_ID="tu-proyecto-id"
export REGION="us-central1"  # Cambia si prefieres otra región

# Configurar gcloud con tu proyecto
gcloud config set project $PROJECT_ID

# Habilitar APIs necesarias
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com  # Si usas Secret Manager
```

## Paso 2: Preparar los secretos en Google Cloud Secret Manager (Opcional)

Si necesitas variables de entorno sensibles (API keys, credenciales):

```bash
# Crear un secreto en Secret Manager
echo -n "tu-valor-secreto" | gcloud secrets create google-sheets-api-key --data-file=-

# O actualizar un secreto existente
echo -n "nuevo-valor" | gcloud secrets versions add google-sheets-api-key --data-file=-

# Dar permiso al Cloud Run service account para leer secretos
gcloud secrets add-iam-policy-binding google-sheets-api-key \
  --member=serviceAccount:$PROJECT_ID@appspot.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor
```

## Paso 3: Desplegar usando Cloud Build

### Opción A: Deploy automatizado (recomendado)

```bash
# Desplegar directamente desde el repositorio o directorio local
gcloud builds submit \
  --config=cloudbuild.yaml \
  --substitutions=_REGION=$REGION,_SERVICE_NAME=eco-wind
```

### Opción B: Deploy manual

```bash
# 1. Compilar la imagen Docker localmente (opcional, para testing)
docker build -t eco-wind:latest .

# 2. Etiquetar para Container Registry
docker tag eco-wind:latest gcr.io/$PROJECT_ID/eco-wind:latest

# 3. Hacer push a Container Registry
docker push gcr.io/$PROJECT_ID/eco-wind:latest

# 4. Desplegar en Cloud Run
gcloud run deploy eco-wind \
  --image=gcr.io/$PROJECT_ID/eco-wind:latest \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --memory=1Gi \
  --cpu=1 \
  --timeout=3600s \
  --set-env-vars=PORT=8080
```

## Paso 4: Verificar el Despliegue

```bash
# Ver el estado del servicio
gcloud run services describe eco-wind --region=$REGION

# Ver los logs en tiempo real
gcloud run services logs read eco-wind --region=$REGION --limit=50 --follow

# Obtener la URL del servicio
gcloud run services describe eco-wind --region=$REGION --format='value(status.url)'
```

## Paso 5: Configurar Variables de Entorno y Secretos

Si necesitas usar Secret Manager en la aplicación:

```bash
# Desplegar nuevamente con referencias a secretos
gcloud run deploy eco-wind \
  --image=gcr.io/$PROJECT_ID/eco-wind:latest \
  --region=$REGION \
  --set-secrets=GOOGLE_SHEETS_API_KEY=google-sheets-api-key:latest \
  --set-env-vars=PORT=8080,GOOGLE_CLOUD_PROJECT=$PROJECT_ID
```

## Troubleshooting

### El build falla con "Build failed; check build logs for details"

1. **Ver logs detallados del build**:
   ```bash
   gcloud builds log <BUILD_ID> --stream
   ```

2. **Problemas comunes**:
   - **Timeout**: El build está tardando demasiado (aumentar timeout en cloudbuild.yaml)
   - **Dependencias faltantes**: Verificar que requirements.txt está correcto
   - **Permisos**: Verificar que el Cloud Build Service Account tiene permisos suficientes

### La aplicación no inicia en Cloud Run

**Error**: "The user-provided container failed to start and listen on the port..."

**Soluciones**:
1. **Verificar que Streamlit escucha en 0.0.0.0**:
   - El Dockerfile ahora incluye `--server.address=0.0.0.0`

2. **Verificar que usa la variable $PORT correctamente**:
   - El ENTRYPOINT ahora usa `${PORT:-8080}`

3. **Ver los logs**:
   ```bash
   gcloud run services logs read eco-wind --region=$REGION --limit=100
   ```

4. **Verificar el health check**:
   - Cloud Run espera que la aplicación responda en `/_stcore/health`
   - Streamlit lo proporciona automáticamente

### Los secretos no se cargan

1. **Verificar que el service account tiene permisos**:
   ```bash
   gcloud secrets get-iam-policy google-sheets-api-key
   ```

2. **Usar el módulo cloud_secrets.py**:
   ```python
   from app.cloud_secrets import load_env_from_secrets, is_cloud_run
   
   if is_cloud_run():
       load_env_from_secrets({
           "GOOGLE_SHEETS_API_KEY": "google-sheets-api-key"
       })
   ```

## Monitoreo y Mantenimiento

### Ver métricas del servicio
```bash
gcloud monitoring dashboards create --config-from-file=- <<EOF
{
  "displayName": "ECO-Wind Cloud Run",
  "mosaicLayout": {
    "columns": 12,
    "tiles": [
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Request Count",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_count\""
                }
              }
            }]
          }
        }
      }
    ]
  }
}
EOF
```

### Actualizar la aplicación

Después de hacer cambios en el código:

```bash
# Opción 1: Usar Cloud Build
gcloud builds submit --config=cloudbuild.yaml

# Opción 2: Manual
docker build -t gcr.io/$PROJECT_ID/eco-wind:latest .
docker push gcr.io/$PROJECT_ID/eco-wind:latest
gcloud run deploy eco-wind \
  --image=gcr.io/$PROJECT_ID/eco-wind:latest \
  --region=$REGION
```

## Integración con GitHub Actions (CI/CD automático)

Crear `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches: [main, develop]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      
      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v1
      
      - name: Deploy to Cloud Run
        run: |
          gcloud builds submit \
            --config=cloudbuild.yaml \
            --substitutions=_REGION=us-central1
```

## Notas Importantes

1. **Puerto**: La aplicación DEBE escuchar en el puerto definido por `$PORT` (por defecto 8080)
2. **Dirección**: DEBE escuchar en `0.0.0.0`, no localhost
3. **Timeout**: Cloud Run mata servicios inactivos; ajusta `--timeout` según necesites
4. **Memoria**: Para aplicaciones grandes, incrementa `--memory` a 2Gi o más
5. **Startup time**: Streamlit puede tardar 30-60 segundos en iniciar; Cloud Run espera por el health check

## Rollback a versión anterior

Si el despliegue nuevo causa problemas:

```bash
# Ver versiones anteriores
gcloud run revisions list --service=eco-wind --region=$REGION

# Cambiar tráfico a una revisión anterior
gcloud run services update-traffic eco-wind \
  --to-revisions=<REVISION_NAME>=100 \
  --region=$REGION
```

## Costo y Optimización

- **Pricing**: Cloud Run factura por vCPU·segundos e invocaciones
- **Optimizar**: Usar `--memory` menor si es posible, `--cpu` apropiado
- **Siempre activo**: `--min-instances` para evitar cold starts
- **Auto-scaling**: Cloud Run escala automáticamente según demanda

Para más información: https://cloud.google.com/run/docs
