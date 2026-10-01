"""Arma la salida pública del observatorio con el contrato vg-precios/1 (ver CONTRATO.md).

    python armar_salida.py            # baja de las fuentes y escribe precios/
    python armar_salida.py --seco     # baja y muestra, sin escribir

Escribe solo si los registros cambiaron: una corrida sin datos nuevos no deja
commit. Si una fuente no responde, sale con error y no toca lo publicado.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

from conectores import cftc

CONTRATO = "vg-precios/1"
SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "precios")
#: Ecuador no tiene horario de verano: UTC-5 todo el año.
ECUADOR = timezone(timedelta(hours=-5))


def _escribir(ruta: str, datos) -> None:
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
        f.write("\n")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--seco", action="store_true", help="no escribe")
    a = p.parse_args()

    ahora = datetime.now(timezone.utc)
    hoy = ahora.astimezone(ECUADOR).date()
    regs, series = cftc.registros(cftc.pedir(), hoy)
    if not regs:
        print("ERROR: la CFTC no devolvió ningún mercado")
        return 1
    for r in regs:
        marca = "" if r["validacion"]["estado"] == "ok" else f"  [REVISAR: {'; '.join(r['validacion']['notas'])}]"
        print(f"{r['producto']:7} {r['fecha']}  fondos {r['valor']:>+9,}  {r['senal']['lectura']}{marca}")

    ruta_ultimo = os.path.join(SALIDA, "ultimo.json")
    previo = None
    if os.path.isfile(ruta_ultimo):
        with open(ruta_ultimo, encoding="utf-8") as f:
            previo = json.load(f)
    if previo and previo.get("registros") == regs:
        print("sin cambios: no se escribe")
        return 0
    if a.seco:
        print("--seco: no se escribe")
        return 0

    ultimo = {
        "contrato": CONTRATO,
        "generado": ahora.isoformat(timespec="seconds"),
        "fecha_ecuador": hoy.isoformat(),
        "fuentes": {"cftc_cot": {"fecha": max(r["fecha"] for r in regs),
                                 "estado": "ok" if all(r["validacion"]["estado"] == "ok" for r in regs)
                                 else "revisar"}},
        "registros": regs,
    }
    _escribir(ruta_ultimo, ultimo)
    _escribir(os.path.join(SALIDA, f"{hoy.isoformat()}.json"), ultimo)
    _escribir(os.path.join(SALIDA, "series", "cftc.json"),
              {"contrato": CONTRATO, "fuente_id": "cftc_cot", "valor": "fondos_neto", "series": series})
    print(f"escrito: precios/ultimo.json, precios/{hoy.isoformat()}.json, precios/series/cftc.json")
    if any(r["validacion"]["estado"] != "ok" for r in regs):
        print("::warning::hay registros marcados para revisar")
    return 0


if __name__ == "__main__":
    sys.exit(main())
