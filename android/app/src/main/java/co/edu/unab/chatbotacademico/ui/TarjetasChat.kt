package co.edu.unab.chatbotacademico.ui

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.net.Uri
import android.widget.Toast
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import co.edu.unab.chatbotacademico.ConsultaPago
import co.edu.unab.chatbotacademico.R
import co.edu.unab.chatbotacademico.data.Accion
import co.edu.unab.chatbotacademico.data.cargarQr
import co.edu.unab.chatbotacademico.data.webUrl
import co.edu.unab.chatbotacademico.ui.componentes.EmojiEnCirculo
import co.edu.unab.chatbotacademico.ui.componentes.Insignia
import co.edu.unab.chatbotacademico.ui.componentes.SuperficieUnab
import co.edu.unab.chatbotacademico.ui.componentes.TarjetaRespuesta
import kotlinx.coroutines.CancellationException
import java.text.NumberFormat
import java.util.Locale

@OptIn(ExperimentalLayoutApi::class)
@Composable
internal fun TarjetaAccion(
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
            EncabezadoAccion("🔗", accion.titulo, accion.descripcion)
            TextButton(onClick = { abrirEnlace(contexto, accion.url) }) { Text("Abrir ↗") }
        }
        is Accion.Qr -> TarjetaQr(accion, baseUrl)
        is Accion.Reserva -> TarjetaRespuesta {
            val horario = "${accion.fecha} · ${accion.horaInicio.take(5)}–${accion.horaFin.take(5)}"
            EncabezadoAccion("🏟️", accion.espacio, horario)
            EtiquetaEstado(accion.estado)
        }
        is Accion.Sugerencias -> FlowRow(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalArrangement = Arrangement.spacedBy(2.dp),
        ) {
            accion.opciones.filter { it.isNotBlank() }.forEach { opcion ->
                ChipAccion(opcion, !ocupado) { onSugerencia(opcion) }
            }
        }
    }
}

@Composable
private fun EncabezadoAccion(emoji: String, titulo: String, descripcion: String = "") {
    Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
        EmojiEnCirculo(emoji)
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(titulo, style = MaterialTheme.typography.titleMedium)
            if (descripcion.isNotBlank()) {
                Text(descripcion, color = TextoApagado, style = MaterialTheme.typography.bodyMedium)
            }
        }
    }
}

@Composable
internal fun TarjetaPago(
    pago: Accion.Pago,
    consulta: ConsultaPago?,
    onPago: (String) -> Unit,
    onConsultar: (String) -> Unit,
    textoBoton: String = "Pagar con Bold",
) {
    val estado = consulta?.estado ?: pago.estado
    SuperficieUnab {
        Column {
            Box(
                Modifier.fillMaxWidth().height(6.dp).background(
                    Brush.horizontalGradient(listOf(UnabPurple, UnabOrange)),
                ),
            )
            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                EncabezadoAccion("💳", nombreConcepto(pago.concepto), pago.descripcion)
                Text(cop(pago.monto), style = MaterialTheme.typography.headlineMedium)
                EtiquetaEstado(estado)
                when {
                    consulta?.consultando == true -> Text(
                        "Consultando el estado del pago…",
                        color = TextoApagado, style = MaterialTheme.typography.bodySmall,
                    )
                    consulta?.error != null -> {
                        Text(consulta.error, color = Peligro, style = MaterialTheme.typography.bodySmall)
                        TextButton(onClick = { onConsultar(pago.orderId) }) { Text("Actualizar estado") }
                    }
                }
                if (estado == "pendiente") {
                    Button(
                        onClick = { onPago(pago.orderId) },
                        enabled = consulta?.consultando != true,
                        modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp),
                        shape = FormaBoton,
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF121212), contentColor = Superficie),
                    ) {
                        Row(horizontalArrangement = Arrangement.spacedBy(7.dp), verticalAlignment = Alignment.CenterVertically) {
                            Icon(painterResource(R.drawable.ic_candado), null, Modifier.size(16.dp))
                            Text(textoBoton)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun EtiquetaEstado(estado: String) {
    val (color, fondo) = when (estado) {
        "aprobado", "confirmada" -> TextoExito to Exito.copy(alpha = 0.12f)
        "rechazado", "fallido", "anulado", "cancelada" -> Peligro to PeligroSuave
        else -> Color(0xFF815000) to SuperficieFuerte
    }
    Insignia(nombreEstado(estado), color, fondo)
}

private data class QrCargado(val bitmap: Bitmap? = null, val cargando: Boolean = true)

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
        Box(
            Modifier.fillMaxWidth().clip(FormaTarjeta).background(SuperficieSuave).padding(12.dp),
            contentAlignment = Alignment.Center,
        ) {
            val bitmap = qr.bitmap
            when {
                qr.cargando -> Box(Modifier.height(120.dp), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator()
                }
                bitmap != null -> Image(
                    bitmap.asImageBitmap(), contentDescription = "Código QR para ${accion.titulo}",
                    modifier = Modifier.widthIn(max = 224.dp).fillMaxWidth().height(224.dp)
                        .background(Superficie, FormaBoton).border(1.dp, Borde, FormaBoton).padding(12.dp),
                )
                else -> Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text("No se pudo cargar el código QR.")
                    TextButton(onClick = { intento++ }) { Text("Reintentar QR") }
                }
            }
        }
        Text("Escanéalo con tu celular", style = MaterialTheme.typography.labelLarge, color = TextoApagado)
        TextButton(
            onClick = { abrirEnlace(contexto, accion.url) },
            contentPadding = PaddingValues(0.dp),
        ) { Text(accion.url) }
    }
}

@Composable
private fun ChipAccion(texto: String, habilitado: Boolean = true, onClick: () -> Unit) {
    OutlinedButton(
        onClick = onClick, enabled = habilitado, shape = CircleShape,
        border = BorderStroke(1.dp, if (habilitado) BordeMorado else Borde),
        colors = ButtonDefaults.outlinedButtonColors(containerColor = Superficie, contentColor = MoradoFuerte),
    ) { Text(texto, maxLines = 3, overflow = TextOverflow.Ellipsis) }
}

@Composable
internal fun QrDetectado(url: String) {
    val contexto = LocalContext.current
    ChipAccion("QR detectado · $url", webUrl(url) != null) { abrirEnlace(contexto, url) }
}

internal fun abrirEnlace(contexto: Context, url: String) {
    val enlace = webUrl(url)
    if (enlace != null) {
        try {
            contexto.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(enlace.toString())))
            return
        } catch (_: ActivityNotFoundException) {
            // Algunos dispositivos no tienen un navegador instalado.
        }
    }
    Toast.makeText(contexto, "No se pudo abrir el enlace.", Toast.LENGTH_SHORT).show()
}

internal fun cop(monto: Long): String =
    "$" + NumberFormat.getIntegerInstance(Locale.forLanguageTag("es-CO")).apply {
        isGroupingUsed = true
    }.format(monto) + " COP"

internal fun nombreEstado(estado: String): String = when (estado) {
    "pendiente_pago" -> "Pendiente de pago"
    else -> estado.replace('_', ' ').replaceFirstChar { it.titlecase() }
}

private fun nombreConcepto(concepto: String): String = when (concepto) {
    "matricula" -> "Matrícula"
    "reserva" -> "Reserva"
    "multa_biblioteca" -> "Multa de biblioteca"
    else -> nombreEstado(concepto)
}
