package co.edu.unab.chatbotacademico.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedCard
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import co.edu.unab.chatbotacademico.CODIGO_REGEX
import co.edu.unab.chatbotacademico.data.PersonaDemo
import co.edu.unab.chatbotacademico.data.personasRespaldo
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.delay

@Composable
fun LoginScreen(
    baseUrl: String,
    apiKey: String,
    cargarPersonas: suspend (String) -> List<PersonaDemo>,
    onLogin: (codigo: String, baseUrl: String, apiKey: String) -> Unit,
) {
    var codigo by rememberSaveable { mutableStateOf("") }
    var url by rememberSaveable(baseUrl) { mutableStateOf(baseUrl) }
    var key by remember(apiKey) { mutableStateOf(apiKey) }
    var touched by rememberSaveable { mutableStateOf(false) }
    val codigoNormalizado = codigo.trim().uppercase()
    val valido = CODIGO_REGEX.matches(codigoNormalizado)
    var personas by remember { mutableStateOf(personasRespaldo) }

    LaunchedEffect(url) {
        delay(350)
        personas = try {
            cargarPersonas(url.ifBlank { baseUrl }).filter { CODIGO_REGEX.matches(it.codigo) }
                .distinctBy { it.codigo }.ifEmpty { personasRespaldo }
        } catch (e: CancellationException) {
            throw e
        } catch (_: Exception) {
            personasRespaldo
        }
    }

    Column(
        Modifier.fillMaxSize().safeDrawingPadding().verticalScroll(rememberScrollState()).padding(vertical = 24.dp),
        verticalArrangement = Arrangement.Center,
    ) {
        Column(Modifier.padding(horizontal = 24.dp)) {
            Text("Asistente", style = MaterialTheme.typography.headlineMedium)
            Text(
                "UNAB 360",
                style = MaterialTheme.typography.displaySmall,
                fontWeight = FontWeight.Black,
                color = MaterialTheme.colorScheme.primary,
            )
            Spacer(Modifier.height(8.dp))
            Text("Consulta tus notas, trámites y agenda universitaria.", style = MaterialTheme.typography.bodyMedium)
            Spacer(Modifier.height(20.dp))
            Text("Probar como…", style = MaterialTheme.typography.titleMedium)
            Text("Perfiles con datos sintéticos", style = MaterialTheme.typography.bodySmall)
        }
        LazyRow(
            contentPadding = PaddingValues(horizontal = 24.dp, vertical = 12.dp),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            items(personas, key = { it.codigo }) { persona ->
                val seleccionado = codigoNormalizado == persona.codigo
                OutlinedCard(
                    onClick = { codigo = persona.codigo; touched = true },
                    modifier = Modifier.width(214.dp),
                    colors = CardDefaults.outlinedCardColors(
                        containerColor = if (seleccionado) MaterialTheme.colorScheme.primaryContainer
                        else MaterialTheme.colorScheme.surfaceContainerLow,
                    ),
                ) {
                    Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                            Text(persona.emoji, style = MaterialTheme.typography.titleLarge)
                            Text(persona.nombre, style = MaterialTheme.typography.titleSmall, maxLines = 1, overflow = TextOverflow.Ellipsis)
                        }
                        Text(persona.programa, style = MaterialTheme.typography.bodySmall, maxLines = 1, overflow = TextOverflow.Ellipsis)
                        Text(persona.titulo, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary)
                    }
                }
            }
        }

        Column(Modifier.padding(horizontal = 24.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        OutlinedTextField(
            value = codigo,
            onValueChange = { codigo = it.take(9); touched = true },
            label = { Text("Código de estudiante") },
            placeholder = { Text("U00000001") },
            singleLine = true,
            isError = touched && !valido,
            supportingText = {
                if (touched && !valido) Text("Formato: U seguida de 8 dígitos (ej. U00000001)")
            },
            keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Characters),
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(
            value = key,
            onValueChange = { key = it },
            label = { Text("Clave de acceso") },
            singleLine = true,
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
            modifier = Modifier.fillMaxWidth(),
        )
        Button(
            onClick = { onLogin(codigo, url, key) },
            enabled = valido,
            modifier = Modifier.fillMaxWidth(),
        ) { Text("Entrar al chat") }
        OutlinedTextField(
            value = url,
            onValueChange = { url = it },
            label = { Text("URL del servidor") },
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
            modifier = Modifier.fillMaxWidth(),
        )
        }
    }
}
