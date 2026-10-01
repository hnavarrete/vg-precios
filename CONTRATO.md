# Contrato de salida · `vg-precios/1`

Todo consumidor (Visi, la web, las piezas de redes, Agroclima) lee lo mismo y de la misma forma.

## Archivos

| Archivo | Qué es |
|---|---|
| `precios/ultimo.json` | Lo último de cada fuente. Es el que se consulta |
| `precios/AAAA-MM-DD.json` | Copia de `ultimo.json` del día en que cambió (fecha de Ecuador). La historia del observatorio |
| `precios/series/cftc.json` | Serie semanal de 3 años de la CFTC, para gráficos |

`ultimo.json` solo se reescribe cuando cambian los datos: si la fuente no publicó nada nuevo,
no hay archivo nuevo ni commit.

## Forma de `ultimo.json`

```json
{
  "contrato": "vg-precios/1",
  "generado": "2026-10-01T06:07:00+00:00",
  "fecha_ecuador": "2026-10-01",
  "fuentes": { "cftc_cot": { "fecha": "2026-09-22", "estado": "ok" } },
  "registros": [ { ...un registro... } ]
}
```

## Campos comunes de todo registro

| Campo | Qué es |
|---|---|
| `fuente` · `fuente_id` | Quién lo publica (`cftc_cot`, y luego `icco`, `sipa`, `campo_vg`) |
| `tipo` | `precio` o `posicion`. **Una posición no es un precio** |
| `producto` · `variedad` | `cacao`, `cafe` (arábica), `azucar`, `banano`… |
| `mercado` · `zona` | Dónde: `ICE Nueva York` y `mundo`; luego `Quevedo`, `El Oro`… |
| `unidad` · `moneda` | `contratos` (sin moneda), `USD/qq`, `USD/t`, `USD/caja` |
| `valor` | El número. `que_es_valor` dice qué número es |
| `fecha` | La fecha del dato, no la de la descarga |
| `n_reportes` | Cuántas observaciones hay detrás (en la CFTC, operadores que reportan) |
| `rango` | Mínimo y máximo de referencia (en la CFTC, de los últimos 3 años) |
| `confianza` | `oficial`, `revisar` o, para la capa de campo, el nivel por coincidencia de fuentes |
| `validacion` | `{"estado": "ok" \| "revisar", "notas": [...]}`. **Un registro `revisar` no se muestra como dato firme** |
| `url_fuente` · `licencia` | De dónde sale y con qué permiso se publica |

## Registros de la CFTC (`fuente_id: cftc_cot`)

- `valor`: posición neta de los **fondos** (*managed money*), contratos comprados menos vendidos.
- `senal`: `neto_pct_interes_abierto`, `cambio_neto_semana`, `percentil_3_anios` y `lectura`,
  una línea en español para personas, sin pronóstico.
- `detalle.categorias`: productores, swaps, fondos, otros y no reportables, con largo, corto,
  spread, neto y cambio de la semana.
- Comprobaciones que marcan `revisar`: las posiciones no suman el interés abierto, el cambio no
  coincide con la semana anterior, el informe no es de un martes o tiene más de 14 días.

## Reglas que no se negocian (idea 008)

- **Identidad tapada (R27-B)**: la capa de campo publica solo agregados por zona y nunca una cifra
  de zona con menos de 5 reportes.
- **Nada con licencia de terceros redistribuido**: cero cotizaciones de ICE en vivo.
- Lo que se publica pasa la revisión de ortografía.
