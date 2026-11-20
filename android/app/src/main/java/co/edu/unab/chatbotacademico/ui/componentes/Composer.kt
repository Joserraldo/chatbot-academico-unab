package co.edu.unab.chatbotacademico.ui.componentes

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import android.speech.RecognizerIntent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.IconButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import co.edu.unab.chatbotacademico.R
import co.edu.unab.chatbotacademico.UiState
import co.edu.unab.chatbotacademico.ui.FormaBoton
import co.edu.unab.chatbotacademico.ui.FormaContenedor
import co.edu.unab.chatbotacademico.ui.MoradoFuerte
import co.edu.unab.chatbotacademico.ui.Peligro
import co.edu.unab.chatbotacademico.ui.SuperficieSuave
import co.edu.unab.chatbotacademico.ui.Texto
import co.edu.unab.chatbotacademico.ui.TextoTenue
import co.edu.unab.chatbotacademico.ui.gradienteNaranja

@Composable
internal fun Composer(
    st: UiState,
    texto: String,
    cambiarTexto: (String) -> Unit,
    adjuntar: (Uri) -> Unit,
    quitarAdjunto: () -> Unit,
    enviar: () -> Unit,
) {
    val contexto = LocalContext.current
    val selector = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
        uri?.let(adjuntar)
    }
    val dictado = remember {
        Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, "es-CO")
            putExtra(RecognizerIntent.EXTRA_PROMPT, "Dicta tu pregunta")
        }
    }
    var vozDisponible by remember(contexto) { mutableStateOf(dictado.resolveActivity(contexto.packageManager) != null) }
    val reconocer = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { resultado ->
        if (resultado.resultCode == Activity.RESULT_OK) {
            val frase = resultado.data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
                ?.firstOrNull()?.trim().orEmpty()
            if (frase.isNotEmpty()) cambiarTexto(listOf(texto.trimEnd(), frase).filter { it.isNotEmpty() }.joinToString(" "))
        }
    }

    val puedeEnviar = !st.typing && !st.preparandoImagen && (texto.isNotBlank() || st.adjunto != null)
    Box(
        Modifier.fillMaxWidth().navigationBarsPadding().imePadding().padding(horizontal = 14.dp, vertical = 9.dp),
        contentAlignment = Alignment.Center,
    ) {
        Column(Modifier.widthIn(max = 632.dp).fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            if (st.adjunto != null || st.preparandoImagen) {
                Row(
                    Modifier.clip(FormaBoton).background(SuperficieSuave).padding(start = 8.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    if (st.preparandoImagen) {
                        CircularProgressIndicator(Modifier.size(22.dp), strokeWidth = 2.dp)
                    } else {
                        st.adjunto?.let {
                            Image(
                                it.miniatura.asImageBitmap(), "Vista previa de la imagen",
                                Modifier.size(34.dp).clip(FormaBoton), contentScale = ContentScale.Crop,
                            )
                        }
                    }
                    Text(
                        if (st.preparandoImagen) "Preparando imagen…" else "Imagen adjunta",
                        Modifier.weight(1f, fill = false), style = MaterialTheme.typography.labelMedium,
                    )
                    IconButton(onClick = quitarAdjunto) {
                        Icon(Icons.Default.Close, "Quitar imagen", Modifier.size(18.dp))
                    }
                }
            }
            st.errorImagen?.let { Text(it, color = Peligro, style = MaterialTheme.typography.bodySmall) }

            SuperficieUnab(forma = FormaContenedor) {
                Row(
                    Modifier.fillMaxWidth().padding(horizontal = 5.dp, vertical = 4.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    IconButton(
                        onClick = { selector.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)) },
                        enabled = !st.typing && !st.preparandoImagen,
                    ) {
                        Icon(painterResource(R.drawable.ic_adjuntar), "Adjuntar imagen", tint = TextoTenue)
                    }

                    val estilo = MaterialTheme.typography.bodyMedium
                    BasicTextField(
                        value = texto,
                        onValueChange = cambiarTexto,
                        modifier = Modifier.weight(1f).padding(vertical = 10.dp)
                            .semantics { contentDescription = "Tu pregunta" },
                        maxLines = 4,
                        textStyle = estilo.copy(color = Texto),
                        cursorBrush = SolidColor(MoradoFuerte),
                        keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                        keyboardActions = KeyboardActions(onSend = { if (puedeEnviar) enviar() }),
                        decorationBox = { contenido ->
                            Box {
                                if (texto.isEmpty()) {
                                    Text(
                                        "Escribe tu pregunta…", color = TextoTenue, style = estilo,
                                        maxLines = 1, overflow = TextOverflow.Ellipsis,
                                    )
                                }
                                contenido()
                            }
                        },
                    )

                    if (vozDisponible) {
                        IconButton(onClick = {
                            try {
                                reconocer.launch(dictado)
                            } catch (_: ActivityNotFoundException) {
                                vozDisponible = false
                            }
                        }) {
                            Icon(painterResource(R.drawable.ic_microfono), "Dictar pregunta", tint = MoradoFuerte)
                        }
                    }
                    IconButton(
                        onClick = enviar,
                        enabled = puedeEnviar,
                        modifier = Modifier.size(48.dp).alpha(if (puedeEnviar) 1f else 0.5f).gradienteNaranja(CircleShape),
                        colors = IconButtonDefaults.iconButtonColors(contentColor = Texto, disabledContentColor = Texto),
                    ) {
                        Icon(Icons.AutoMirrored.Filled.Send, "Enviar", Modifier.size(21.dp))
                    }
                }
            }
        }
    }
}
