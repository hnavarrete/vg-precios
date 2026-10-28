"""Corre el observatorio y publica lo nuevo. Lo lanza la tarea VG-ObservatorioPrecios de la Torre 2, cada día.

Por qué una tarea local y no el flujo de GitHub (.github/workflows/cftc-semanal.yml): ese flujo no se puede subir sin
el permiso `workflow` del token de GitHub (ítem 91 de Henrry), y el 28-oct el observatorio llevaba 23 días sin
actualizarse. R-TAREAS: un guion local, sin tokens de modelo. Cuando el flujo exista, esta tarea se apaga.

Pasos: trae lo último del repositorio, corre `armar_salida.py` (solo reescribe si la fuente publicó algo nuevo),
y si cambió algo en `precios/`, hace commit y push de esa carpeta y de nada más.
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def correr(*cmd: str) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", errors="replace")


def main() -> int:
    print(f"[{datetime.now():%Y-%m-%d %H:%M}] observatorio: inicio")
    r = correr("git", "pull", "--ff-only", "-q")
    if r.returncode:
        print("git pull falló:", r.stderr.strip()[:300])
        return 1
    r = correr(sys.executable, "-X", "utf8", "armar_salida.py")
    print(r.stdout.strip()[-1500:])
    if r.returncode:
        print("armar_salida falló:", r.stderr.strip()[-800:])
        return 1
    if not correr("git", "status", "--porcelain", "--", "precios").stdout.strip():
        print("sin datos nuevos: nada que publicar")
        return 0
    correr("git", "add", "--", "precios")
    r = correr("git", "commit", "-q", "-m", "precios: actualización automática (tarea VG-ObservatorioPrecios, Torre 2)")
    if r.returncode:
        print("git commit falló:", (r.stdout + r.stderr).strip()[:300])
        return 1
    r = correr("git", "push", "-q")
    if r.returncode:
        print("git push falló:", r.stderr.strip()[:300])
        return 1
    print("publicado:", correr("git", "log", "--oneline", "-1").stdout.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
