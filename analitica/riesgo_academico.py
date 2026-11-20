"""Entrena, evalúa y publica el modelo de la demo con datos sintéticos."""

import argparse
from contextlib import contextmanager
from datetime import date
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory, gettempdir

import matplotlib
import numpy as np
import pandas as pd
import pgserver
import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay, accuracy_score, confusion_matrix, f1_score,
    roc_auc_score, roc_curve,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

matplotlib.use("Agg")
import matplotlib.pyplot as plt


RAIZ = Path(__file__).resolve().parents[1]
INICIO = RAIZ / "db/init"
FIGURAS = RAIZ / "docs/evidencias/ml"
METRICAS = RAIZ / "analitica/metricas.json"
SQL_RIESGO = INICIO / "07_v2_riesgo.sql"
SEMILLA_V2 = INICIO / "05_v2_seed.sql"
SEMILLA = 42
UMBRAL_EMPATE = 0.01
FECHA_DEMO = date(2026, 11, 19)
NARANJA, MORADO = "#FF9D00", "#8600DD"

NOMBRES = {
    "promedio": "Promedio acumulado",
    "tendencia": "Tendencia del promedio",
    "reprobados": "Cursos reprobados previos",
    "creditos_periodo": "Créditos aprobados por periodo cursado",
    "brecha": "Brecha frente a los créditos esperados",
    "diagnostico": "Puntaje en la prueba diagnóstica del CCD",
    "cursos_ccd": "Cursos del CCD aprobados",
    "matricula": "Estado de matrícula",
}
# Tareas de TEMA y notas del corte 1 existen solo para el periodo actual: no hay historial
# con el que entrenar, así que quedan fuera del modelo (se documenta en docs/ANALITICA-ML.md).
NUMERICAS = [variable for variable in NOMBRES if variable != "matricula"]
ESTADOS = {
    "matriculado": "matriculado",
    "pendiente_pago": "pendiente de pago",
    "preinscrito": "preinscrito",
    "aplazado": "aplazado",
    "sin_matricula": "sin matrícula registrada",
}


@contextmanager
def postgres_local(semilla_v2=SEMILLA_V2, directorio=None):
    """Usa un clúster descartable para que cada ejecución vea las mismas semillas."""
    directorio = Path(directorio or gettempdir()).resolve()
    if not str(directorio).isascii():
        raise ValueError("La ruta para los datos de PostgreSQL debe ser ASCII y sin tildes.")
    with TemporaryDirectory(prefix="unab-riesgo-", dir=directorio) as datos:
        datos = Path(datos)
        if sys.platform == "win32":
            # Clúster descartable: se publica el SQL y se omite la sincronización inicial.
            subprocess.run(
                [Path(pgserver.__file__).parent / "pginstall/bin/initdb.exe", "-D", datos, "--auth=trust",
                 "--encoding=UTF8", "--locale=C", "--no-sync", "-U", "postgres"],
                check=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, timeout=90,
            )
        servidor = pgserver.get_server(datos, cleanup_mode="stop")
        try:
            with psycopg.connect(servidor.get_uri(), autocommit=True) as conexion:
                conexion.execute("SET TIME ZONE 'UTC+5'")
                conexion.execute("CREATE ROLE chatbot_ro")
                for archivo in ("01_schema.sql", "02_views.sql", "03_seed.sql", "04_v2_schema.sql"):
                    conexion.execute((INICIO / archivo).read_text(encoding="utf-8"))
                con_v2 = semilla_v2 is not None and Path(semilla_v2).is_file()
                if con_v2:
                    conexion.execute(Path(semilla_v2).read_text(encoding="utf-8"))
                yield conexion, con_v2
        finally:
            servidor.cleanup()


def tabla(conexion, consulta, parametros=None, indice="codigo"):
    with conexion.execute(consulta, parametros) as cursor:
        columnas = [columna.name for columna in cursor.description]
        return pd.DataFrame.from_records(cursor.fetchall(), columns=columnas).set_index(indice)


