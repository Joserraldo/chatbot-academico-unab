package co.edu.unab.chatbotacademico.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material3.AssistChip
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
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import co.edu.unab.chatbotacademico.Msg
import co.edu.unab.chatbotacademico.UiState

private val SUGERENCIAS = listOf(
    "¿Cómo va mi avance en el plan?",
    "¿Qué cursos de competencias digitales he tomado?",
    "¿Cuándo son las inscripciones?",
    "¿Qué es la insignia de competencias digitales?",
    "Novedades y convocatorias",
    "¿Cuántos semestres me faltan?",
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(
    st: UiState,
    onSend: (String) -> Unit,
    onRetry: () -> Unit,
    onNew: () -> Unit,
    onLogout: () -> Unit,
) {
    var menu by remember { mutableStateOf(false) }
    var input by remember { mutableStateOf("") }
    val listState = rememberLazyListState()
    val extra = (if (st.typing) 1 else 0) + (if (st.error != null) 1 else 0)

    LaunchedEffect(st.messages.size, st.typing, st.error) {
        val total = st.messages.size + extra
        if (total > 0) listState.animateScrollToItem(total - 1)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Asistente Académico UNAB", style = MaterialTheme.typography.titleMedium)
                        Text(st.codigo.orEmpty(), style = MaterialTheme.typography.labelSmall)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary,
                    actionIconContentColor = MaterialTheme.colorScheme.onPrimary,
                ),
                actions = {
                    IconButton(onClick = { menu = true }) { Icon(Icons.Default.MoreVert, "Menú") }
                    DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                        DropdownMenuItem(text = { Text("Nueva conversación") },
                            onClick = { menu = false; onNew() })
                        DropdownMenuItem(text = { Text("Cerrar sesión") },
                            onClick = { menu = false; onLogout() })
                    }
                },
            )
        },
        bottomBar = {
            Column(Modifier.background(MaterialTheme.colorScheme.surface).imePadding()) {
                LazyRow(
                    contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 12.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    items(SUGERENCIAS) { s ->
                        AssistChip(onClick = { onSend(s) }, label = { Text(s) }, enabled = !st.typing)
                    }
                }
                Row(
                    Modifier.fillMaxWidth().padding(8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    OutlinedTextField(
                        value = input,
                        onValueChange = { input = it },
                        placeholder = { Text("Escribe tu pregunta…") },
                        modifier = Modifier.weight(1f),
                        maxLines = 4,
                        keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                        shape = RoundedCornerShape(24.dp),
                    )
                    IconButton(
                        onClick = { onSend(input); input = "" },
                        enabled = input.isNotBlank() && !st.typing,
                    ) { Icon(Icons.AutoMirrored.Filled.Send, "Enviar", tint = MaterialTheme.colorScheme.primary) }
                }
            }
        },
    ) { pad ->
        LazyColumn(
            state = listState,
            modifier = Modifier.fillMaxSize().padding(pad),
            contentPadding = androidx.compose.foundation.layout.PaddingValues(12.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            if (st.messages.isEmpty() && !st.typing) {
                item {
                    Text(
                        "¡Hola! Pregúntame por tu avance en el plan, tus cursos, fechas de inscripción y novedades. " +
                            "Puedes usar las sugerencias de abajo.",
                        style = MaterialTheme.typography.bodyLarge,
                        modifier = Modifier.padding(8.dp),
                    )
                }
            }
            items(st.messages, key = { it.id }) { Bubble(it) }
            if (st.typing) item { Typing() }
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
        Box(
            Modifier.widthIn(max = 320.dp).clip(RoundedCornerShape(16.dp)).background(bg).padding(12.dp),
        ) {
            if (m.fromUser) Text(m.text, color = fg) else Text(renderMarkdown(m.text), color = fg)
        }
        if (!m.fromUser) {
            m.intencion?.let {
                Text(it, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.primary,
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

@Composable
private fun Typing() {
    Text(
        "escribiendo…",
        style = MaterialTheme.typography.bodySmall,
        fontStyle = FontStyle.Italic,
        modifier = Modifier.padding(start = 6.dp),
    )
}
