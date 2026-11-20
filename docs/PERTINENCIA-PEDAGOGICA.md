# Pertinencia pedagógica

Criterio de la rúbrica: *Pertinencia pedagógica (5 %)*: respuestas personalizadas, prompts usados y accionables (requisitos, proyección, recomendaciones para el éxito), coherentes con la educación de precisión y el autoaprendizaje, con evidencia de investigación.

> Todos los datos de estudiantes son **sintéticos**. El modelo de riesgo y las recomendaciones son apoyo orientativo, no conceptos oficiales de la UNAB.

## 1. Marco: educación de precisión y analítica del aprendizaje

La **analítica del aprendizaje** (*learning analytics*) usa los datos de estudiantes y sus contextos para comprender y mejorar el aprendizaje (Siemens y Long, 2011; Ferguson, 2012). La **educación de precisión** lleva esa idea a la personalización individual: identificar lo antes posible a los estudiantes en riesgo y ofrecer intervenciones oportunas, apoyándose en aprendizaje automático (Luan y Tsai, 2021). Los **sistemas de alerta temprana** como Course Signals (Arnold y Pistilli, 2012) son su aplicación institucional más conocida.

El asistente implementa el ciclo completo en cuatro pasos:

| Paso del ciclo | Qué hace el sistema | Dónde vive |
|---|---|---|
| 1. Datos del estudiante | Notas por corte, avance, promedio, matrícula, tareas de TEMA, evaluaciones docentes, préstamos de biblioteca, historial de cursos y competencias digitales (sintéticos, esquemas `academico` y `servicios`) | Vistas `academico.v_estado_academico`, `v_alertas_prerrequisitos`, `v_requisitos_grado`, `v_insignia`; tabla `servicios.riesgo_estudiante` |
| 2. Diagnóstico | Estado académico, cursos bloqueados por prerrequisitos, requisitos de grado pendientes, estimación de riesgo con factores explicados | Herramientas MCP `estado_academico`, `alertas_requisitos`, `riesgo_academico`, `resumen_360` |
| 3. Recomendación accionable | Reglas explícitas sobre promedio, reprobados, prerrequisitos, insignia, requisitos de grado, TEMA y biblioteca; acciones derivadas de los factores de riesgo | `recomendaciones` y `_acciones_riesgo` en `mcp-server/server.py` |
| 4. Seguimiento | Proyección de semestres, gráficas de progreso, panel "Hoy en tu U", recordatorios y trámites con enlaces | `proyeccion_semestres`, `GET /api/graficas/{codigo}`, `GET /api/hoy/{codigo}` (ver `docs/CONTRATOS-V2.md`) |

Las reglas de `recomendaciones` replican las que el documento RAG `data/docs_ccd/exito_academico.md` enuncia como principios de educación de precisión: priorizar reprobados que son prerrequisito, ajustar la carga de créditos al rendimiento reciente, recomendar tutorías cuando el promedio baja de 3.5 y sugerir cursos del CCD según el nivel. Así la respuesta de consulta general (RAG) y la del agente con datos (MCP) dicen lo mismo desde fuentes distintas: la política institucional y los datos del estudiante.

## 2. Aprendizaje autorregulado

Zimmerman (2002) describe el aprendizaje autorregulado como un ciclo de tres fases: **planificación** (metas, estrategias), **ejecución** (automonitoreo, control) y **autorreflexión** (autoevaluación, atribuciones). En cursos abiertos, fijar metas y planificar estrategias se asocia con el logro de objetivos personales (Kizilcec et al., 2017), lo que justifica un asistente que ayude a *planear* y a *monitorear*, no solo a informar.

| Fase | Funcionalidad | Cómo apoya la autorregulación |
|---|---|---|
| Planificación | `proyeccion_semestres`, `cursos_pendientes`, `alertas_requisitos` | Muestra cuántos semestres faltan, qué cursos están habilitados y cuáles bloqueados, para fijar una meta realista de matrícula |
| Planificación | Recomendación de autoaprendizaje (2 horas semanales, práctica espaciada, portafolio en GitHub) | Convierte el autoaprendizaje en un hábito concreto y medible, alineado con la próxima asignatura |
| Ejecución | Recordatorios de tareas de TEMA (`tareas_tema`, `resumen_360` con próximos 7 días y vencidas) | Gestión del tiempo y priorización por fecha y peso |
| Ejecución | `notas_periodo_actual` con "nota necesaria para aprobar" | Automonitoreo: el estudiante sabe cuánto necesita en lo que resta del periodo |
| Ejecución | Panel "Hoy en tu U" (`/api/hoy/{codigo}`) | Un solo vistazo diario a horario, pendientes, pagos, biblioteca y noticias |
| Autorreflexión | `resumen_360` ("¿cómo voy?"), gráficas `notas_semestre`, `avance`, `parciales`, `riesgo`, `cohorte` | Comparar el propio progreso en el tiempo y frente a la cohorte |
| Autorreflexión | Evaluación docente (`evaluaciones_docentes_pendientes`) | Cierra el ciclo: el estudiante valora la enseñanza recibida |

## 3. Retroalimentación efectiva

