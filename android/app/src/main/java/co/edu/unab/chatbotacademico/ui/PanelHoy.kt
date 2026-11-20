package co.edu.unab.chatbotacademico.ui

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import co.edu.unab.chatbotacademico.ConsultaPago
import co.edu.unab.chatbotacademico.data.Hoy
import co.edu.unab.chatbotacademico.ui.componentes.EmojiEnCirculo
import co.edu.unab.chatbotacademico.ui.componentes.Insignia
import co.edu.unab.chatbotacademico.ui.componentes.TarjetaRespuesta
import java.text.NumberFormat
import java.time.LocalDate
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter
import java.time.temporal.ChronoUnit
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun PanelHoy(
    agenda: Hoy?,
    error: String?,
    ocupado: Boolean,
    pagos: Map<String, ConsultaPago>,
    onPago: (String) -> Unit,
    onConsultarPago: (String) -> Unit,
    reintentar: () -> Unit,
    renovar: () -> Unit,
    cerrar: () -> Unit,
) {
    val contexto = LocalContext.current
    val ahora = remember { ZonedDateTime.now(zonaUnab) }
    ModalBottomSheet(
        onDismissRequest = cerrar,
        sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
        containerColor = Crema,
        shape = FormaContenedor,
    ) {
        Column(Modifier.fillMaxHeight(0.93f)) {
            Row(
                Modifier.fillMaxWidth().padding(start = 16.dp, end = 6.dp, bottom = 5.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    "Hoy en tu U", Modifier.weight(1f).semantics { heading() },
                    style = MaterialTheme.typography.headlineSmall,
                )
                IconButton(onClick = cerrar) { Icon(Icons.Default.Close, "Cerrar panel Hoy") }
            }
            LazyColumn(
                modifier = Modifier.fillMaxWidth(),
                contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 4.dp, bottom = 20.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                if (agenda == null) {
                    item {
                        if (error == null) {
                            Box(Modifier.fillMaxWidth().padding(20.dp), contentAlignment = Alignment.Center) {
                                CircularProgressIndicator()
                            }
                        } else {
                            TarjetaRespuesta {
                                Text(error, color = Peligro)
                                TextButton(onClick = reintentar) { Text("Reintentar") }
                            }
                        }
                    }
                } else {
                    agenda.estudiante?.let {
                        item { ResumenEstudiante(it, agenda.riesgo) }
                    }
                    item {
                        SeccionHoy("🗓️", "Horario de hoy", agenda.horario, "No tienes clases programadas para hoy.") {
                            EntradaAgenda(it.curso, "${it.horario} · ${it.salon}")
                            Text(it.docente, style = MaterialTheme.typography.bodySmall, color = TextoApagado)
                        }
                    }
                    item {
                        SeccionHoy("📝", "Tareas TEMA", agenda.tareas, "No tienes tareas registradas.") { tarea ->
                            val entrega = horaLocal(tarea.fecha)
                            val vencida = tarea.estado == "vencida" ||
                                (tarea.estado == "pendiente" && entrega?.isBefore(ahora) == true)
                            val estado = when {
                                vencida -> "Vencida"
                                tarea.estado == "pendiente" && entrega != null ->
                                    cuentaRegresiva(ChronoUnit.DAYS.between(ahora.toLocalDate(), entrega.toLocalDate()))
                                else -> nombreEstado(tarea.estado)
                            }
                            EntradaAgenda(tarea.titulo, "${tarea.curso} · ${entrega?.format(formatoHora) ?: fechaCorta(tarea.fecha)}")
                            Insignia(estado, if (vencida) Peligro else MoradoFuerte, if (vencida) PeligroSuave else MoradoSuave)
                        }
                    }
                    item {
                        SeccionHoy("⭐", "Califica a tu profe", agenda.evaluaciones, "Estás al día con tus evaluaciones.") {
                            EntradaAgenda(it.curso, "${it.docente} · Hasta ${fechaCorta(it.fecha)}")
                        }
                    }
                    item {
                        SeccionHoy("📚", "Préstamos", agenda.prestamos, "No tienes préstamos activos.") { prestamo ->
                            val fecha = runCatching { LocalDate.parse(prestamo.fecha) }.getOrNull()
                            val vencido = prestamo.estado == "vencido" ||
                                (prestamo.estado == "activo" && fecha?.isBefore(ahora.toLocalDate()) == true)
                            EntradaAgenda(
                                prestamo.titulo,
                                (if (vencido) "Venció el " else "Vence el ") + fechaCorta(prestamo.fecha),
                                if (vencido) Peligro else TextoApagado,
                            )
                            if (prestamo.multa > 0) Text(
                                "Multa · ${cop(prestamo.multa)}", color = Peligro, style = MaterialTheme.typography.bodySmall,
                            )
                            TextButton(onClick = renovar, enabled = !ocupado) { Text("¿Cómo renuevo?") }
                        }
                    }
                    item {
                        if (agenda.pagos.isEmpty()) {
                            SeccionHoy<Unit>("💳", "Pagos pendientes", emptyList(), "No tienes órdenes pendientes.") {}
                        } else EncabezadoSeccion("💳", "Pagos pendientes")
                    }
                    items(agenda.pagos, key = { it.orderId }) { pago ->
                        TarjetaPago(pago, pagos[pago.orderId], onPago, onConsultarPago, textoBoton = "Pagar")
                    }
                    item {
                        SeccionHoy("📰", "Noticias del día", agenda.noticias, "No hay noticias disponibles.") { noticia ->
                            Row(
                                Modifier.fillMaxWidth().clip(FormaBoton)
                                    .clickable(onClickLabel = "Abrir noticia") { abrirEnlace(contexto, noticia.url) }
                                    .padding(vertical = 7.dp),
                                horizontalArrangement = Arrangement.spacedBy(8.dp),
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                val meta = listOfNotNull(noticia.fuente, noticia.fecha?.let(::fechaCorta)).joinToString(" · ")
                                Column(Modifier.weight(1f)) { EntradaAgenda(noticia.titulo, meta) }
                                Text("↗", color = MoradoFuerte, style = MaterialTheme.typography.titleMedium)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ResumenEstudiante(estudiante: Hoy.Estudiante, riesgo: Hoy.Riesgo?) {
    val formato = remember {
        NumberFormat.getNumberInstance(Locale.forLanguageTag("es-CO")).apply { maximumFractionDigits = 2 }
    }
    val avance = estudiante.avance?.takeIf(Double::isFinite)?.coerceIn(0.0, 100.0)
    var animar by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) { animar = true }
    val progreso by animateFloatAsState(
        targetValue = if (animar) ((avance ?: 0.0) / 100).toFloat() else 0f,
        animationSpec = tween(700),
        label = "Avance del plan",
    )

    TarjetaRespuesta(forma = FormaContenedor) {
        Text(estudiante.nombre, style = MaterialTheme.typography.titleLarge)
        Text(
            listOfNotNull(estudiante.programa, estudiante.semestre?.let { "Semestre $it" }).joinToString(" · "),
            color = TextoApagado, style = MaterialTheme.typography.bodyMedium,
        )
        HorizontalDivider(color = Borde)
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f)) {
                Text("Promedio acumulado", style = MaterialTheme.typography.labelMedium, color = TextoApagado)
                Text(
                    estudiante.promedio?.takeIf(Double::isFinite)?.let { formato.format(it) } ?: "Sin promedio",
                    style = MaterialTheme.typography.headlineMedium,
                )
            }
            when (riesgo?.nivel) {
                "alto" -> Insignia("Riesgo alto", Peligro, PeligroSuave)
                "medio" -> Insignia("Riesgo medio", Color(0xFF815000), SuperficieFuerte)
                "bajo" -> Insignia("Riesgo bajo", TextoExito, Exito.copy(alpha = 0.12f))
            }
        }
        if (avance != null) {
            Text("Avance del plan · ${formato.format(avance)} %", style = MaterialTheme.typography.labelLarge)
            LinearProgressIndicator(
                progress = { progreso },
                modifier = Modifier.fillMaxWidth(),
                color = UnabOrange,
                trackColor = SuperficieFuerte,
            )
        }
    }
}

@Composable
private fun <T> SeccionHoy(
    emoji: String,
    titulo: String,
    elementos: List<T>,
    vacio: String,
    contenido: @Composable (T) -> Unit,
) {
    TarjetaRespuesta {
        EncabezadoSeccion(emoji, titulo)
        if (elementos.isEmpty()) {
            Text(vacio, color = TextoApagado, style = MaterialTheme.typography.bodyMedium)
        }
        elementos.forEachIndexed { i, elemento ->
            if (i > 0) HorizontalDivider(color = Borde)
            Column(verticalArrangement = Arrangement.spacedBy(3.dp)) { contenido(elemento) }
        }
    }
}

@Composable
private fun EncabezadoSeccion(emoji: String, titulo: String) {
    Row(horizontalArrangement = Arrangement.spacedBy(9.dp), verticalAlignment = Alignment.CenterVertically) {
        EmojiEnCirculo(emoji)
        Text(titulo, Modifier.semantics { heading() }, style = MaterialTheme.typography.titleMedium)
    }
}

@Composable
private fun EntradaAgenda(titulo: String, detalle: String, color: Color = TextoApagado) {
    Text(titulo, style = MaterialTheme.typography.titleSmall)
    Text(detalle, style = MaterialTheme.typography.bodySmall, color = color)
}

private val zonaUnab = ZoneId.of("America/Bogota")
private val formatoDia = DateTimeFormatter.ofPattern("dd/MM/yyyy")
private val formatoHora = DateTimeFormatter.ofPattern("dd/MM · HH:mm")

private fun horaLocal(fecha: String): ZonedDateTime? =
    runCatching { OffsetDateTime.parse(fecha).atZoneSameInstant(zonaUnab) }.getOrNull()

private fun fechaCorta(fecha: String): String =
    runCatching { LocalDate.parse(fecha).format(formatoDia) }.getOrNull()
        ?: horaLocal(fecha)?.format(formatoDia) ?: fecha

private fun cuentaRegresiva(dias: Long): String = when (dias) {
    0L -> "Vence hoy"
    1L -> "Vence mañana"
    else -> "Vence en $dias días"
}
