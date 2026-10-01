"""Conector CFTC contra 12 filas reales (1 al 22-sep-2026, bajadas el 1-oct-2026).

Solo biblioteca estándar: `python -m unittest discover -s tests`.
"""
import copy
import io
import json
import os
import re
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from conectores import cftc  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "cftc_72hh_2026-09.json")
HOY = date(2026, 10, 1)


def filas():
    with open(FIXTURE, encoding="utf-8") as f:
        return json.load(f)


class Respuesta(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class TestCFTC(unittest.TestCase):
    def setUp(self):
        self.regs, self.series = cftc.registros(filas(), HOY)
        self.por = {r["producto"]: r for r in self.regs}

    def test_un_registro_por_mercado_con_el_ultimo_martes(self):
        self.assertEqual(set(self.por), {"cacao", "cafe", "azucar"})
        for r in self.regs:
            self.assertEqual(r["fecha"], "2026-09-22")
            self.assertEqual(r["validacion"], {"estado": "ok", "notas": []})
            self.assertEqual(r["confianza"], "oficial")

    def test_valores_medidos(self):
        self.assertEqual(self.por["cacao"]["valor"], -16406)
        self.assertEqual(self.por["cacao"]["senal"]["cambio_neto_semana"], -6867)
        self.assertEqual(self.por["cafe"]["valor"], 15806)
        self.assertEqual(self.por["azucar"]["detalle"]["interes_abierto"], 1147767)
        self.assertEqual(self.por["cacao"]["detalle"]["contrato"], "contracts of 10 metric tons")

    def test_todas_las_filas_cuadran_con_el_interes_abierto(self):
        for f in filas():
            self.assertTrue(cftc.cuadra(cftc.semana(f)), f["report_date_as_yyyy_mm_dd"])

    def test_descuadre_marca_para_revisar(self):
        malas = filas()
        for f in malas:
            if f["cftc_contract_market_code"] == "073732" and f["report_date_as_yyyy_mm_dd"].startswith("2026-09-22"):
                f["open_interest_all"] = str(int(f["open_interest_all"]) + 1)
        r = {x["producto"]: x for x in cftc.registros(malas, HOY)[0]}["cacao"]
        self.assertEqual(r["validacion"]["estado"], "revisar")
        self.assertEqual(r["confianza"], "revisar")

    def test_cambio_que_no_coincide_con_la_semana_anterior(self):
        malas = filas()
        for f in malas:
            if f["cftc_contract_market_code"] == "083731" and f["report_date_as_yyyy_mm_dd"].startswith("2026-09-22"):
                f["change_in_m_money_long_all"] = str(int(f["change_in_m_money_long_all"]) + 5)
        r = {x["producto"]: x for x in cftc.registros(malas, HOY)[0]}["cafe"]
        self.assertIn("el cambio de los fondos no coincide con la semana anterior", r["validacion"]["notas"])

    def test_informe_vencido(self):
        r = cftc.registros(filas(), date(2026, 10, 20))[0][0]
        self.assertTrue(any("más de 14 días" in n for n in r["validacion"]["notas"]))

    def test_campo_faltante_en_semana_vieja_no_tumba_el_registro(self):
        malas = filas()
        vieja = [f for f in malas if f["report_date_as_yyyy_mm_dd"].startswith("2026-09-01")][0]
        del vieja["m_money_positions_long_all"]
        regs, _ = cftc.registros(malas, HOY)
        self.assertEqual(len(regs), 3)

    def test_series_ordenadas_por_fecha(self):
        fechas = [s["fecha"] for s in self.series["cacao"]]
        self.assertEqual(fechas, sorted(fechas))
        self.assertEqual(len(fechas), 4)

    def test_percentil(self):
        self.assertEqual(cftc.percentil(5, [1, 2, 3, 4, 5]), 100)
        self.assertEqual(cftc.percentil(1, [1, 2, 3, 4, 5]), 20)
        self.assertEqual(cftc.percentil(0, []), 0)

    def test_lectura_en_espanol_neutro_y_sin_pronostico(self):
        t = self.por["cacao"]["senal"]["lectura"]
        self.assertIn("vendidos en neto, 16.406 contratos", t)
        self.assertIn("vendieron 6.867 contratos en la semana", t)
        self.assertIn("-9,2 % del interés abierto", t)
        # sin voseo ni promesas de precio
        palabra = r"(?<![^\W\d_]){}(?![^\W\d_])"
        for prohibida in ("vos", "subirá", "bajará", "comprá", "vendé"):
            self.assertIsNone(re.search(palabra.format(prohibida), t))

    def test_campos_del_contrato(self):
        comunes = {"fuente", "fuente_id", "tipo", "producto", "variedad", "unidad", "moneda", "valor",
                   "fecha", "zona", "n_reportes", "rango", "confianza"}
        for r in self.regs:
            self.assertTrue(comunes <= set(r), comunes - set(r))

    def test_pedir_arma_la_consulta_sin_red(self):
        visto = {}

        def abrir(pedido, timeout):
            visto["url"], visto["ua"] = pedido.full_url, pedido.get_header("User-agent")
            return Respuesta(json.dumps(filas()).encode())

        self.assertEqual(len(cftc.pedir(abrir=abrir)), 12)
        self.assertIn("72hh-3qpy.json", visto["url"])
        self.assertIn("073732", visto["url"])
        self.assertTrue(visto["ua"].startswith("vg-precios/"))

    def test_el_original_no_se_modifica(self):
        f = filas()
        copia = copy.deepcopy(f)
        cftc.registros(f, HOY)
        self.assertEqual(f, copia)


if __name__ == "__main__":
    unittest.main()
