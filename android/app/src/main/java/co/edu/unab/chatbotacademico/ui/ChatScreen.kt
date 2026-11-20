package co.edu.unab.chatbotacademico.ui

import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.WindowInsetsSides
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.only
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import co.edu.unab.chatbotacademico.R
import co.edu.unab.chatbotacademico.UiState
import co.edu.unab.chatbotacademico.data.ChatApiException
import co.edu.unab.chatbotacademico.data.Hoy
import co.edu.unab.chatbotacademico.data.checkoutUrl
import co.edu.unab.chatbotacademico.data.personasRespaldo
import co.edu.unab.chatbotacademico.ui.componentes.AvatarUnab
import co.edu.unab.chatbotacademico.ui.componentes.BienvenidaChat
import co.edu.unab.chatbotacademico.ui.componentes.Composer
import co.edu.unab.chatbotacademico.ui.componentes.Escribiendo
import co.edu.unab.chatbotacademico.ui.componentes.Insignia
import co.edu.unab.chatbotacademico.ui.componentes.MensajeChat
import co.edu.unab.chatbotacademico.ui.componentes.TarjetaRespuesta
import kotlinx.coroutines.CancellationException

@Composable
fun ChatScreen(
    st: UiState,
    onSend: (String, Boolean) -> Unit,
    onRetry: () -> Unit,
    onNew: () -> Unit,
    onLogout: () -> Unit,
    onAdjuntar: (Uri) -> Unit,
    onQuitarAdjunto: () -> Unit,
    onPago: (String) -> Unit,
    onCerrarPago: () -> Unit,
    onConsultarPago: (String) -> Unit,
    cargarHoy: suspend () -> Hoy,
) {
    var input by rememberSaveable(st.codigo) { mutableStateOf("") }
    var verHoy by rememberSaveable(st.codigo) { mutableStateOf(false) }
    var intentoAgenda by remember(st.codigo) { mutableIntStateOf(0) }
    var agenda by remember(st.codigo) { mutableStateOf<Hoy?>(null) }
    var errorAgenda by remember(st.codigo) { mutableStateOf<String?>(null) }
    val listState = rememberLazyListState()
    val animados = remember { mutableSetOf<Long>() }
    val enviarSugerencia: (String) -> Unit = { onSend(it, false) }

    LaunchedEffect(st.codigo, st.baseUrl, intentoAgenda) {
        errorAgenda = null
        agenda = try {
            cargarHoy()
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            errorAgenda = (e as? ChatApiException)?.message ?: "No se pudo cargar tu agenda. Revisa la conexión."
            null
        }
    }

    val pagoUrl = st.ordenAbierta?.let { checkoutUrl(st.baseUrl, it) }
    if (pagoUrl != null) {
        PantallaPago(pagoUrl, onCerrarPago)
        return
    }

    val perfil = personasRespaldo.firstOrNull { it.codigo == st.codigo }
    val estudiante = agenda?.estudiante
    val nombre = estudiante?.nombre?.let { completo ->
        perfil?.nombre?.takeIf { completo == it || completo.startsWith("$it ") }
            ?: completo.substringBefore(' ')
    } ?: perfil?.nombre
    val programa = estudiante?.programa ?: perfil?.programa
    val identidad = listOfNotNull(nombre, programa).joinToString(" · ").ifEmpty { st.codigo.orEmpty() }

    LaunchedEffect(st.messages.size, st.typing, st.error) {
        val total = st.messages.size + (if (st.typing) 1 else 0) + (if (st.error != null) 1 else 0)
        if (total > 0) listState.animateScrollToItem(total - 1)
    }

    Scaffold(
        modifier = Modifier.windowInsetsPadding(WindowInsets.safeDrawing.only(WindowInsetsSides.Horizontal)),
        containerColor = Color.Transparent,
        contentWindowInsets = WindowInsets(0, 0, 0, 0),
        topBar = {
            BarraChat(
                identidad,
                onHoy = {
                    if (agenda != null || errorAgenda != null) intentoAgenda++
                    verHoy = true
                },
                onNew = { input = ""; animados.clear(); onNew() },
                onLogout = onLogout,
            )
        },
        bottomBar = {
            Composer(st, input, { input = it }, onAdjuntar, onQuitarAdjunto) {
                onSend(input, true)
                input = ""
            }
        },
    ) { padding ->
        Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.TopCenter) {
            LazyColumn(
                state = listState,
                modifier = Modifier.widthIn(max = 660.dp).fillMaxSize(),
                contentPadding = PaddingValues(start = 14.dp, top = 16.dp, end = 14.dp, bottom = 20.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp),
            ) {
                if (st.messages.isEmpty() && !st.typing) {
                    item { BienvenidaChat(nombre, enviarSugerencia) }
                }
                items(st.messages, key = { it.id }) { mensaje ->
                    MensajeChat(mensaje, animados) {
                        mensaje.acciones.forEach {
                            TarjetaAccion(it, st.baseUrl, st.pagos, st.typing, enviarSugerencia, onPago, onConsultarPago)
                        }
                        mensaje.graficas.forEach { GraficaChat(it) }
                        mensaje.qrDetectados.filter { it.isNotBlank() }.distinct().forEach { QrDetectado(it) }
                    }
                }
                if (st.typing) item { Escribiendo() }
                st.error?.let { error ->
                    item {
                        TarjetaRespuesta(color = PeligroSuave) {
                            Text(error, color = Peligro, style = MaterialTheme.typography.bodyMedium)
                            TextButton(onClick = onRetry) { Text("Reintentar") }
                        }
                    }
                }
            }
        }
    }

    if (verHoy) {
        PanelHoy(
            agenda = agenda,
            error = errorAgenda,
            ocupado = st.typing,
            pagos = st.pagos,
            onPago = onPago,
            onConsultarPago = onConsultarPago,
            reintentar = { intentoAgenda++ },
            renovar = {
                verHoy = false
                enviarSugerencia("¿Cómo renuevo mi préstamo de biblioteca?")
            },
            cerrar = { verHoy = false },
        )
    }
}

