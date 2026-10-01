# vg-precios · Observatorio de precios agro de Vision Geografica

Integra lo abierto y oficial, y publica la confianza de cada cifra. Es la idea 008 del
masterplan; dueño: sesión #08 (bus de precios).

| Fuente | Qué da | Frecuencia | Estado |
|---|---|---|---|
| **CFTC · Commitments of Traders** | Hacia dónde empujan los fondos en cacao, café y azúcar (ICE Nueva York) | Semanal (martes, publicado el viernes) | ✅ En marcha |
| ICCO | Precio de referencia mundial del cacao | Diario | Siguiente |
| MAG · SIPA | Precio al productor en Ecuador | Periódico | Después de probar el acceso desde GitHub |

## Cómo corre

GitHub Actions (`.github/workflows/cftc-semanal.yml`) lo ejecuta el viernes después de la
publicación de la CFTC y el lunes por si un feriado la corrió. No depende de ninguna PC
encendida, no usa secretos ni tokens de modelos de lenguaje, y solo hace commit si hay datos nuevos.

```bash
python -m unittest discover -s tests   # pruebas, contra filas reales guardadas
python armar_salida.py --seco          # baja y muestra, sin escribir
python armar_salida.py                 # baja y escribe precios/
```

Solo biblioteca estándar de Python: no hay dependencias que vigilar.

La forma de la salida está en [CONTRATO.md](CONTRATO.md).
