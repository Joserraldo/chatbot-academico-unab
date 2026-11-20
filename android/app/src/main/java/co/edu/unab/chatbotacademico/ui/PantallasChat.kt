package co.edu.unab.chatbotacademico.ui

import android.graphics.Bitmap
import android.webkit.CookieManager
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import co.edu.unab.chatbotacademico.ConsultaPago
import co.edu.unab.chatbotacademico.data.ChatApiException
import co.edu.unab.chatbotacademico.data.Hoy
import co.edu.unab.chatbotacademico.data.webUrl
import kotlinx.coroutines.CancellationException
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.time.format.DateTimeParseException

@Composable
fun PantallaPago(url: String, cerrar: () -> Unit) {
    var intento by remember(url) { mutableIntStateOf(0) }
    PantallaSecundaria("Pago de prueba", cerrar) { padding ->
        key(url, intento) {
            var cargando by remember { mutableStateOf(true) }
            var fallo by remember { mutableStateOf(false) }
            Box(Modifier.fillMaxSize().padding(padding)) {
                AndroidView(
                    modifier = Modifier.fillMaxSize(),
                    factory = { context ->
                        WebView(context).apply {
                            settings.javaScriptEnabled = true
                            settings.domStorageEnabled = true
                            settings.allowFileAccess = false
                            settings.allowContentAccess = false
                            CookieManager.getInstance().setAcceptThirdPartyCookies(this, true)
                            webViewClient = object : WebViewClient() {
                                override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                                    val destino = webUrl(request.url.toString()) ?: return true
                                    val origen = webUrl(url) ?: return true
                                    return !destino.isHttps && (origen.isHttps || destino.host != origen.host || destino.port != origen.port)
                                }

                                override fun onPageStarted(view: WebView, url: String?, favicon: Bitmap?) {
                                    cargando = true
                                    fallo = false
                                }

                                override fun onPageFinished(view: WebView, url: String?) {
                                    cargando = false
                                }

                                override fun onReceivedError(view: WebView, request: WebResourceRequest, error: WebResourceError) {
                                    if (request.isForMainFrame) {
                                        cargando = false
                                        fallo = true
                                    }
                                }

                                override fun onReceivedHttpError(view: WebView, request: WebResourceRequest, response: WebResourceResponse) {
                                    if (request.isForMainFrame) {
                                        cargando = false
                                        fallo = true
                                    }
                                }
                            }
                            loadUrl(url)
                        }
                    },
                    onRelease = {
                        it.stopLoading()
                        it.destroy()
                    },
                )
                if (cargando) CircularProgressIndicator(Modifier.align(Alignment.Center))
                if (fallo) {
                    Box(Modifier.align(Alignment.Center).padding(20.dp)) {
                        TarjetaRespuesta {
                            Text("No se pudo abrir el pago.")
                            TextButton(onClick = { intento++ }) { Text("Reintentar") }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun PantallaHoy(
    cargarHoy: suspend () -> Hoy,
    pagos: Map<String, ConsultaPago>,
    onPago: (String) -> Unit,
    onConsultarPago: (String) -> Unit,
    cerrar: () -> Unit,
) {
    var intento by remember { mutableIntStateOf(0) }
    var datos by remember { mutableStateOf<Hoy?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    val contexto = LocalContext.current
    LaunchedEffect(intento) {
        error = null
        datos = try {
            cargarHoy()
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            error = (e as? ChatApiException)?.message ?: "No se pudo cargar tu agenda. Revisa la conexión."
            null
        }
    }
    PantallaSecundaria("Hoy en tu U", cerrar) { padding ->
        val agenda = datos
        LazyColumn(
            Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            if (agenda == null) {
                item {
                    if (error == null) CircularProgressIndicator()
                    else TarjetaRespuesta {
                        Text(error.orEmpty())
                        TextButton(onClick = { intento++ }) { Text("Reintentar") }
                    }
                }
            } else {
                item {
                    SeccionHoy("Tareas en TEMA", agenda.tareas, "Sin tareas pendientes.") {
                        Text(it.titulo, style = MaterialTheme.typography.titleSmall)
                        Text("${it.curso} · ${fechaLocal(it.fecha)} · ${nombreEstado(it.estado)}")
                    }
                }
                item {
                    SeccionHoy("Evaluaciones docentes", agenda.evaluaciones, "Sin evaluaciones pendientes.") {
                        Text(it.curso, style = MaterialTheme.typography.titleSmall)
                        Text("${it.docente} · Hasta ${it.fecha}")
                    }
                }
                item {
                    SeccionHoy("Préstamos de biblioteca", agenda.prestamos, "Sin préstamos registrados.") {
                        Text(it.titulo, style = MaterialTheme.typography.titleSmall)
                        Text("Vence ${it.fecha} · ${nombreEstado(it.estado)}")
                        if (it.multa > 0) Text("Multa · ${cop(it.multa)}")
                    }
                }
                item {
                    Text("Pagos pendientes", style = MaterialTheme.typography.titleMedium)
                    if (agenda.pagos.isEmpty()) Text("Sin pagos pendientes.")
                }
                agenda.pagos.forEach { pago ->
                    item(key = pago.orderId) { TarjetaPago(pago, pagos[pago.orderId], onPago, onConsultarPago) }
                }
                item {
                    SeccionHoy("Noticias", agenda.noticias, "Sin noticias disponibles.") {
                        Text(it.titulo, style = MaterialTheme.typography.titleSmall)
                        TextButton(onClick = { abrirEnlace(contexto, it.url) }) { Text("Leer en ${it.fuente}") }
                    }
                }
            }
        }
    }
}

@Composable
private fun <T> SeccionHoy(
    titulo: String,
    items: List<T>,
    vacio: String,
    contenido: @Composable (T) -> Unit,
) {
    TarjetaRespuesta {
        Text(titulo, style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary)
        if (items.isEmpty()) Text(vacio, style = MaterialTheme.typography.bodyMedium)
        items.forEachIndexed { i, item ->
            if (i > 0) HorizontalDivider()
            contenido(item)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun PantallaSecundaria(titulo: String, cerrar: () -> Unit, contenido: @Composable (PaddingValues) -> Unit) {
    BackHandler(onBack = cerrar)
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(titulo) },
                navigationIcon = {
                    IconButton(onClick = cerrar) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "Volver") }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary,
                    navigationIconContentColor = MaterialTheme.colorScheme.onPrimary,
                ),
            )
        },
        content = contenido,
    )
}

private val zonaUnab = ZoneId.of("America/Bogota")
private val formatoFecha = DateTimeFormatter.ofPattern("dd/MM/yyyy HH:mm")

private fun fechaLocal(fecha: String): String = try {
    OffsetDateTime.parse(fecha).atZoneSameInstant(zonaUnab).format(formatoFecha)
} catch (_: DateTimeParseException) {
    fecha
}
