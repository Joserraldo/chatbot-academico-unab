package co.edu.unab.chatbotacademico.ui

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material3.AssistChip
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import co.edu.unab.chatbotacademico.Msg
import co.edu.unab.chatbotacademico.R
import co.edu.unab.chatbotacademico.UiState
import co.edu.unab.chatbotacademico.data.Hoy
import co.edu.unab.chatbotacademico.data.checkoutUrl

private val SUGERENCIAS = listOf(
    "¿Cómo voy este semestre?",
    "Muéstrame mis notas en gráfica",
    "¿Qué tareas tengo en TEMA?",
    "Quiero pagar mi matrícula",
    "Reservar una sala de estudio mañana a las 10",
    "¿Cómo renuevo un libro de biblioteca?",
    "¿Cuál es mi riesgo académico?",
    "Noticias de tecnología de hoy",
    "¿Cómo va mi avance en el plan?",
    "¿Qué cursos de competencias digitales he tomado?",
    "¿Cuándo son las inscripciones?",
    "¿Qué es la insignia de competencias digitales?",
    "Novedades y convocatorias",
    "¿Cuántos semestres me faltan?",
    "¿Qué me recomiendas para el próximo semestre?",
)

@OptIn(ExperimentalMaterial3Api::class)
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
    var menu by remember { mutableStateOf(false) }
    var input by rememberSaveable { mutableStateOf("") }
    var verHoy by rememberSaveable { mutableStateOf(false) }
    val listState = rememberLazyListState()
    val photoPicker = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
        uri?.let(onAdjuntar)
    }
    val enviarSugerencia: (String) -> Unit = { onSend(it, false) }
    val puedeEnviar = !st.typing && !st.preparandoImagen && (input.isNotBlank() || st.adjunto != null)
    val enviar = {
        if (puedeEnviar) {
            onSend(input, true)
            input = ""
        }
    }

    val pagoUrl = st.ordenAbierta?.let { checkoutUrl(st.baseUrl, it) }
    if (pagoUrl != null) {
        PantallaPago(pagoUrl, onCerrarPago)
        return
    }
    if (verHoy) {
        PantallaHoy(cargarHoy, st.pagos, onPago, onConsultarPago) { verHoy = false }
        return
    }

    LaunchedEffect(st.messages.size, st.typing, st.error) {
        val extra = (if (st.typing) 1 else 0) + (if (st.error != null) 1 else 0)
        val total = st.messages.size + extra
        if (total > 0) listState.animateScrollToItem(total - 1)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Asistente UNAB 360", style = MaterialTheme.typography.titleMedium, maxLines = 1)
                        Text(st.codigo.orEmpty(), style = MaterialTheme.typography.labelSmall)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary,
                    actionIconContentColor = MaterialTheme.colorScheme.onPrimary,
                ),
                actions = {
                    TextButton(onClick = { verHoy = true }) {
                        Text("Hoy en tu U", color = MaterialTheme.colorScheme.onPrimary)
                    }
                    IconButton(onClick = { menu = true }) { Icon(Icons.Default.MoreVert, "Menú") }
                    DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                        DropdownMenuItem(text = { Text("Nueva conversación") },
                            onClick = { menu = false; input = ""; onNew() })
                        DropdownMenuItem(text = { Text("Cerrar sesión") },
                            onClick = { menu = false; onLogout() })
                    }
                },
            )
        },
        bottomBar = {
            Column(Modifier.background(MaterialTheme.colorScheme.surface).imePadding()) {
                LazyRow(
                    contentPadding = PaddingValues(horizontal = 12.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    items(SUGERENCIAS) { s ->
                        AssistChip(onClick = { enviarSugerencia(s) }, label = { Text(s) }, enabled = !st.typing)
                    }
                }
                if (st.adjunto != null || st.preparandoImagen) {
                    Row(
                        Modifier.fillMaxWidth().padding(horizontal = 12.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        st.adjunto?.let {
                            Image(
                                it.miniatura.asImageBitmap(), "Vista previa del adjunto",
                                Modifier.size(48.dp).clip(RoundedCornerShape(8.dp)), contentScale = ContentScale.Crop,
                            )
                        }
                        if (st.preparandoImagen) CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp)
                        Text(
                            if (st.preparandoImagen) "Preparando imagen…" else "Imagen adjunta",
                            Modifier.weight(1f), style = MaterialTheme.typography.labelMedium,
                        )
                        TextButton(onClick = onQuitarAdjunto) { Text("Quitar") }
                    }
                }
                st.errorImagen?.let {
                    Text(it, Modifier.padding(horizontal = 12.dp), color = MaterialTheme.colorScheme.error)
                }
                Row(
                    Modifier.fillMaxWidth().padding(8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    IconButton(
                        onClick = { photoPicker.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)) },
                        enabled = !st.typing && !st.preparandoImagen,
                    ) { Icon(painterResource(R.drawable.ic_adjuntar), "Adjuntar imagen") }
                    OutlinedTextField(
                        value = input,
                        onValueChange = { input = it },
                        placeholder = { Text("Escribe tu pregunta…") },
                        modifier = Modifier.weight(1f),
                        maxLines = 4,
                        keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                        keyboardActions = KeyboardActions(onSend = { enviar() }),
                        shape = RoundedCornerShape(24.dp),
                    )
                    IconButton(
                        onClick = enviar,
                        enabled = puedeEnviar,
                    ) { Icon(Icons.AutoMirrored.Filled.Send, "Enviar") }
                }
            }
        },
    ) { pad ->
        LazyColumn(
            state = listState,
            modifier = Modifier.fillMaxSize().padding(pad),
            contentPadding = PaddingValues(12.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            if (st.messages.isEmpty() && !st.typing) {
                item {
                    TarjetaRespuesta {
                        Text("¿Qué quieres consultar?", style = MaterialTheme.typography.headlineSmall)
                        Text("Revisa tus notas, resuelve un trámite o adjunta una foto para analizarla.")
                    }
                }
            }
            items(st.messages, key = { it.id }) { mensaje ->
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Bubble(mensaje)
                    mensaje.acciones.forEach {
                        TarjetaAccion(it, st.baseUrl, st.pagos, st.typing, enviarSugerencia, onPago, onConsultarPago)
                    }
                    mensaje.graficas.forEach { GraficaChat(it) }
                    mensaje.qrDetectados.filter { it.isNotBlank() }.distinct().forEach { QrDetectado(it) }
                }
            }
            if (st.typing) item {
                Row(Modifier.padding(6.dp), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                    CircularProgressIndicator(Modifier.size(16.dp), strokeWidth = 2.dp)
                    Text("Consultando…", style = MaterialTheme.typography.bodySmall)
                }
            }
            st.error?.let { err ->
                item {
                    Column(
                        Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp))
                            .background(MaterialTheme.colorScheme.errorContainer).padding(12.dp),
                    ) {
                        Text(err, color = MaterialTheme.colorScheme.onErrorContainer)
                        TextButton(onClick = onRetry) { Text("Reintentar") }
                    }
                }
            }
        }
    }
}