def variables(conexion, periodo, fecha, es_actual):
    datos = tabla(conexion, """
        WITH periodos AS (
            SELECT *, ROW_NUMBER() OVER (ORDER BY fecha_inicio, id) AS orden
            FROM academico.periodo
        ), observado AS (
            SELECT * FROM periodos WHERE id = %(periodo)s
        ), historial AS (
            SELECT h.estudiante_id, h.curso_id, h.estado, h.nota, c.creditos, p.orden
            FROM academico.historial_curso h
            JOIN academico.curso_plan c ON c.id = h.curso_id
            JOIN periodos p ON p.id = h.periodo_id
            JOIN observado o ON p.orden <= o.orden AND p.fecha_inicio <= %(fecha)s
            WHERE h.estado IN ('aprobado', 'reprobado')
              AND (p.fecha_fin <= %(fecha)s OR (%(actual)s AND p.id = o.id))
        ), por_periodo AS (
            SELECT estudiante_id, orden,
                   SUM(nota * creditos) AS puntos,
                   SUM(creditos) FILTER (WHERE nota IS NOT NULL) AS peso,
                   COUNT(*) FILTER (WHERE estado = 'reprobado') AS reprobados,
                   COALESCE(SUM(creditos) FILTER (WHERE estado = 'aprobado'), 0) AS aprobados
            FROM historial
            GROUP BY estudiante_id, orden
        ), recientes AS (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY estudiante_id ORDER BY orden DESC) AS rango
            FROM por_periodo
            WHERE peso > 0
        ), tendencia AS (
            SELECT estudiante_id, REGR_SLOPE(puntos / peso, orden) AS pendiente
            FROM recientes WHERE rango <= 3
            GROUP BY estudiante_id
        ), resumen AS (
            SELECT estudiante_id, (SUM(puntos) / NULLIF(SUM(peso), 0))::float AS promedio,
                   SUM(reprobados)::float AS reprobados, AVG(aprobados)::float AS creditos_periodo
            FROM por_periodo
            GROUP BY estudiante_id
        ), avance AS (
            SELECT estudiante_id, SUM(creditos) AS creditos
            FROM (SELECT DISTINCT estudiante_id, curso_id, creditos FROM historial
                  WHERE estado = 'aprobado') cursos_unicos
            GROUP BY estudiante_id
        )
        SELECT e.codigo, r.promedio, t.pendiente AS tendencia,
               COALESCE(r.reprobados, 0) AS reprobados,
               r.creditos_periodo, (COALESCE(plan.creditos, 0) - COALESCE(a.creditos, 0))::float AS brecha,
               d.puntaje::float AS diagnostico, ccd.aprobados::float AS cursos_ccd,
               COALESCE(m.estado, 'sin_matricula') AS matricula
        FROM academico.estudiante e
        CROSS JOIN observado o
        LEFT JOIN periodos cohorte ON cohorte.codigo = e.cohorte
        LEFT JOIN resumen r ON r.estudiante_id = e.id
        LEFT JOIN tendencia t ON t.estudiante_id = e.id
        LEFT JOIN avance a ON a.estudiante_id = e.id
        LEFT JOIN academico.matricula m ON m.estudiante_id = e.id AND m.periodo_id = o.id
        LEFT JOIN LATERAL (
            SELECT SUM(creditos) AS creditos
            FROM academico.curso_plan c
            WHERE c.programa_id = e.programa_id
              AND c.semestre <= CASE WHEN %(actual)s THEN e.semestre_actual - 1
                                     ELSE o.orden - cohorte.orden + 1 END
        ) plan ON true
        LEFT JOIN LATERAL (
            SELECT puntaje
            FROM academico.prueba_diagnostica
            WHERE estudiante_id = e.id AND fecha <= %(fecha)s
            ORDER BY fecha DESC LIMIT 1
        ) d ON true
        LEFT JOIN LATERAL (
            SELECT COUNT(*) AS aprobados FROM academico.estudiante_curso_cd
            WHERE estudiante_id = e.id AND fecha <= %(fecha)s AND estado = 'aprobado'
        ) ccd ON true
        ORDER BY e.codigo
    """, {"periodo": int(periodo), "fecha": fecha, "actual": es_actual})
    datos = datos.reindex(columns=NOMBRES)
    datos[NUMERICAS] = datos[NUMERICAS].astype(float)
    return datos


