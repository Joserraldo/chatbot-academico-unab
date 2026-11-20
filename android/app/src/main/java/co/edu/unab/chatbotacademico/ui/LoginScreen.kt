package co.edu.unab.chatbotacademico.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.MutableTransitionState
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.slideInVertically
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import co.edu.unab.chatbotacademico.CODIGO_REGEX
import co.edu.unab.chatbotacademico.R
import co.edu.unab.chatbotacademico.data.PersonaDemo
import co.edu.unab.chatbotacademico.data.personasRespaldo
import co.edu.unab.chatbotacademico.data.webUrl
import co.edu.unab.chatbotacademico.ui.componentes.BotonNaranja
import co.edu.unab.chatbotacademico.ui.componentes.EmojiEnCirculo
import co.edu.unab.chatbotacademico.ui.componentes.SuperficieUnab
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@Composable
fun LoginScreen(
    baseUrl: String,
    apiKey: String,
    cargarPersonas: suspend (String) -> List<PersonaDemo>,
    onLogin: (codigo: String, baseUrl: String, apiKey: String) -> Unit,
) {
    var codigo by rememberSaveable { mutableStateOf("") }
    var url by rememberSaveable(baseUrl) { mutableStateOf(baseUrl) }
    var clave by remember(apiKey) { mutableStateOf(apiKey) }
    var verClave by remember { mutableStateOf(false) }
    var opciones by rememberSaveable { mutableStateOf(false) }
    var personas by remember { mutableStateOf(personasRespaldo) }
    val codigoNormalizado = codigo.trim().uppercase()
    val codigoValido = CODIGO_REGEX.matches(codigoNormalizado)
    val servidorValido = url.isBlank() || webUrl(url.trim()) != null
    val entrar = { onLogin(codigoNormalizado, url, clave) }
    val desplazamiento = rememberScrollState()
    val alcance = rememberCoroutineScope()
    val entrada = remember { MutableTransitionState(false).apply { targetState = true } }

    LaunchedEffect(url, baseUrl) {
        delay(350)
        personas = try {
            cargarPersonas(url.trim().ifBlank { baseUrl })
                .filter { CODIGO_REGEX.matches(it.codigo) }.distinctBy { it.codigo }.ifEmpty { personasRespaldo }
        } catch (e: CancellationException) {
            throw e
        } catch (_: Exception) {
            personasRespaldo
        }
    }

    Box(Modifier.fillMaxSize().safeDrawingPadding().imePadding(), contentAlignment = Alignment.TopCenter) {
        Column(Modifier.widthIn(max = 560.dp).fillMaxWidth().verticalScroll(desplazamiento).padding(14.dp)) {
            AnimatedVisibility(
                visibleState = entrada,
                enter = fadeIn(tween(330)) + slideInVertically(tween(330)) { it / 35 },
            ) {
                SuperficieUnab(forma = FormaContenedor) {
                    Column(
                        Modifier.fillMaxWidth().padding(horizontal = 18.dp, vertical = 22.dp),
                        verticalArrangement = Arrangement.spacedBy(18.dp),
                    ) {
                        Column(Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally) {
                            Image(
                                painterResource(R.drawable.logo_unab), "Universidad UNAB",
                                Modifier.widthIn(max = 180.dp).fillMaxWidth().height(56.dp),
                            )
                            Text(
                                "Asistente UNAB 360",
                                Modifier.padding(top = 10.dp),
                                style = MaterialTheme.typography.headlineSmall,
                                textAlign = TextAlign.Center,
                            )
                            Text(
                                "Universidad Autónoma de Bucaramanga",
                                color = TextoApagado, textAlign = TextAlign.Center,
                                style = MaterialTheme.typography.bodyMedium,
                            )
                        }

                        val colores = OutlinedTextFieldDefaults.colors(
                            unfocusedBorderColor = Borde, focusedBorderColor = NaranjaFuerte,
                            unfocusedContainerColor = Superficie, focusedContainerColor = Superficie,
                        )
                        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            OutlinedTextField(
                                value = codigo,
                                onValueChange = { codigo = it.take(9) },
                                label = { Text("Código de estudiante") },
                                placeholder = { Text("U00000001") },
                                singleLine = true,
                                isError = codigo.isNotEmpty() && !codigoValido,
                                supportingText = { Text("Formato: U seguido de 8 dígitos") },
                                keyboardOptions = KeyboardOptions(
                                    capitalization = KeyboardCapitalization.Characters,
                                    imeAction = ImeAction.Next,
                                ),
                                shape = FormaBoton, colors = colores, modifier = Modifier.fillMaxWidth(),
                            )
                            OutlinedTextField(
                                value = clave,
                                onValueChange = { clave = it },
                                label = { Text("Clave de acceso") },
                                singleLine = true,
                                visualTransformation = if (verClave) VisualTransformation.None else PasswordVisualTransformation(),
                                trailingIcon = {
                                    IconButton(onClick = { verClave = !verClave }) {
                                        Icon(
                                            painterResource(if (verClave) R.drawable.ic_ocultar else R.drawable.ic_ver),
                                            if (verClave) "Ocultar clave" else "Mostrar clave",
                                        )
                                    }
                                },
                                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password, imeAction = ImeAction.Done),
                                keyboardActions = KeyboardActions(onDone = { if (codigoValido && servidorValido) entrar() }),
                                shape = FormaBoton, colors = colores, modifier = Modifier.fillMaxWidth(),
                            )
                            BotonNaranja(
                                "Entrar al chat", codigoValido && servidorValido, entrar,
                                modifier = Modifier.padding(top = 8.dp),
                            )
                            TextButton(onClick = { opciones = !opciones }) {
                                Text("Opciones avanzadas", color = TextoApagado)
                                Icon(
                                    if (opciones) Icons.Default.KeyboardArrowUp else Icons.Default.KeyboardArrowDown,
                                    null, Modifier.size(18.dp), tint = TextoApagado,
                                )
                            }
                            AnimatedVisibility(opciones) {
                                OutlinedTextField(
                                    value = url,
                                    onValueChange = { url = it },
                                    label = { Text("URL del servidor") },
                                    isError = !servidorValido,
                                    supportingText = { if (!servidorValido) Text("Escribe una URL válida del servidor.") },
                                    singleLine = true,
                                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
                                    shape = FormaBoton, colors = colores, modifier = Modifier.fillMaxWidth(),
                                )
                            }
                        }

                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Column {
                                Text("Probar como…", style = MaterialTheme.typography.titleLarge)
                                Text(
                                    "Elige un perfil con datos sintéticos para completar el código.",
                                    style = MaterialTheme.typography.bodySmall, color = TextoApagado,
                                )
                            }
                            personas.forEach { persona ->
                                TarjetaPersona(persona, codigoNormalizado == persona.codigo) {
                                    codigo = persona.codigo
                                    alcance.launch { desplazamiento.animateScrollTo(0) }
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
private fun TarjetaPersona(persona: PersonaDemo, seleccionada: Boolean, elegir: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().clip(FormaTarjeta)
            .background(if (seleccionada) NaranjaSuave else Superficie)
            .border(if (seleccionada) 2.dp else 1.dp, if (seleccionada) UnabOrange else Borde, FormaTarjeta)
            .selectable(seleccionada, role = Role.RadioButton, onClick = elegir)
            .padding(12.dp),
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        EmojiEnCirculo(persona.emoji)
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(persona.titulo, style = MaterialTheme.typography.titleSmall)
            Text(persona.programa, style = MaterialTheme.typography.labelLarge, color = MoradoFuerte)
            if (persona.descripcion.isNotBlank()) {
                Text(
                    persona.descripcion, style = MaterialTheme.typography.bodySmall,
                    color = TextoApagado, maxLines = 2, overflow = TextOverflow.Ellipsis,
                )
            }
            Text(persona.codigo, style = MaterialTheme.typography.labelMedium, color = TextoTenue)
        }
        if (seleccionada) Icon(Icons.Default.Check, null, Modifier.size(18.dp), tint = MoradoFuerte)
    }
}
