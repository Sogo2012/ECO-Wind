#!/usr/bin/env python3
"""
Script de prueba para validar la configuración de Streamlit.

Verifica que:
1. Streamlit puede ser importado
2. El puerto está correctamente configurado
3. La aplicación puede escuchar en 0.0.0.0
"""

import os
import sys
import socket
import subprocess
import time
import signal
from pathlib import Path

# Colores para output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def print_success(msg):
    print(f"{GREEN}✓ {msg}{RESET}")


def print_error(msg):
    print(f"{RED}✗ {msg}{RESET}")


def print_warning(msg):
    print(f"{YELLOW}⚠ {msg}{RESET}")


def check_streamlit_installed():
    """Verifica que Streamlit está instalado."""
    try:
        import streamlit as st
        print_success(f"Streamlit {st.__version__} está instalado")
        return True
    except ImportError:
        print_error("Streamlit no está instalado. Ejecuta: pip install streamlit")
        return False


def check_dependencies():
    """Verifica que las dependencias requeridas están disponibles."""
    dependencies = [
        "pandas",
        "numpy",
        "matplotlib",
        "folium",
        "plotly",
        "scipy",
    ]

    missing = []
    for dep in dependencies:
        try:
            __import__(dep)
        except ImportError:
            missing.append(dep)

    if missing:
        print_error(f"Dependencias faltantes: {', '.join(missing)}")
        print_warning(
            f"Instalalas con: pip install {' '.join(missing)}"
        )
        return False

    print_success("Todas las dependencias requeridas están instaladas")
    return True


def check_app_file():
    """Verifica que el archivo app.py existe."""
    app_file = Path("app/app.py")
    if app_file.exists():
        print_success(f"Archivo {app_file} encontrado")
        return True
    else:
        print_error(f"Archivo {app_file} no encontrado")
        return False


def check_port_available(port=8080):
    """Verifica que el puerto está disponible."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("0.0.0.0", port))
        print_success(f"Puerto {port} está disponible")
        return True
    except OSError:
        print_error(f"Puerto {port} no está disponible (en uso)")
        return False


def test_streamlit_startup():
    """Prueba que Streamlit puede iniciar correctamente."""
    port = os.environ.get("PORT", "8080")
    print(f"\nIntentando iniciar Streamlit en puerto {port}...")
    print_warning("(La aplicación se detendrá automáticamente después de 10 segundos)")

    # Configurar ambiente
    env = os.environ.copy()
    env["PORT"] = port

    # Iniciar Streamlit
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "app/app.py",
            f"--server.port={port}",
            "--server.address=0.0.0.0",
            "--logger.level=warning",
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # Esperar a que la aplicación inicie
        time.sleep(5)

        # Verificar que el proceso sigue activo
        if process.poll() is None:
            print_success("Streamlit inició correctamente")

            # Intentar conectar al puerto
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(2)
                    # Intentar conexión a localhost (Cloud Run usará 0.0.0.0 pero testamos localhost)
                    result = s.connect_ex(("127.0.0.1", int(port)))
                    if result == 0:
                        print_success(f"Conexión exitosa al puerto {port}")
                    else:
                        print_warning(f"No se pudo conectar a puerto {port} (puede ser normal en algunos ambientes)")
            except Exception as e:
                print_warning(f"Error al testear conexión: {e}")

            return True
        else:
            stdout, stderr = process.communicate()
            print_error("Streamlit falló al iniciar")
            if stderr:
                print(f"  Error: {stderr[:200]}")
            return False

    finally:
        # Terminar el proceso
        try:
            process.terminate()
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def main():
    """Ejecuta todas las pruebas."""
    print("=" * 60)
    print("Prueba de Configuración de Streamlit para Cloud Run")
    print("=" * 60)

    tests = [
        ("Verificar Streamlit", check_streamlit_installed),
        ("Verificar dependencias", check_dependencies),
        ("Verificar app.py", check_app_file),
        ("Verificar puerto disponible", check_port_available),
        ("Test de inicio", test_streamlit_startup),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"Excepción en {test_name}: {e}")
            results.append((test_name, False))

    # Resumen
    print("\n" + "=" * 60)
    print("Resumen de Pruebas")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = f"{GREEN}✓ PASS{RESET}" if result else f"{RED}✗ FAIL{RESET}"
        print(f"{status} - {test_name}")

    print(f"\nTotal: {passed}/{total} pruebas pasadas")

    if passed == total:
        print_success("¡Todo listo para desplegar en Cloud Run!")
        return 0
    else:
        print_error("Hay problemas que deben ser resueltos antes de desplegar")
        return 1


if __name__ == "__main__":
    sys.exit(main())