def construir_datos(conexion, fecha):
    periodos = tabla(conexion, """
        SELECT id, codigo, fecha_inicio, fecha_fin, actual
        FROM academico.periodo ORDER BY fecha_inicio, id
    """, indice="id")
    vigentes = periodos.loc[periodos.actual]
    if len(vigentes) != 1:
        raise ValueError("Debe haber exactamente un periodo marcado como actual.")
    actual = vigentes.iloc[0]
    if not actual.fecha_inicio <= fecha <= actual.fecha_fin:
        raise ValueError(f"La fecha de corte debe pertenecer al periodo actual {actual.codigo}.")
    cerrados = periodos.loc[periodos.fecha_fin < actual.fecha_inicio]
    if len(cerrados) < 2:
        raise ValueError("Se requieren dos periodos cerrados antes del periodo actual.")
    observado, objetivo = (cerrados.iloc[posicion] for posicion in (-2, -1))
    etiquetas = tabla(conexion, """
        SELECT e.codigo, (BOOL_OR(h.estado = 'reprobado') OR
               COALESCE(SUM(h.nota * c.creditos) /
                        NULLIF(SUM(c.creditos) FILTER (WHERE h.nota IS NOT NULL), 0)
                        < 3.3, false))::int AS riesgo
        FROM academico.historial_curso h
        JOIN academico.curso_plan c ON c.id = h.curso_id
        JOIN academico.estudiante e ON e.id = h.estudiante_id
        WHERE h.periodo_id = %s AND h.estado IN ('aprobado', 'reprobado')
        GROUP BY e.codigo
        HAVING COUNT(h.nota) > 0 OR BOOL_OR(h.estado = 'reprobado')
        ORDER BY e.codigo
    """, (int(objetivo.name),))
    historico = variables(conexion, observado.name, observado.fecha_fin, False).join(
        etiquetas, how="inner"
    )
    vigentes = variables(conexion, actual.name, fecha, True)
    cortes = {
        "ultimo_periodo_observado": observado.codigo,
        "fecha_variables_entrenamiento": observado.fecha_fin.isoformat(),
        "periodo_etiqueta": objetivo.codigo,
        "periodo_puntuacion": actual.codigo,
        "fecha_puntuacion": fecha.isoformat(),
    }
    return historico, vigentes, cortes


def evaluar(historico):
    x = historico[list(NOMBRES)]
    y = historico.riesgo
    if set(y) != {0, 1} or y.value_counts().min() < 7:
        raise ValueError("Se requieren al menos siete estudiantes etiquetados de cada clase.")
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.25, stratify=y, random_state=SEMILLA
    )
    if y_train.value_counts().min() < 5 or y_test.nunique() != 2:
        raise ValueError("La partición debe cubrir ambas clases y permitir cinco folds.")
    particiones = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEMILLA)
    candidatos = {
        "Regresión logística": LogisticRegression(max_iter=1000, random_state=SEMILLA),
        "Bosque aleatorio": RandomForestClassifier(
            n_estimators=200, min_samples_leaf=5, random_state=SEMILLA
        ),
    }
    resultados, modelos, curvas = {}, {}, {}
    for nombre, estimador in candidatos.items():
        preprocesado = ColumnTransformer([
            ("numericas", make_pipeline(SimpleImputer(keep_empty_features=True),
                                         StandardScaler()), NUMERICAS),
            ("matricula", OneHotEncoder(handle_unknown="ignore", sparse_output=False), ["matricula"]),
        ])
        modelo = make_pipeline(preprocesado, estimador)
        auc_cv = cross_val_score(modelo, x_train, y_train, cv=particiones, scoring="roc_auc")
        modelo.fit(x_train, y_train)
        probabilidades = modelo.predict_proba(x_test)[:, 1]
        predicciones = probabilidades >= 0.5
        resultados[nombre] = {
            "auc_cv_folds": auc_cv.tolist(),
            "auc_cv_media": float(auc_cv.mean()),
            "auc_cv_desviacion": float(auc_cv.std()),
            "auc": roc_auc_score(y_test, probabilidades),
            "f1": f1_score(y_test, predicciones, zero_division=0),
            "accuracy": accuracy_score(y_test, predicciones),
            "matriz": confusion_matrix(y_test, predicciones, labels=[0, 1]).tolist(),
        }
        curvas[nombre] = roc_curve(y_test, probabilidades)[:2]
        modelos[nombre] = modelo
    elegido = max(resultados, key=lambda nombre: resultados[nombre]["auc_cv_media"])
    # Regla de parsimonia: si el modelo lineal queda a menos de UMBRAL_EMPATE de AUC en la
    # validación cruzada (ruido de 5 folds con ~135 casos), se prefiere por interpretable.
    simple = "Regresión logística"
    if resultados[simple]["auc_cv_media"] >= resultados[elegido]["auc_cv_media"] - UMBRAL_EMPATE:
        elegido = simple
    return elegido, modelos[elegido], resultados, curvas, x_train, x_test, y_test


