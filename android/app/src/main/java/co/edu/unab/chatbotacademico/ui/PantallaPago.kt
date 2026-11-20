package co.edu.unab.chatbotacademico.ui

import android.graphics.Bitmap
import android.webkit.CookieManager
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import co.edu.unab.chatbotacademico.R
import co.edu.unab.chatbotacademico.data.webUrl
import co.edu.unab.chatbotacademico.ui.componentes.Insignia
import co.edu.unab.chatbotacademico.ui.componentes.TarjetaRespuesta

@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun PantallaPago(url: String, cerrar: () -> Unit) {
    BackHandler(onBack = cerrar)
    var intento by remember(url) { mutableIntStateOf(0) }
    Scaffold(
        containerColor = Crema,
        topBar = {
            TopAppBar(
                title = {
                    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                        Row(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
                            Icon(painterResource(R.drawable.ic_candado), null, Modifier.size(17.dp), tint = MoradoFuerte)
                            Text("Pago seguro · Bold", style = MaterialTheme.typography.titleMedium)
                        }
                        Insignia("Modo de pruebas")
                    }
                },
                navigationIcon = {
                    IconButton(onClick = cerrar) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "Volver al chat") }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Superficie),
            )
        },
    ) { padding ->
        key(url, intento) {
            var progreso by remember { mutableIntStateOf(0) }
            var fallo by remember { mutableStateOf(false) }
            Box(Modifier.fillMaxSize().padding(padding)) {
                AndroidView(
                    modifier = Modifier.fillMaxSize(),
                    factory = { contexto ->
                        WebView(contexto).apply {
                            settings.javaScriptEnabled = true
                            settings.domStorageEnabled = true
                            settings.allowFileAccess = false
                            settings.allowContentAccess = false
                            CookieManager.getInstance().setAcceptThirdPartyCookies(this, true)
                            webChromeClient = object : WebChromeClient() {
                                override fun onProgressChanged(view: WebView, newProgress: Int) {
                                    progreso = newProgress
                                }
                            }
                            webViewClient = object : WebViewClient() {
                                override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                                    val destino = webUrl(request.url.toString()) ?: return true
                                    val origen = webUrl(url) ?: return true
                                    return !destino.isHttps && (origen.isHttps || destino.host != origen.host || destino.port != origen.port)
                                }

                                override fun onPageStarted(view: WebView, url: String?, favicon: Bitmap?) {
                                    progreso = 0
                                    fallo = false
                                }

                                override fun onPageFinished(view: WebView, url: String?) {
                                    progreso = 100
                                }

                                override fun onReceivedError(view: WebView, request: WebResourceRequest, error: WebResourceError) {
                                    if (request.isForMainFrame) fallo = true
                                }

                                override fun onReceivedHttpError(view: WebView, request: WebResourceRequest, response: WebResourceResponse) {
                                    if (request.isForMainFrame) fallo = true
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
                if (!fallo && progreso < 100) {
                    LinearProgressIndicator(
                        progress = { progreso / 100f }, modifier = Modifier.fillMaxWidth(),
                        color = UnabOrange, trackColor = SuperficieFuerte,
                    )
                }
                if (fallo) {
                    Box(Modifier.align(Alignment.Center).padding(18.dp)) {
                        TarjetaRespuesta {
                            Text("No se pudo abrir el pago.", style = MaterialTheme.typography.titleMedium)
                            TextButton(onClick = { intento++ }) { Text("Reintentar") }
                        }
                    }
                }
            }
        }
    }
}