Hattie y Timperley (2007) proponen que la retroalimentación eficaz responde tres preguntas: **¿a dónde voy?** (metas), **¿cómo voy?** (progreso) y **¿qué sigue?** (próximos pasos), y que su efecto depende de su tipo y de cómo se entrega. El diseño de las respuestas lo refleja:

- **¿A dónde voy?** Requisitos de grado, porcentaje de avance, insignia de competencias digitales (3 cursos, al menos uno intermedio o avanzado), semestres restantes.
- **¿Cómo voy?** Promedio, notas acumuladas por corte, estado de cada curso ("en riesgo"), tareas vencidas, siempre con el dato exacto devuelto por la herramienta.
- **¿Qué sigue?** Una lista corta de acciones ordenadas por impacto (`_acciones_riesgo` ordena los factores por aporte), con enlaces a trámites (`enlaces_tramites`) y botones de acción en la interfaz.

Los *prompts* refuerzan estas propiedades (`BASE_SYSTEM` en `n8n/build_workflows.py`):

- Respuestas "claras y breves (máx. 180 palabras), con viñetas": limita la carga cognitiva.
- "Nunca inventes notas, fechas, requisitos ni enlaces: si una herramienta no trae el dato, dilo": la retroalimentación es verificable.
- "Usa las herramientas MCP SIEMPRE con el código del estudiante": la personalización proviene de datos y no de generalidades.
- El clasificador de intención distingue historial (personalizado), consulta general (RAG) y trámites (acción), de modo que cada pregunta recibe el tipo de respuesta que necesita.
- Las descripciones de las herramientas son parte del prompt. `riesgo_academico` indica "preséntala con empatía y enfocada en qué puede hacer" y `resumen_360` pide "explica lo más importante en pocas viñetas y ofrece profundizar".

## 4. Modelo de riesgo: uso orientativo y responsable

`servicios.riesgo_estudiante` guarda, por estudiante, la probabilidad, el nivel (bajo, medio, alto), los **factores con su aporte** y el nombre del modelo. `servicios.modelo_riesgo` registra las métricas de entrenamiento (AUC, F1, exactitud, matriz de confusión, importancias, tamaños de entrenamiento y prueba). Principios de diseño:

1. **Orientativo, no punitivo.** La herramienta devuelve un `aviso`: "estimación estadística de un modelo sobre datos sintéticos; no es un concepto oficial". El riesgo no afecta ningún trámite ni decisión; solo dispara acompañamiento (tutorías, Bienestar Universitario).
2. **Transparencia de factores.** Se muestran los factores que *suben* el riesgo (aporte positivo) y se traducen en acciones. Una etiqueta opaca ("riesgo alto") sin explicación no es accionable ni auditable. La gráfica `riesgo` expone esos aportes.
3. **Lenguaje de apoyo.** El prompt de la herramienta exige empatía y foco en lo que el estudiante puede hacer; con riesgo medio o alto el mensaje invita a buscar ayuda "sin pena".
4. **Sesgos.** Un modelo entrenado con datos históricos puede reproducir desigualdades y los falsos positivos pueden estigmatizar. Por eso se reportan métricas por clase (matriz de confusión) y se recomienda revisar calibración y errores por cohorte antes de cualquier uso real.
5. **Datos sintéticos y consentimiento.** Aquí no hay personas reales. En un despliegue institucional serían necesarios consentimiento informado, finalidad declarada, minimización de datos y posibilidad de ver y corregir los propios datos (Slade y Prinsloo, 2013). Los guardrails ya impiden consultar el código de otro estudiante y cada interacción queda en `academico.chat_log`.
6. **Lecciones de Course Signals.** Purdue informó mejoras en retención y búsqueda de ayuda con un semáforo de riesgo (Arnold y Pistilli, 2012), pero esos resultados provienen de comparaciones entre cursos con y sin la herramienta, no de experimentos aleatorizados, y no deben leerse como causalidad. Tomamos de allí lo útil (señal temprana, intervención oportuna, mensaje directo al estudiante) y evitamos sobreprometer: nuestro sistema no mide impacto causal y lo declara como limitación. Un semáforo por sí solo no genera aprendizaje; hace falta la acción siguiente, por eso cada nivel va acompañado de acciones sugeridas.

## 5. De la pregunta del estudiante a la recomendación

Los estudiantes demo `U00000201` a `U00000206` (tabla `academico.persona_demo`) cubren situaciones distintas.

