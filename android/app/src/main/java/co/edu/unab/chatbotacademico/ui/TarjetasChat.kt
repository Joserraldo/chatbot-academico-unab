package co.edu.unab.chatbotacademico.ui

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.Toast
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedCard
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import co.edu.unab.chatbotacademico.ConsultaPago
import co.edu.unab.chatbotacademico.data.Accion
import co.edu.unab.chatbotacademico.data.cargarQr
import co.edu.unab.chatbotacademico.data.webUrl
import kotlinx.coroutines.CancellationException
import java.text.NumberFormat
import java.util.Locale

@Composable
fun TarjetaAccion(
    accion: Accion,
    baseUrl: String,
    pagos: Map<String, ConsultaPago>,
    ocupado: Boolean,
    onSugerencia: (String) -> Unit,
    onPago: (String) -> Unit,
    onConsultarPago: (String) -> Unit,
) {
    val contexto = LocalContext.current
    when (accion) {
        is Accion.Pago -> TarjetaPago(accion, pagos[accion.orderId], onPago, onConsultarPago)
        is Accion.Enlace -> TarjetaRespuesta {
            Text(accion.titulo, style = MaterialTheme.typography.titleMedium)
            if (accion.descripcion.isNotBlank()) Text(accion.descripcion, style = MaterialTheme.typography.bodyMedium)
            TextButton(onClick = { abrirEnlace(contexto, accion.url) }) { Text("Abrir enlace") }
        }
        is Accion.Qr -> TarjetaQr(accion, baseUrl)
        is Accion.Reserva -> TarjetaRespuesta {
            Text(accion.espacio, style = MaterialTheme.typography.titleMedium)
            Text("${accion.fecha} · ${accion.horaInicio.take(5)}–${accion.horaFin.take(5)}")
            EtiquetaEstado(accion.estado)
        }
        is Accion.Sugerencias -> Row(
            Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            accion.opciones.filter { it.isNotBlank() }.forEach { opcion ->
                AssistChip(
                    onClick = { onSugerencia(opcion) },
                    enabled = !ocupado,
                    label = { Text(opcion) },
                )
            }
        }
    }
}

@Composable
fun TarjetaPago(pago: Accion.Pago, consulta: ConsultaPago?, onPago: (String) -> Unit, onConsultar: (String) -> Unit) {
    val estado = consulta?.estado ?: pago.estado
    TarjetaRespuesta {
        Text(nombreConcepto(pago.concepto), style = MaterialTheme.typography.titleMedium)
        if (pago.descripcion.isNotBlank()) Text(pago.descripcion, style = MaterialTheme.typography.bodyMedium)
        Text(cop(pago.monto), style = MaterialTheme.typography.headlineSmall, color = MaterialTheme.colorScheme.primary)
        EtiquetaEstado(estado)
        when {
            consulta?.consultando == true -> Text("Consultando el estado del pago…", style = MaterialTheme.typography.bodySmall)
            consulta?.error != null -> {
                Text(consulta.error, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                TextButton(onClick = { onConsultar(pago.orderId) }) { Text("Actualizar estado") }
            }
        }
        if (estado == "pendiente") {
            Button(onClick = { onPago(pago.orderId) }, enabled = consulta?.consultando != true) {
                Text("Pagar con Bold")
            }
        }
    }
}

@Composable
fun TarjetaRespuesta(contenido: @Composable () -> Unit) {
    OutlinedCard(Modifier.widthIn(max = 520.dp).fillMaxWidth(), shape = RoundedCornerShape(8.dp, 20.dp, 20.dp, 20.dp)) {
        Column(
            Modifier.fillMaxWidth().padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) { contenido() }
    }
}

@Composable
private fun EtiquetaEstado(estado: String) {
    val colores = MaterialTheme.colorScheme
    val (fondo, texto) = when (estado) {
        "aprobado", "confirmada" -> colores.primaryContainer to colores.onPrimaryContainer
        "rechazado", "fallido", "anulado", "cancelada" -> colores.errorContainer to colores.onErrorContainer
        else -> colores.secondaryContainer to colores.onSecondaryContainer
    }
    Text(
        nombreEstado(estado),
        modifier = Modifier.background(fondo, RoundedCornerShape(16.dp)).padding(horizontal = 10.dp, vertical = 4.dp),
        color = texto,
        style = MaterialTheme.typography.labelMedium,
    )
}

private data class QrCargado(val bitmap: android.graphics.Bitmap? = null, val cargando: Boolean = true)

@Composable
private fun TarjetaQr(accion: Accion.Qr, baseUrl: String) {
    val contexto = LocalContext.current
    var intento by remember { mutableIntStateOf(0) }
    val qr by produceState(QrCargado(), baseUrl, accion.imagen, intento) {
        value = QrCargado()
        val bitmap = try {
            cargarQr(baseUrl, accion.imagen)
        } catch (e: CancellationException) {
            throw e
        } catch (_: Exception) {
            null
        }
        value = QrCargado(bitmap, cargando = false)
    }
    TarjetaRespuesta {
        Text(accion.titulo, style = MaterialTheme.typography.titleMedium)
        Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
            val bitmap = qr.bitmap
            when {
                qr.cargando -> Box(Modifier.height(96.dp), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator()
                }
                bitmap != null -> Image(
                    bitmap.asImageBitmap(), contentDescription = "Código QR para ${accion.titulo}",
                    modifier = Modifier.widthIn(max = 232.dp).fillMaxWidth().height(232.dp).background(Color.White),
                )
                else -> Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text("No se pudo cargar el código QR.")
                    TextButton(onClick = { intento++ }) { Text("Reintentar QR") }
                }
            }
        }
        TextButton(onClick = { abrirEnlace(contexto, accion.url) }) { Text(accion.url) }
    }
}

@Composable
fun QrDetectado(url: String) {
    val contexto = LocalContext.current
    AssistChip(
        onClick = { abrirEnlace(contexto, url) },
        enabled = webUrl(url) != null,
        label = { Text("QR detectado: $url", maxLines = 2, overflow = TextOverflow.Ellipsis) },
    )
}

fun abrirEnlace(contexto: Context, url: String) {
    val enlace = webUrl(url)
    if (enlace != null) {
        try {
            contexto.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(enlace.toString())))
            return
        } catch (_: ActivityNotFoundException) {
            // Algunos emuladores no traen un navegador instalado.
        }
    }
    Toast.makeText(contexto, "No se pudo abrir el enlace.", Toast.LENGTH_SHORT).show()
}

fun cop(monto: Long): String =
    NumberFormat.getIntegerInstance(Locale.forLanguageTag("es-CO")).format(monto) + " COP"

fun nombreEstado(estado: String): String = estado.replace('_', ' ').replaceFirstChar { it.titlecase() }

private fun nombreConcepto(concepto: String): String = when (concepto) {
    "matricula" -> "Matrícula"
    "reserva" -> "Reserva"
    "multa_biblioteca" -> "Multa de biblioteca"
    else -> nombreEstado(concepto)
}
