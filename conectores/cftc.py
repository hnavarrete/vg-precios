"""Conector CFTC · Commitments of Traders, informe desagregado, solo futuros.

Fuente oficial y abierta: la API Socrata de publicreporting.cftc.gov, conjunto
`72hh-3qpy`. Sin llave ni registro; datos de dominio público del gobierno de EE. UU.

Qué da: cada martes, cuántos contratos de futuros tiene cada tipo de participante
en cacao, café y azúcar de ICE Nueva York. La CFTC lo publica el viernes a las
15:30 de Nueva York (el lunes si hubo feriado). **No es un precio**: dice hacia
dónde empujan los fondos, que es lo que más mueve el precio a corto plazo.

Dos comprobaciones salen de los propios datos y se exigen en cada registro
(medidas el 1-oct-2026: 12 de 12 filas y 9 de 9 pares de semanas):
- La suma de largos y spreads de todas las categorías da el interés abierto, y
  la de cortos también: cada contrato tiene un comprador y un vendedor.
- El neto de los fondos de esta semana menos el de la anterior da el cambio que
  reporta la misma CFTC.
Si una falla, el registro sale con `validacion.estado = "revisar"`: se publica
marcado, nunca como dato firme.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import date

API = "https://publicreporting.cftc.gov/resource/72hh-3qpy.json"
URL_FUENTE = "https://publicreporting.cftc.gov/stories/s/Commitments-of-Traders/r4w3-av2u/"
AGENTE = "vg-precios/1.0 (+https://github.com/hnavarrete/vg-precios)"
#: Tres años de semanas, para ubicar la posición de hoy frente a su historia.
SEMANAS = 156
#: El informe es del martes; si el último tiene más de dos semanas, algo se trabó.
VENCIDO_DIAS = 14

MERCADOS = {
    "073732": {"producto": "cacao", "variedad": None, "mercado": "ICE Nueva York"},
    "083731": {"producto": "cafe", "variedad": "arábica", "mercado": "ICE Nueva York"},
    "080732": {"producto": "azucar", "variedad": "crudo n.º 11", "mercado": "ICE Nueva York"},
}
NOMBRE = {"cacao": "cacao", "cafe": "café", "azucar": "azúcar"}

# (largo, corto, spread, cambio del largo, cambio del corto) de cada categoría.
# Los nombres de la CFTC no son parejos: unos llevan `_all`, otros no, y los cortos
# de swaps usan doble guion bajo. Van tal como vienen (medido el 1-oct-2026).
CATEGORIAS = {
    "productores": ("prod_merc_positions_long", "prod_merc_positions_short", None,
                    "change_in_prod_merc_long", "change_in_prod_merc_short"),
    "swaps": ("swap_positions_long_all", "swap__positions_short_all", "swap__positions_spread_all",
              "change_in_swap_long_all", "change_in_swap_short_all"),
    "fondos": ("m_money_positions_long_all", "m_money_positions_short_all", "m_money_positions_spread",
               "change_in_m_money_long_all", "change_in_m_money_short_all"),
    "otros": ("other_rept_positions_long", "other_rept_positions_short", "other_rept_positions_spread",
              "change_in_other_rept_long", "change_in_other_rept_short"),
    "no_reportables": ("nonrept_positions_long_all", "nonrept_positions_short_all", None,
                       "change_in_nonrept_long_all", "change_in_nonrept_short_all"),
}


def pedir(codigos=tuple(MERCADOS), semanas: int = SEMANAS, abrir=urllib.request.urlopen) -> list[dict]:
    """Las filas de la API, de la más nueva a la más vieja."""
    lista = ",".join(f"'{c}'" for c in codigos)
    q = urllib.parse.urlencode({"$where": f"cftc_contract_market_code in({lista})",
                                "$order": "report_date_as_yyyy_mm_dd DESC",
                                "$limit": str(semanas * len(codigos) + 30)})
    pedido = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": AGENTE,
                                                          "Accept": "application/json"})
    with abrir(pedido, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def _n(fila: dict, campo: str | None) -> int:
    if campo is None:
        return 0
    v = fila.get(campo)
    if v in (None, ""):
        raise ValueError(f"falta el campo {campo}")
    return int(float(v))


def semana(fila: dict) -> dict:
    """Una fila de la CFTC → posiciones por categoría, con neto y cambio semanal."""
    cats = {}
    for nombre, (largo, corto, spread, c_largo, c_corto) in CATEGORIAS.items():
        l, c = _n(fila, largo), _n(fila, corto)
        cats[nombre] = {"largo": l, "corto": c, "spread": _n(fila, spread), "neto": l - c,
                        "cambio_neto": _n(fila, c_largo) - _n(fila, c_corto)}
    return {"fecha": fila["report_date_as_yyyy_mm_dd"][:10],
            "codigo": fila["cftc_contract_market_code"],
            "interes_abierto": _n(fila, "open_interest_all"),
            "operadores": _n(fila, "traders_tot_all"),
            "contrato": (fila.get("contract_units") or "").strip("() ").lower(),
            "categorias": cats}


def cuadra(s: dict) -> bool:
    """Largos y spreads suman el interés abierto, y los cortos también."""
    c = s["categorias"].values()
    largos = sum(x["largo"] + x["spread"] for x in c)
    cortos = sum(x["corto"] + x["spread"] for x in c)
    return largos == s["interes_abierto"] == cortos


def percentil(valor: int, serie: list[int]) -> int:
    """Porcentaje de semanas de la serie con un valor menor o igual al de hoy."""
    return round(100 * sum(1 for v in serie if v <= valor) / len(serie)) if serie else 0


def _miles(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _decimal(x: float) -> str:
    return f"{x:+.1f}".replace(".", ",")


def lectura(producto: str, neto: int, pct: float, cambio: int, pctil: int) -> str:
    """Una línea para personas: qué hacen los fondos, sin pronosticar nada."""
    lado = "comprados" if neto > 0 else "vendidos" if neto < 0 else "sin posición"
    if cambio == 0:
        mov = "sin cambio en la semana"
    else:
        mov = f"{'compraron' if cambio > 0 else 'vendieron'} {_miles(abs(cambio))} contratos en la semana"
    return (f"Fondos en {NOMBRE[producto]}: {lado} en neto, {_miles(abs(neto))} contratos "
            f"({_decimal(pct)} % del interés abierto); {mov}. Su posición supera o iguala "
            f"la del {pctil} % de las semanas de los últimos 3 años.")


def registros(filas: list[dict], hoy: date) -> tuple[list[dict], dict]:
    """(un registro por mercado con el contrato vg-precios/1, series semanales para gráficos)."""
    por_codigo: dict[str, list[dict]] = {}
    for f in filas:
        por_codigo.setdefault(f.get("cftc_contract_market_code"), []).append(f)
    salida, series = [], {}
    for codigo, info in MERCADOS.items():
        semanas = []
        for f in sorted(por_codigo.get(codigo, []), key=lambda f: f["report_date_as_yyyy_mm_dd"]):
            try:
                semanas.append(semana(f))
            except (ValueError, KeyError):
                continue  # una semana vieja ilegible no tumba a las demás
        if not semanas:
            continue
        # La consulta trae de más (el límite es por todas las filas): «3 años» son 156 semanas.
        semanas = semanas[-SEMANAS:]
        ult = semanas[-1]
        fondos = ult["categorias"]["fondos"]
        serie = [s["categorias"]["fondos"]["neto"] for s in semanas]
        notas = []
        if not cuadra(ult):
            notas.append("las posiciones no suman el interés abierto")
        if len(semanas) > 1:
            prev = semanas[-2]
            siete = (date.fromisoformat(ult["fecha"]) - date.fromisoformat(prev["fecha"])).days == 7
            if siete and fondos["neto"] - prev["categorias"]["fondos"]["neto"] != fondos["cambio_neto"]:
                notas.append("el cambio de los fondos no coincide con la semana anterior")
        fecha = date.fromisoformat(ult["fecha"])
        if fecha.weekday() != 1:
            notas.append("el informe no es de un martes")
        if (hoy - fecha).days > VENCIDO_DIAS:
            notas.append(f"el último informe es del {ult['fecha']}: tiene más de {VENCIDO_DIAS} días")
        pct = 100 * fondos["neto"] / ult["interes_abierto"] if ult["interes_abierto"] else 0.0
        pctil = percentil(fondos["neto"], serie)
        salida.append({
            "fuente": "CFTC · Commitments of Traders",
            "fuente_id": "cftc_cot",
            "tipo": "posicion",
            "producto": info["producto"],
            "variedad": info["variedad"],
            "mercado": info["mercado"],
            "zona": "mundo",
            "unidad": "contratos",
            "moneda": None,
            "valor": fondos["neto"],
            "que_es_valor": "posición neta de los fondos (managed money): contratos comprados menos vendidos",
            "fecha": ult["fecha"],
            "n_reportes": ult["operadores"],
            "rango": {"min": min(serie), "max": max(serie), "semanas": len(serie)},
            "confianza": "oficial" if not notas else "revisar",
            "senal": {"neto_pct_interes_abierto": round(pct, 1), "cambio_neto_semana": fondos["cambio_neto"],
                      "percentil_3_anios": pctil,
                      "lectura": lectura(info["producto"], fondos["neto"], pct, fondos["cambio_neto"], pctil)},
            "detalle": {"interes_abierto": ult["interes_abierto"], "contrato": ult["contrato"],
                        "categorias": ult["categorias"]},
            "validacion": {"estado": "ok" if not notas else "revisar", "notas": notas},
            "url_fuente": URL_FUENTE,
            "licencia": "dominio público (gobierno de EE. UU.)",
        })
        series[info["producto"]] = [{"fecha": s["fecha"], "fondos_neto": s["categorias"]["fondos"]["neto"],
                                     "interes_abierto": s["interes_abierto"]} for s in semanas]
    return salida, series
