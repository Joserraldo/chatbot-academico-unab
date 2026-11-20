# Riesgo académico · Asistente UNAB 360

El módulo entrena y evalúa un clasificador sobre registros académicos 100 % sintéticos. Publica un puntaje de riesgo para cada estudiante, con hasta tres factores observados que ayudan a interpretar la estimación.

## Reentrenar en Windows 11 con Git Bash

Desde la raíz del repositorio, usa CPython 3.12 de 64 bits, disponible para la rueda de PostgreSQL con pgvector. [Archivos publicados de pgserver 0.1.4](https://pypi.org/project/pgserver/0.1.4/#files)

```bash
py -3.12 -m venv .venv-ml
source .venv-ml/Scripts/activate
python -m pip install -r analitica/requirements.txt
python analitica/riesgo_academico.py
jupyter nbconvert --execute --inplace analitica/riesgo_academico.ipynb
```

El proceso crea un clúster temporal de PostgreSQL en el directorio temporal del sistema (`pgserver` no trae datos de zona horaria, por eso la sesión usa `UTC+5`) y carga `01_schema.sql`, `02_views.sql`, `03_seed.sql`, `04_v2_schema.sql` y, si está presente, `05_v2_seed.sql`. La ruta de datos debe ser ASCII. Si el entorno virtual está en una ruta con tildes, pasa un directorio existente con `--directorio-temporal`. El corte de la demo es el 19 de noviembre de 2026. Usa `--fecha-corte AAAA-MM-DD` para cambiarlo dentro del periodo marcado como actual.

Puedes probar una semilla v2 de integración con `--semilla-v2 RUTA`. Para usar el mismo archivo al ejecutar el cuaderno, exporta `UNAB_SEMILLA_V2` con la ruta absoluta. Cada ejecución vuelve a generar el SQL, las figuras y las métricas.

## Método

La etiqueta vale 1 si el estudiante reprobó al menos un curso o tuvo un promedio ponderado inferior a 3,3 en el último periodo cerrado. El conjunto de evaluación requiere evidencia para asignar la etiqueta. Las variables de ajuste se calculan exclusivamente con periodos anteriores al de la etiqueta. El estudiante se puntúa con las variables del periodo actual y su historial disponible.

Se comparan regresión logística estandarizada y bosque aleatorio. El 75 % de los estudiantes etiquetados sirve para el ajuste y una validación cruzada estratificada de cinco folds. El mayor AUC promedio decide el modelo; si la logística queda a menos de 0,01 del mejor (menos que la desviación entre folds) se prefiere por interpretable. El 25 % reservado proporciona el AUC, F1, exactitud y matriz de confusión de prueba.

## Integración

`db/init/07_v2_riesgo.sql` publica una fila por estudiante en `servicios.riesgo_estudiante` y las métricas del modelo seleccionado en `servicios.modelo_riesgo`. El MCP `riesgo_academico` y la gráfica `riesgo` consumen el puntaje individual. El dashboard `/app/analitica` consume el resumen agregado en `GET /api/analitica/resumen`.

El [informe de analítica](../docs/ANALITICA-ML.md) detalla las variables, el uso orientativo y el paso de publicación en una base existente.

## Resultados reales (datos sintéticos, semilla 42)

| Modelo | AUC CV (5 folds) | AUC prueba | F1 | Exactitud |
|---|---|---|---|---|
| **Regresión logística (elegido)** | 0,857 ± 0,040 | 0,770 | 0,735 | 0,717 |
| Bosque aleatorio | 0,859 ± 0,034 | 0,743 | 0,680 | 0,652 |

181 estudiantes etiquetados (96 en riesgo, 85 sin riesgo): 135 de entrenamiento y 46 de prueba. Se puntúan los 206. Niveles: 84 bajo, 36 medio, 86 alto. Detalle completo, figuras y limitaciones en [docs/ANALITICA-ML.md](../docs/ANALITICA-ML.md).