| # | Pregunta del estudiante | Herramienta / dato | Tipo de recomendación | Principio pedagógico |
|---|---|---|---|---|
| 1 | U00000201: "¿Qué me falta para graduarme?" | `v_requisitos_grado`, `alertas_requisitos` | Lista de requisitos pendientes (recta final del plan) | Meta clara, "¿a dónde voy?" (Hattie y Timperley, 2007); planificación (Zimmerman, 2002) |
| 2 | U00000202: "¿Estoy en riesgo?" | `riesgo_academico` (nivel, factores, acciones) | Acciones ordenadas por aporte del factor y acompañamiento de Bienestar | Alerta temprana transparente y no punitiva (Arnold y Pistilli, 2012; Slade y Prinsloo, 2013) |
| 3 | U00000202: "¿Qué tareas tengo vencidas?" | `tareas_tema` (estado, días restantes) | Priorizar por peso y fecha; escribir al docente si se necesita plazo | Gestión del tiempo en la fase de ejecución |
| 4 | U00000203: "¿Cuántos semestres me quedan?" | `proyeccion_semestres`, `v_requisitos_grado` | Proyección de semestres y requisitos pendientes | Planificación de metas realistas |
| 5 | U00000204: "¿Cuál es mi horario de hoy y cómo me muevo en la U?" | `horario`, `calendario_academico`, RAG institucional | Orientación inicial y fechas clave | Reducción de carga cognitiva en la transición; andamiaje |
| 6 | U00000205: "Quiero pagar mi matrícula 2026-2" | `estado_academico` (`pendiente_pago`), flujo de pago Bold en modo pruebas | Acción guiada con botón de pago y recordatorio de fechas | Retroalimentación accionable, "¿qué sigue?" |
| 7 | U00000206: "¿Qué pasa con mi préstamo vencido?" | `prestamos_biblioteca` (multa, estado) | Renovar en el catálogo y pagar la multa | Prevención de consecuencias; autogestión |
| 8 | U00000001: "¿Cómo recupero mis 4 cursos reprobados?" | `cursos_pendientes`, `alertas_requisitos`, `recomendaciones` | Priorizar los que son prerrequisito y ajustar créditos | Personalización por datos del estudiante (Luan y Tsai, 2021) |
| 9 | "¿Voy bien en mis materias?" | `notas_periodo_actual` (nota necesaria para aprobar) | Meta numérica por curso para el siguiente corte | Automonitoreo, "¿cómo voy?" |
| 10 | "¿Cómo voy en general?" | `resumen_360` (todo en una llamada) | Resumen en pocas viñetas y oferta de profundizar | Autorreflexión (Zimmerman, 2002) |
| 11 | "¿Qué puedo aprender por mi cuenta para mi próximo semestre?" | RAG sobre `exito_academico.md`, `oferta_competencias_digitales` | 2 horas semanales, práctica espaciada, cursos del CCD según nivel | Autoaprendizaje y metas propias (Kizilcec et al., 2017) |
| 12 | "Muéstrame mi progreso en una gráfica" | `GET /api/graficas/{codigo}` (`notas_semestre`, `avance`, `cohorte`) | Visualización del propio progreso y comparación con la cohorte | Retroalimentación visual y autorreflexión |

## 6. Limitaciones

- Los datos son sintéticos, de modo que las métricas del modelo no prueban eficacia pedagógica real.
- No se ha medido el efecto del asistente en el desempeño de estudiantes; lo que se valida es el comportamiento técnico (guardrails, herramientas, pruebas automatizadas).
- Las reglas de recomendación son explícitas y revisables; se prefirieron a un modelo opaco para que un director de programa pueda auditarlas.
- Un uso real exigiría evaluación con estudiantes, revisión ética institucional y consentimiento.

## 7. Referencias

Arnold, K. E., y Pistilli, M. D. (2012). Course Signals at Purdue: Using learning analytics to increase student success. En *Proceedings of the 2nd International Conference on Learning Analytics and Knowledge (LAK 2012)*. ACM. https://researchr.org/publication/ArnoldP12

Ferguson, R. (2012). Learning analytics: Drivers, developments and challenges. *International Journal of Technology Enhanced Learning, 4*(5/6), 304-317. https://core.ac.uk/download/82975909.pdf

Hattie, J., y Timperley, H. (2007). The power of feedback. *Review of Educational Research, 77*(1), 81-112. https://doi.org/10.3102/003465430298487

Holmes, W., Bialik, M., y Fadel, C. (2019). *Artificial intelligence in education: Promises and implications for teaching and learning*. Center for Curriculum Redesign. https://oro.open.ac.uk/60255

Kizilcec, R. F., Pérez-Sanagustín, M., y Maldonado, J. J. (2017). Self-regulated learning strategies predict learner behavior and goal attainment in Massive Open Online Courses. *Computers & Education, 104*, 18-33. https://doi.org/10.1016/j.compedu.2016.10.001

Luan, H., y Tsai, C.-C. (2021). A review of using machine learning approaches for precision education. *Educational Technology & Society, 24*(1), 250-266. https://doaj.org/article/3aab60e9caec44fab6fc950b99b4443d

Siemens, G., y Long, P. (2011). Penetrating the fog: Analytics in learning and education. *EDUCAUSE Review, 46*(5). https://er.educause.edu/articles/2011/9/penetrating-the-fog-analytics-in-learning-and-education

Slade, S., y Prinsloo, P. (2013). Learning analytics: Ethical issues and dilemmas. *American Behavioral Scientist, 57*(10), 1509-1528. https://doi.org/10.1177/0002764213479366

Zimmerman, B. J. (2002). Becoming a self-regulated learner: An overview. *Theory Into Practice, 41*(2), 64-70. https://doi.org/10.1207/s15430421tip4102_2
