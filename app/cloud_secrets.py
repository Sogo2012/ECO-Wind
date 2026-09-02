"""
Gestor de secretos para Google Cloud Run.

Usa Application Default Credentials (ADC) para acceder a Secret Manager
sin necesidad de archivos .json locales.
"""

import os
from functools import lru_cache
from typing import Optional


def get_secret(secret_name: str, project_id: Optional[str] = None) -> str:
    """
    Obtiene un secreto de Google Cloud Secret Manager.

    Args:
        secret_name: Nombre del secreto en Secret Manager
        project_id: ID del proyecto GCP (si no se proporciona, usa GOOGLE_CLOUD_PROJECT)

    Returns:
        Valor del secreto

    Raises:
        ValueError: Si el secreto no existe o no se puede acceder
        ImportError: Si google-cloud-secret-manager no está instalado
    """
    if not project_id:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
        if not project_id:
            raise ValueError(
                "project_id must be provided or GOOGLE_CLOUD_PROJECT env var must be set"
            )

    try:
        from google.cloud import secretmanager
    except ImportError:
        raise ImportError(
            "google-cloud-secret-manager is required. Install with: pip install google-cloud-secret-manager"
        )

    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        raise ValueError(f"Failed to access secret '{secret_name}': {str(e)}")


@lru_cache(maxsize=100)
def get_secret_cached(secret_name: str, project_id: Optional[str] = None) -> str:
    """
    Versión cached de get_secret para mejorar performance.
    """
    return get_secret(secret_name, project_id)


def load_env_from_secrets(secret_keys: dict[str, str], project_id: Optional[str] = None):
    """
    Carga variables de entorno desde Secret Manager.

    Args:
        secret_keys: Dict con {env_var_name: secret_name}
        project_id: ID del proyecto GCP
    """
    for env_var, secret_name in secret_keys.items():
        if not os.environ.get(env_var):
            try:
                value = get_secret_cached(secret_name, project_id)
                os.environ[env_var] = value
            except ValueError as e:
                print(f"Warning: Could not load secret {secret_name}: {e}")


def is_cloud_run() -> bool:
    """Detecta si la aplicación está corriendo en Cloud Run."""
    return bool(os.environ.get("K_SERVICE")) or bool(
        os.environ.get("CLOUD_RUN_JOB_EXECUTION")
    )


def setup_cloud_run_environment():
    """
    Configura el entorno para Cloud Run.

    Esto incluye:
    - Verificar que se está usando la variable $PORT correcta
    - Configurar Application Default Credentials
    - Cargar secretos si es necesario
    """
    if is_cloud_run():
        # Asegurar que la aplicación usa el puerto correcto
        port = os.environ.get("PORT", "8080")
        os.environ["PORT"] = port

        # Verificar que google-cloud-secret-manager está disponible
        try:
            import google.auth
            _, project_id = google.auth.default()
            if project_id:
                os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
        except Exception:
            pass


# Ejecutar setup al importar si está en Cloud Run
if is_cloud_run():
    setup_cloud_run_environment()