def explicar(modelo, x_train, x_test, y_test, actuales, probabilidades):
    if isinstance(modelo[-1], LogisticRegression):
        coeficientes = modelo[-1].coef_[0]
        transformados = modelo[0].transform(actuales)
        aportes = transformados * coeficientes
        categorias = modelo[0].named_transformers_["matricula"].categories_[0]
        importancias = [
            {"factor": NOMBRES[variable], "importancia": float(coeficiente)}
            for variable, coeficiente in zip(NUMERICAS, coeficientes)
        ] + [
            {"factor": f"Matrícula {ESTADOS.get(estado, estado)}", "importancia": float(coeficiente)}
            for estado, coeficiente in zip(categorias, coeficientes[len(NUMERICAS):])
        ]
        locales = pd.DataFrame(aportes[:, :len(NUMERICAS)], index=actuales.index, columns=NUMERICAS)
        locales["matricula"] = aportes[:, len(NUMERICAS):].sum(axis=1)
        metodo = "Coeficientes logísticos"
    else:
        permutacion = permutation_importance(
            modelo, x_test, y_test, scoring="roc_auc", n_repeats=20, random_state=SEMILLA
        )
        importancias = [
            {"factor": nombre, "importancia": float(media), "desviacion": float(desviacion)}
            for nombre, media, desviacion in zip(
                NOMBRES.values(), permutacion.importances_mean, permutacion.importances_std
            )
        ]
        referencia = x_train[NUMERICAS].median().to_dict()
        referencia["matricula"] = x_train.matricula.mode().iat[0]
        locales = pd.DataFrame({
            variable: probabilidades - modelo.predict_proba(actuales.assign(**{variable: valor}))[:, 1]
            for variable, valor in referencia.items()
        }, index=actuales.index)
        metodo = "Importancia por permutación (pérdida de AUC)"
    importancias.sort(key=lambda dato: abs(dato["importancia"]), reverse=True)
    return importancias, locales, metodo


def factores_estudiante(valores, aportes):
    factores = []
    for variable in aportes.abs().sort_values(ascending=False, kind="stable").index:
        valor = valores[variable]
        if pd.isna(valor):
            continue
        aporte = round(float(aportes[variable]), 6)
        texto = NOMBRES[variable]
        if variable == "matricula":
            valor = ESTADOS.get(valor, valor)
            texto = f"Estado de matrícula ({valor})"
        elif variable == "tendencia":
            valor = round(float(valor), 4)
            direccion = "a la baja" if valor < 0 else "al alza" if valor > 0 else "estable"
            texto = f"Tendencia del promedio {direccion} ({valor:+.2f} por semestre)"
        else:
            valor = round(float(valor), 4)
            texto = f"{texto} ({valor:g})"
        factores.append({"factor": texto, "valor": valor, "aporte": aporte})
        if len(factores) == 3:
            break
    return factores


