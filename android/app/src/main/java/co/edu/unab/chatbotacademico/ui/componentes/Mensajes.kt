package co.edu.unab.chatbotacademico.ui.componentes

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateContentSize
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.MutableTransitionState
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.StartOffset
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.slideInVertically
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import co.edu.unab.chatbotacademico.Msg
import co.edu.unab.chatbotacademico.ui.Borde
import co.edu.unab.chatbotacademico.ui.FormaContenedor
import co.edu.unab.chatbotacademico.ui.FormaTarjeta
import co.edu.unab.chatbotacademico.ui.MoradoFuerte
import co.edu.unab.chatbotacademico.ui.Superficie
import co.edu.unab.chatbotacademico.ui.SuperficieSuave
import co.edu.unab.chatbotacademico.ui.Texto
import co.edu.unab.chatbotacademico.ui.TextoApagado
import co.edu.unab.chatbotacademico.ui.gradienteNaranja
import co.edu.unab.chatbotacademico.ui.nombreEstado
import co.edu.unab.chatbotacademico.ui.renderMarkdown

private data class Sugerencia(val emoji: String, val titulo: String, val pregunta: String)

private val sugerencias = listOf(
    Sugerencia("📊", "Mis notas en gráfica", "Muéstrame mis notas en gráfica"),
    Sugerencia("🎯", "Mi riesgo académico", "¿Cuál es mi riesgo académico?"),
    Sugerencia("📝", "Tareas en TEMA", "¿Qué tareas tengo en TEMA?"),
    Sugerencia("💳", "Pagar matrícula", "Quiero pagar mi matrícula"),
    Sugerencia("🏟️", "Reservar espacio", "Quiero reservar un espacio"),
    Sugerencia("📚", "Renovar libro", "¿Cómo renuevo mi préstamo de biblioteca?"),
    Sugerencia("📰", "Noticias de hoy", "Noticias de tecnología de hoy"),
    Sugerencia("🗓️", "Calendario", "¿Cuándo son las inscripciones?"),
)

