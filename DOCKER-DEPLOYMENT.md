# Docker & GCS Deployment Guide
## Phase 3B - Entrega Local + Cloud

**Status:** Dockerfile + docker-compose.yml + requirements.txt listos  
**Siguiente:** Ejecutar en tu máquina local (Windows/Mac/Linux)

---

## 📦 PASO 1: BUILD & RUN LOCAL (En tu máquina)

### Pre-requisitos
- ✅ Docker Desktop instalado ([descarga](https://www.docker.com/products/docker-desktop))
- ✅ Git con el repo ECO-Wind clonado
- ✅ `cd` al directorio del proyecto

### Construcción

```bash
# 1. Build la imagen (primera vez tarda 3-5 min)
docker build -t eco-wind:latest .

# Output esperado:
# ✓ Successfully built eco-wind:latest

# 2. Verificar imagen
docker images | grep eco-wind
```

### Ejecución Local

**Opción A: Con docker-compose (Recomendado)**
```bash
docker-compose up -d

# Ver logs
docker-compose logs -f eco-wind

# Acceder a http://localhost:8501
```

**Opción B: Sin docker-compose**
```bash
docker run -d \
  --name eco-wind \
  -p 8501:8501 \
  -v $(pwd):/app \
  eco-wind:latest

# Ver logs
docker logs -f eco-wind

# Acceder a http://localhost:8501
```

### Validación Local
- ✅ Abre http://localhost:8501 en tu navegador
- ✅ Verifica que cargue la app
- ✅ Prueba el toggle "🔬 Usar método avanzado (Gower distance)"
- ✅ Si todo funciona → Proceed to Step 2

### Detener Container
```bash
docker-compose down
# O
docker stop eco-wind && docker rm eco-wind
```

---

## 📤 PASO 2: PUSH A GCS (Google Cloud Storage)

### Pre-requisitos
- ✅ Google Cloud Project creado
- ✅ `gcloud` CLI instalado ([descarga](https://cloud.google.com/sdk/docs/install))
- ✅ Autenticado: `gcloud auth login`
- ✅ Proyecto configurado: `gcloud config set project YOUR_PROJECT_ID`

### Pasos

#### 1. Habilitar APIs
```bash
gcloud services enable \
  containerregistry.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com
```

#### 2. Configurar Docker para GCP
```bash
# Autenticar Docker con GCP
gcloud auth configure-docker

# Verificar
docker images
```

#### 3. Tag de imagen para GCR
```bash
# Variables
export GCP_PROJECT_ID="tu-proyecto-id"
export IMAGE_NAME="eco-wind"
export GCP_IMAGE="gcr.io/${GCP_PROJECT_ID}/${IMAGE_NAME}"

# Tag
docker tag eco-wind:latest ${GCP_IMAGE}:latest

# Verificar
docker images | grep gcr.io
```

#### 4. Push a GCS
```bash
docker push ${GCP_IMAGE}:latest

# Output esperado:
# latest: digest: sha256:abc123... size: 5000
```

---

## 🚀 PASO 3: DEPLOY A CLOUD RUN

### Opción A: Desde gcloud CLI (Más control)

```bash
gcloud run deploy eco-wind \
  --image=${GCP_IMAGE}:latest \
  --platform=managed \
  --region=us-central1 \
  --allow-unauthenticated \
  --port=8501 \
  --memory=1Gi \
  --timeout=3600 \
  --set-env-vars="STREAMLIT_SERVER_ADDRESS=0.0.0.0,STREAMLIT_SERVER_PORT=8501"

# Output:
# Service [eco-wind] revision [eco-wind-00001-abc] has been deployed
# Service URL: https://eco-wind-xxxxx.run.app
```

### Opción B: Console (Más fácil)

1. Ve a https://console.cloud.google.com/run
2. Click "Create Service"
3. Selecciona "Deploy one revision from an existing image"
4. Busca `gcr.io/YOUR_PROJECT_ID/eco-wind`
5. Nombre: `eco-wind`
6. Region: `us-central1`
7. Authentication: Allow unauthenticated invocations
8. Click "Create"

---

## ✅ VALIDACIÓN EN CLOUD RUN

1. Obtener URL pública:
```bash
gcloud run services describe eco-wind --region=us-central1 --format='value(status.url)'
```

2. Acceder: `https://eco-wind-xxxxx.run.app`

3. Verificar:
   - ✅ Carga la interfaz Streamlit
   - ✅ Ve todas las pestañas
   - ✅ Toggle "Usar método avanzado (Gower distance)" aparece
   - ✅ Puedes hacer búsqueda de sitios

---

## 📊 RESUMEN DE COMANDOS RÁPIDOS

```bash
# LOCAL
docker-compose up -d              # Levantar
docker-compose logs -f eco-wind   # Ver logs
docker-compose down               # Detener
http://localhost:8501             # Acceder

# GCS PUSH
docker tag eco-wind:latest gcr.io/YOUR_PROJECT/eco-wind
docker push gcr.io/YOUR_PROJECT/eco-wind

# CLOUD RUN DEPLOY
gcloud run deploy eco-wind \
  --image=gcr.io/YOUR_PROJECT/eco-wind:latest \
  --platform=managed \
  --region=us-central1 \
  --allow-unauthenticated
```

---

## 🔧 TROUBLESHOOTING

### "Connection refused" en localhost:8501
```bash
# Verificar que el container está corriendo
docker ps | grep eco-wind

# Ver logs
docker logs eco-wind

# Si no está corriendo:
docker-compose up -d
sleep 5  # Esperar inicialización
```

### "Authentication failed" al push a GCS
```bash
gcloud auth configure-docker
docker push ...
```

### Cloud Run timeout (app tarda mucho en cargar)
- Aumentar timeout: `--timeout=3600`
- Aumentar memoria: `--memory=2Gi`
- Verificar logs: `gcloud run logs eco-wind --limit=50`

### "Image not found" en Cloud Run
```bash
# Verificar que la imagen está en GCR
gcloud container images list --filter="eco-wind"

# O push nuevamente
docker push gcr.io/YOUR_PROJECT/eco-wind:latest
```

---

## 📋 CHECKLIST ENTREGA

- [ ] Docker build exitoso localmente
- [ ] App funciona en http://localhost:8501
- [ ] Toggle Gower visible y funcional
- [ ] Image pusheada a gcr.io
- [ ] Deployed a Cloud Run
- [ ] URL pública compartida con cliente
- [ ] Validación final en Cloud Run ✅

---

## 🎯 URLs FINALES PARA ENTREGA

Compartir con cliente:
```
Aplicación Phase 3B - ECO Wind
📱 URL Pública: https://eco-wind-xxxxx.run.app
🏗️ Arquitectura: Streamlit + Dynamic Terrain + Gower Distance
✅ Toggle Gower disponible para A/B testing
```

---

**Tiempo total: ~30 min (build local + push + deploy)**
