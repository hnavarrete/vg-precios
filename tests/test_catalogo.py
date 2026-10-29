"""El catalogo de jugadores es publico: estas pruebas cuidan sus reglas."""
import json
import unittest
from pathlib import Path

CATALOGO = Path(__file__).resolve().parent.parent / "catalogo"

GRUPOS_PERMITIDOS = {
    "contrato", "cultivo", "version", "actualizado", "estado", "reglas", "clima",
    "oferta", "reguladores", "precio", "demanda", "factores",
}
NIVELES = {"global", "regional", "local"}


class TestCatalogo(unittest.TestCase):
    def setUp(self):
        self.catalogos = {p.name: json.loads(p.read_text(encoding="utf-8"))
                          for p in CATALOGO.glob("jugadores-*.json")}
        self.assertTrue(self.catalogos, "no hay ningun catalogo")

    def test_solo_grupos_publicos(self):
        # Un grupo nuevo (p. ej. «empresas») no entra sin cambiar esta lista a proposito:
        # el repositorio es publico y las empresas viven solo en el catalogo interno.
        for nombre, c in self.catalogos.items():
            self.assertLessEqual(set(c), GRUPOS_PERMITIDOS, nombre)

    def test_cifra_con_fuente_y_fecha(self):
        for nombre, c in self.catalogos.items():
            for p in c["oferta"]["paises"]:
                if p.get("produccion_t") is not None or p.get("cuota") is not None:
                    self.assertTrue(p.get("fuente") and p.get("fecha_fuente"), f"{nombre}: {p['pais']}")

    def test_factores_completos(self):
        for nombre, c in self.catalogos.items():
            for f in c["factores"]:
                self.assertIn(f["nivel"], NIVELES, f["factor"])
                for campo in ("indicador", "fuente", "frecuencia", "empuja"):
                    self.assertTrue(f.get(campo), f"{nombre}: {f['factor']} sin {campo}")
                self.assertIsInstance(f["conectado"], bool)


if __name__ == "__main__":
    unittest.main()