@Composable
internal fun BienvenidaChat(nombre: String?, enviar: (String) -> Unit) {
    SuperficieUnab(forma = FormaContenedor) {
        Column(
            Modifier.fillMaxWidth().background(Brush.linearGradient(
                0f to SuperficieSuave, 0.68f to Superficie,
            )).padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(13.dp),
        ) {
            AvatarUnab(Modifier.size(44.dp))
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(
                    if (nombre.isNullOrBlank()) "¡Hola! 👋" else "Hola, $nombre 👋",
                    style = MaterialTheme.typography.headlineMedium,
                )
                Text(
                    "Consulta tus notas, organiza tu día o resuelve un trámite.",
                    color = TextoApagado, style = MaterialTheme.typography.bodyMedium,
                )
            }
            Column(verticalArrangement = Arrangement.spacedBy(7.dp)) {
                sugerencias.chunked(2).forEach { fila ->
                    Row(
                        Modifier.fillMaxWidth().height(IntrinsicSize.Min),
                        horizontalArrangement = Arrangement.spacedBy(7.dp),
                    ) {
                        fila.forEach { sugerencia ->
                            Surface(
                                onClick = { enviar(sugerencia.pregunta) },
                                modifier = Modifier.weight(1f).fillMaxHeight().heightIn(min = 48.dp),
                                shape = RoundedCornerShape(16.dp),
                                color = Superficie,
                                border = BorderStroke(1.dp, Borde),
                            ) {
                                Row(
                                    Modifier.padding(horizontal = 9.dp, vertical = 7.dp),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(7.dp),
                                ) {
                                    Text(sugerencia.emoji)
                                    Text(
                                        sugerencia.titulo, style = MaterialTheme.typography.labelLarge,
                                        fontWeight = FontWeight.SemiBold,
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
internal fun MensajeChat(mensaje: Msg, animados: MutableSet<Long>, extras: @Composable () -> Unit) {
    val visible = remember(mensaje.id) {
        MutableTransitionState(mensaje.id in animados).apply { targetState = true }
    }
    LaunchedEffect(mensaje.id) { animados.add(mensaje.id) }
    AnimatedVisibility(
        visibleState = visible,
        enter = fadeIn(tween(230)) + slideInVertically(tween(260)) { it.coerceAtMost(100) / 5 },
    ) {
        Column(Modifier.fillMaxWidth().animateContentSize(), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            if (mensaje.fromUser) BurbujaUsuario(mensaje) else BurbujaAsistente(mensaje)
            extras()
        }
    }
}

@Composable
private fun BurbujaUsuario(mensaje: Msg) {
    Box(Modifier.fillMaxWidth().padding(start = 42.dp), contentAlignment = Alignment.CenterEnd) {
        Column(
            Modifier.widthIn(max = 410.dp).gradienteNaranja(FormaTarjeta).padding(horizontal = 15.dp, vertical = 11.dp),
            verticalArrangement = Arrangement.spacedBy(7.dp),
        ) {
            mensaje.miniatura?.let {
                Image(
                    it.asImageBitmap(), "Imagen enviada",
                    Modifier.widthIn(max = 200.dp).heightIn(max = 150.dp).clip(RoundedCornerShape(11.dp)),
                )
            }
            if (mensaje.text.isNotBlank()) {
                SelectionContainer {
                    Text(mensaje.text, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.bodyMedium)
                }
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun BurbujaAsistente(mensaje: Msg) {
    if (mensaje.text.isBlank() && mensaje.intencion == null && mensaje.fuentes.isEmpty()) return
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        AvatarUnab(Modifier.size(30.dp))
        TarjetaRespuesta(Modifier.weight(1f)) {
            mensaje.intencion?.let { Insignia(intencionVisible(it)) }
            if (mensaje.text.isNotBlank()) {
                val markdown = remember(mensaje.text) { renderMarkdown(mensaje.text) }
                SelectionContainer { Text(markdown, color = Texto, style = MaterialTheme.typography.bodyMedium) }
            }
            if (mensaje.fuentes.isNotEmpty()) {
                Text("Fuentes", style = MaterialTheme.typography.labelMedium, color = TextoApagado)
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(5.dp),
                    verticalArrangement = Arrangement.spacedBy(4.dp),
                ) {
                    mensaje.fuentes.distinct().filter { it.isNotBlank() }.forEach {
                        Insignia(it, TextoApagado, SuperficieSuave)
                    }
                }
            }
        }
    }
}

@Composable
internal fun Escribiendo() {
    val rebote = rememberInfiniteTransition(label = "Respuesta del asistente")
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
        AvatarUnab(Modifier.size(30.dp))
        Row(
            Modifier.background(Superficie, FormaTarjeta).padding(horizontal = 12.dp, vertical = 10.dp)
                .semantics { liveRegion = LiveRegionMode.Polite },
            horizontalArrangement = Arrangement.spacedBy(5.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            repeat(3) { indice ->
                val salto by rebote.animateFloat(
                    initialValue = 0f, targetValue = -5f,
                    animationSpec = infiniteRepeatable(
                        animation = tween(360, easing = FastOutSlowInEasing),
                        repeatMode = RepeatMode.Reverse,
                        initialStartOffset = StartOffset(indice * 100),
                    ),
                    label = "Punto ${indice + 1}",
                )
                Box(Modifier.size(6.dp).graphicsLayer { translationY = salto.dp.toPx() }.background(MoradoFuerte, CircleShape))
            }
            Text(
                "Consultando…", Modifier.padding(start = 3.dp),
                style = MaterialTheme.typography.bodySmall, color = TextoApagado,
            )
        }
    }
}

private fun intencionVisible(intencion: String): String = when (intencion) {
    "tramites" -> "Trámites"
    "bloqueado" -> "Consulta restringida"
    "ruta" -> "Ruta académica"
    else -> nombreEstado(intencion)
}