@Composable
private fun BarraChat(identidad: String, onHoy: () -> Unit, onNew: () -> Unit, onLogout: () -> Unit) {
    var menu by remember { mutableStateOf(false) }
    Column(Modifier.fillMaxWidth().background(Superficie.copy(alpha = 0.86f)).statusBarsPadding()) {
        Row(
            Modifier.fillMaxWidth().padding(start = 14.dp, end = 2.dp, top = 8.dp, bottom = 10.dp),
            horizontalArrangement = Arrangement.spacedBy(6.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            AvatarUnab(Modifier.size(36.dp))
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                Text("Asistente UNAB 360", style = MaterialTheme.typography.titleMedium)
                Insignia(identidad)
            }
            TextButton(onHoy, shape = CircleShape, contentPadding = PaddingValues(horizontal = 8.dp)) {
                Row(horizontalArrangement = Arrangement.spacedBy(4.dp), verticalAlignment = Alignment.CenterVertically) {
                    Icon(painterResource(R.drawable.ic_calendario), null, Modifier.size(17.dp))
                    Text("Hoy", style = MaterialTheme.typography.labelLarge)
                }
            }
            Box {
                IconButton(onClick = { menu = true }) { Icon(Icons.Default.MoreVert, "Menú de conversación") }
                DropdownMenu(
                    expanded = menu, onDismissRequest = { menu = false },
                    shape = FormaTarjeta, containerColor = Superficie,
                ) {
                    DropdownMenuItem(text = { Text("Nueva conversación") }, onClick = { menu = false; onNew() })
                    DropdownMenuItem(text = { Text("Cerrar sesión") }, onClick = { menu = false; onLogout() })
                }
            }
        }
        HorizontalDivider(color = Borde)
    }
}