def generar_figuras(conteo, resultados, curvas, elegido, importancias, metodo):
    FIGURAS.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})

    def guardar(figura, archivo):
        figura.savefig(FIGURAS / archivo, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(figura)

    fig, ax = plt.subplots(figsize=(6.5, 4.4), layout="constrained")
    for (nombre, (fpr, tpr)), color in zip(curvas.items(), (MORADO, NARANJA)):
        ax.plot(fpr, tpr, color=color, linewidth=2.5,
                label=f"{nombre} · AUC {resultados[nombre]['auc']:.3f}")
    ax.plot([0, 1], [0, 1], "--", color="#777777", label="Azar")
    ax.set(title="Curvas ROC en el conjunto de prueba", xlabel="Tasa de falsos positivos",
           ylabel="Tasa de verdaderos positivos", xlim=(0, 1), ylim=(0, 1.02))
    ax.legend(loc="lower right", frameon=False)
    ax.grid(alpha=0.2)
    guardar(fig, "roc.png")

    fig, ax = plt.subplots(figsize=(6, 4.4), layout="constrained")
    morados = matplotlib.colors.LinearSegmentedColormap.from_list("unab", ["#F7EEFC", MORADO])
    matriz = np.array(resultados[elegido]["matriz"])
    ConfusionMatrixDisplay(matriz, display_labels=["Sin riesgo", "En riesgo"]).plot(
        ax=ax, cmap=morados, colorbar=False, values_format="d"
    )
    ax.set(title=f"Matriz de confusión · {elegido}\nPrueba con umbral 0,50",
           xlabel="Predicción", ylabel="Etiqueta observada")
    guardar(fig, "matriz_confusion.png")

    fig, ax = plt.subplots(figsize=(8, 4.6), layout="constrained")
    datos = list(reversed(importancias))
    valores = [dato["importancia"] for dato in datos]
    ax.barh([dato["factor"] for dato in datos], valores,
            color=[MORADO if valor >= 0 else NARANJA for valor in valores])
    ax.axvline(0, color="#555555", linewidth=0.8)
    ax.set(title="Importancia de las variables", xlabel=metodo)
    ax.grid(axis="x", alpha=0.2)
    guardar(fig, "importancias.png")

    fig, ax = plt.subplots(figsize=(6, 4), layout="constrained")
    barras = ax.bar(["Sin riesgo", "En riesgo"], list(conteo.values()), color=[MORADO, NARANJA], width=0.55)
    total = sum(conteo.values())
    ax.bar_label(barras, labels=[f"{n} · {n / total:.1%}" for n in conteo.values()], padding=4)
    ax.set(title=f"Distribución de la etiqueta · {total} estudiantes", ylabel="Estudiantes",
           ylim=(0, max(conteo.values()) * 1.2))
    guardar(fig, "distribucion_riesgo.png")


def generar_sql(conexion, puntajes, metricas):
    # El inicializador y la migración ejecutan esta semilla con el usuario administrador.
    insert_riesgo = sql.SQL("INSERT INTO servicios.riesgo_estudiante "
                           "(codigo, probabilidad, nivel, factores, modelo) VALUES\n{};")
    filas = [
        sql.SQL("({}, {}, {}, {}, {})").format(
            codigo, probabilidad, nivel, Jsonb(factores), metricas["modelo_elegido"]
        )
        for codigo, probabilidad, nivel, factores in puntajes
    ]
    insert_modelo = sql.SQL("""
INSERT INTO servicios.modelo_riesgo
    (nombre, auc, f1, accuracy, matriz, importancias, n_train, n_test)
VALUES ({}, {}, {}, {}, {}, {}, {}, {});""")
    ganador = metricas["modelos"][metricas["modelo_elegido"]]
    entrada = insert_modelo.format(
        metricas["modelo_elegido"], round(ganador["auc"], 8), round(ganador["f1"], 8),
        round(ganador["accuracy"], 8), Jsonb(ganador["matriz"]), Jsonb(metricas["importancias"]),
        metricas["n_train"], metricas["n_test"],
    )
    return "\n".join([
        "-- GENERADO por analitica/riesgo_academico.py",
        "-- Datos sintéticos. Ejecutar como administrador después de las semillas académicas.",
        "BEGIN;",
        "LOCK TABLE servicios.riesgo_estudiante, servicios.modelo_riesgo IN SHARE ROW EXCLUSIVE MODE;",
        "DELETE FROM servicios.riesgo_estudiante;",
        "DELETE FROM servicios.modelo_riesgo;",
        insert_riesgo.format(sql.SQL(",\n").join(filas)).as_string(conexion),
        entrada.as_string(conexion),
        "COMMIT;", "",
    ])


def ejecutar(fecha=FECHA_DEMO, semilla_v2=SEMILLA_V2, directorio=None):
    with postgres_local(semilla_v2, directorio) as (conexion, con_v2):
        historico, actuales, cortes = construir_datos(conexion, fecha)
        elegido, modelo, resultados, curvas, x_train, x_test, y_test = evaluar(historico)
        probabilidades = modelo.predict_proba(actuales)[:, 1]
        importancias, aportes, metodo = explicar(modelo, x_train, x_test, y_test, actuales, probabilidades)
        puntajes = []
        for (codigo, valores), probabilidad in zip(actuales.iterrows(), probabilidades):
            probabilidad = round(float(probabilidad), 4)
            nivel = "alto" if probabilidad >= 0.6 else "medio" if probabilidad >= 0.35 else "bajo"
            puntajes.append((codigo, probabilidad, nivel, factores_estudiante(valores, aportes.loc[codigo])))
        conteo = {
            "sin_riesgo": int((historico.riesgo == 0).sum()),
            "en_riesgo": int((historico.riesgo == 1).sum()),
        }
        numericas = historico[NUMERICAS + ["riesgo"]]
        correlaciones = json.loads(numericas.corr().to_json(double_precision=6))
        metricas = {
            "datos": "100 % sintéticos",
            "semilla_aleatoria": SEMILLA,
            "semilla_v2": con_v2,
            **cortes,
            "etiqueta": "Al menos un curso reprobado o promedio ponderado inferior a 3,3.",
            "distribucion_etiqueta": conteo,
            "correlaciones_pearson": correlaciones,
            "observaciones_por_variable": {
                variable: {"historico": int(historico[variable].count()),
                           "puntuacion": int(actuales[variable].count()),
                           "valores_distintos_entrenamiento": int(x_train[variable].nunique())}
                for variable in NOMBRES
            },
            "n_train": len(x_train),
            "n_test": len(x_test),
            "n_puntuados": len(puntajes),
            "niveles": {nivel: sum(fila[2] == nivel for fila in puntajes) for nivel in ("bajo", "medio", "alto")},
            "modelo_elegido": elegido,
            "modelos": resultados,
            "metodo_importancias": metodo,
            "importancias": importancias,
        }
        semilla_sql = generar_sql(conexion, puntajes, metricas)
        for _ in range(2):
            conexion.execute(semilla_sql)
            n_riesgos = conexion.execute("SELECT COUNT(*) FROM servicios.riesgo_estudiante").fetchone()[0]
            n_modelos = conexion.execute("SELECT COUNT(*) FROM servicios.modelo_riesgo").fetchone()[0]
            if (n_riesgos, n_modelos) != (len(actuales), 1):
                raise RuntimeError("La publicación local debe contener todos los puntajes y un solo modelo.")

    generar_figuras(conteo, resultados, curvas, elegido, importancias, metodo)
    SQL_RIESGO.write_text(semilla_sql, encoding="utf-8")
    METRICAS.write_text(json.dumps(metricas, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    return metricas


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fecha-corte", type=date.fromisoformat, default=FECHA_DEMO,
                        help="Fecha dentro del periodo actual (AAAA-MM-DD).")
    parser.add_argument("--semilla-v2", type=Path,
                        help="Ruta alternativa a la semilla v2 para pruebas de integración.")
    parser.add_argument("--directorio-temporal", type=Path,
                        help="Directorio existente sin tildes para el clúster local.")
    args = parser.parse_args()
    if args.semilla_v2 is not None and not args.semilla_v2.is_file():
        parser.error("La ruta indicada para la semilla v2 no corresponde a un archivo.")
    metricas = ejecutar(args.fecha_corte, args.semilla_v2 or SEMILLA_V2, args.directorio_temporal)
    print(f"{metricas['n_puntuados']} estudiantes puntuados · modelo {metricas['modelo_elegido']}")
    for nombre, datos in metricas["modelos"].items():
        print(f"{nombre} | AUC CV {datos['auc_cv_media']:.3f} | AUC prueba {datos['auc']:.3f} "
              f"| F1 {datos['f1']:.3f} | exactitud {datos['accuracy']:.3f}")


if __name__ == "__main__":
    main()
