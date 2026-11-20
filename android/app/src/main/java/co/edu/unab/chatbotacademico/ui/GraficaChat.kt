package co.edu.unab.chatbotacademico.ui

import android.graphics.Paint
import android.text.TextPaint
import android.text.TextUtils
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.clipRect
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import co.edu.unab.chatbotacademico.data.Grafica
import co.edu.unab.chatbotacademico.ui.componentes.TarjetaRespuesta
import java.text.NumberFormat
import java.util.Locale
import kotlin.math.abs
import kotlin.math.ceil

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun GraficaChat(grafica: Grafica) {
    val palette = listOf(UnabPurple, NaranjaFuerte, TextoExito, Color(0xFFC65C8E))
    val progreso = remember(grafica) { Animatable(0f) }
    val format = remember { NumberFormat.getNumberInstance(Locale.forLanguageTag("es-CO")).apply { maximumFractionDigits = 2 } }
    val labels = grafica.labels
    val series = grafica.series
    val valores = remember(grafica) {
        series.flatMap { it.datos.take(labels.size) }.filterNotNull().filter { it.isFinite() }
    }
    val doughnut = grafica.tipo == "doughnut"
    val hayDatos = valores.any { !doughnut || it > 0.0 }
    LaunchedEffect(progreso, hayDatos) {
        if (hayDatos) progreso.animateTo(1f, tween(700))
    }

    TarjetaRespuesta {
        Text(grafica.titulo, style = MaterialTheme.typography.titleMedium)
        grafica.unidad?.takeIf { it.isNotBlank() }?.let {
            Text(it, style = MaterialTheme.typography.labelMedium, color = TextoTenue)
        }
        if (hayDatos) {
            val accesible = remember(grafica) {
                series.joinToString(". ") { serie ->
                    val puntos = labels.zip(serie.datos).mapNotNull { (label, dato) ->
                        dato?.takeIf(Double::isFinite)?.let { "$label, ${format.format(it)}" }
                    }
                    "${serie.nombre}: ${puntos.joinToString("; ")}"
                }
            }
            Canvas(
                Modifier.fillMaxWidth().height(184.dp).semantics { contentDescription = accesible },
            ) {
                if (doughnut) {
                    dibujarAnillos(grafica, palette, progreso.value)
                } else {
                    val escalaNota = grafica.unidad?.contains("0-5") == true
                    val minimo = minOf(0.0, valores.min())
                    val maximo = maxOf(if (escalaNota) 5.0 else 0.0, valores.max())
                    dibujarEjes(grafica, palette, Borde, TextoApagado, format, minimo, maximo, progreso.value)
                }
            }
            FlowRow(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalArrangement = Arrangement.spacedBy(5.dp),
            ) {
                val leyenda = if (doughnut) labels else series.map { it.nombre }
                leyenda.forEachIndexed { indice, nombre ->
                    Row(horizontalArrangement = Arrangement.spacedBy(5.dp), verticalAlignment = Alignment.CenterVertically) {
                        Box(Modifier.size(10.dp).background(palette[indice % palette.size], CircleShape))
                        Text(nombre, style = MaterialTheme.typography.labelMedium)
                    }
                }
            }
            if (doughnut && series.size > 1) {
                Text(
                    "Del centro hacia afuera: " + series.joinToString(" · ") { it.nombre },
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        } else {
            Text("No hay datos para esta gráfica.", style = MaterialTheme.typography.bodySmall)
        }
        grafica.nota?.takeIf { it.isNotBlank() }?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
    }
}

private fun DrawScope.dibujarEjes(
    grafica: Grafica,
    palette: List<Color>,
    ejes: Color,
    texto: Color,
    formato: NumberFormat,
    minimo: Double,
    maximo: Double,
    progreso: Float,
) {
    val rango = (maximo - minimo).takeIf { it > 0.0 } ?: 1.0
    val paint = TextPaint(Paint.ANTI_ALIAS_FLAG).apply {
        color = texto.toArgb()
        textSize = 10.sp.toPx()
        textAlign = Paint.Align.RIGHT
    }
    val izquierda = maxOf(paint.measureText(formato.format(minimo)), paint.measureText(formato.format(minimo + rango))) + 8.dp.toPx()
    val derecha = size.width - 4.dp.toPx()
    if (izquierda >= derecha) return
    val arriba = 13.dp.toPx()
    val abajo = size.height - 22.dp.toPx()
    val paso = (derecha - izquierda) / grafica.labels.size
    fun x(i: Int) = izquierda + paso * (i + 0.5f)
    fun y(valor: Double) = abajo - ((valor - minimo) / rango * (abajo - arriba)).toFloat()
    val canvas = drawContext.canvas.nativeCanvas

    for (i in 0..3) {
        val valor = minimo + rango * i / 3
        val nivel = y(valor)
        drawLine(ejes, Offset(izquierda, nivel), Offset(derecha, nivel))
        canvas.drawText(formato.format(valor), izquierda - 4.dp.toPx(), nivel - (paint.ascent() + paint.descent()) / 2, paint)
    }
    drawLine(ejes, Offset(izquierda, arriba), Offset(izquierda, abajo))
    if (minimo < 0 && maximo > 0) {
        drawLine(ejes, Offset(izquierda, y(0.0)), Offset(derecha, y(0.0)), 2.dp.toPx())
    }

    paint.textAlign = Paint.Align.CENTER
    val salto = ceil(grafica.labels.size / 5.0).toInt()
    grafica.labels.forEachIndexed { i, nombre ->
        if (i % salto == 0) {
            val visible = TextUtils.ellipsize(nombre, paint, paso * salto * 0.90f, TextUtils.TruncateAt.END)
            val margen = paint.measureText(visible.toString()) / 2
            val centro = x(i).coerceIn(margen, size.width - margen)
            canvas.drawText(visible.toString(), centro, size.height - 4.dp.toPx(), paint)
        }
    }

    if (grafica.tipo == "line") {
        clipRect(right = izquierda + (size.width - izquierda) * progreso) {
            grafica.series.forEachIndexed { indice, serie ->
                val color = palette[indice % palette.size]
                var anterior: Offset? = null
                serie.datos.take(grafica.labels.size).forEachIndexed { i, valor ->
                    val punto = valor?.takeIf(Double::isFinite)?.let { Offset(x(i), y(it)) }
                    if (punto != null) {
                        anterior?.let { drawLine(color, it, punto, 2.dp.toPx()) }
                        drawCircle(color, 3.dp.toPx(), punto)
                    }
                    anterior = punto
                }
            }
        }
        return
    }

    val anchoGrupo = paso * 0.76f
    val anchoBarra = anchoGrupo / grafica.series.size
    val base = y(0.0)
    grafica.series.forEachIndexed { indice, serie ->
        val color = palette[indice % palette.size]
        serie.datos.take(grafica.labels.size).forEachIndexed { i, valor ->
            if (valor != null && valor.isFinite()) {
                val extremo = y(valor * progreso)
                val borde = x(i) - anchoGrupo / 2 + anchoBarra * indice
                drawRoundRect(
                    color, Offset(borde, minOf(extremo, base)),
                    Size(anchoBarra * 0.88f, abs(extremo - base)), CornerRadius(3.dp.toPx()),
                )
            }
        }
    }
}

private fun DrawScope.dibujarAnillos(grafica: Grafica, palette: List<Color>, progreso: Float) {
    val radioMaximo = size.minDimension / 2 - 4.dp.toPx()
    val paso = radioMaximo * 0.62f / grafica.series.size
    grafica.series.forEachIndexed { indice, serie ->
        val valores = serie.datos.take(grafica.labels.size).map { it?.takeIf { n -> n.isFinite() && n > 0 } ?: 0.0 }
        val total = valores.sum()
        if (total > 0.0) {
            val radio = radioMaximo * 0.38f + paso * (indice + 0.5f)
            var inicio = -90f
            valores.forEachIndexed { i, valor ->
                val giro = (360 * valor / total).toFloat()
                val visible = minOf(giro, 360f * progreso - (inicio + 90f))
                if (visible > 0f) {
                    drawArc(
                        palette[i % palette.size], inicio, visible, false,
                        topLeft = Offset(center.x - radio, center.y - radio),
                        size = Size(radio * 2, radio * 2),
                        style = Stroke(paso * 0.86f),
                    )
                }
                inicio += giro
            }
        }
    }
}