@Composable
private fun Bubble(m: Msg) {
    val cs = MaterialTheme.colorScheme
    val bg = if (m.fromUser) cs.primary else cs.secondaryContainer
    val fg = if (m.fromUser) cs.onPrimary else cs.onSecondaryContainer
    Column(
        Modifier.fillMaxWidth(),
        horizontalAlignment = if (m.fromUser) Alignment.End else Alignment.Start,
    ) {
        if (m.text.isNotBlank() || m.miniatura != null) {
            Column(
                Modifier.widthIn(max = 340.dp).clip(RoundedCornerShape(16.dp)).background(bg).padding(12.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                m.miniatura?.let {
                    Image(
                        it.asImageBitmap(), "Imagen enviada",
                        Modifier.widthIn(max = 180.dp).heightIn(max = 150.dp).clip(RoundedCornerShape(10.dp)),
                    )
                }
                if (m.fromUser) Text(m.text, color = fg) else Text(renderMarkdown(m.text), color = fg)
            }
        }
        if (!m.fromUser) {
            m.intencion?.let {
                Text(nombreEstado(it), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.padding(start = 6.dp, top = 2.dp))
            }
            if (m.fuentes.isNotEmpty()) {
                Text(
                    "Fuentes: " + m.fuentes.joinToString(" · "),
                    style = MaterialTheme.typography.labelSmall,
                    fontStyle = FontStyle.Italic,
                    modifier = Modifier.padding(start = 6.dp).widthIn(max = 320.dp),
                )
            }
        }
    }
}

