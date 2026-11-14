package co.edu.unab.chatbotacademico.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.dp
import co.edu.unab.chatbotacademico.CODIGO_REGEX

@Composable
fun LoginScreen(baseUrl: String, onLogin: (codigo: String, baseUrl: String) -> Unit) {
    var codigo by remember { mutableStateOf("") }
    var url by remember(baseUrl) { mutableStateOf(baseUrl) }
    var touched by remember { mutableStateOf(false) }
    val valido = CODIGO_REGEX.matches(codigo.trim().uppercase())

    Column(
        Modifier.fillMaxSize().safeDrawingPadding().verticalScroll(rememberScrollState()).padding(24.dp),
        verticalArrangement = Arrangement.Center,
    ) {
        Text("Asistente Académico", style = MaterialTheme.typography.headlineMedium,
            color = MaterialTheme.colorScheme.primary)
        Text("UNAB", style = MaterialTheme.typography.headlineMedium, color = UnabOrange)
        Spacer(Modifier.height(8.dp))
        Text(
            "Ingresa tu código de estudiante para consultar tu avance académico, calendario y novedades.",
            style = MaterialTheme.typography.bodyMedium,
        )
        Spacer(Modifier.height(24.dp))

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
        Spacer(Modifier.height(8.dp))
        OutlinedTextField(
            value = url,
            onValueChange = { url = it },
            label = { Text("URL del servidor") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        Spacer(Modifier.height(24.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.fillMaxWidth()) {
            OutlinedButton(onClick = { codigo = "U00000001"; touched = true }) { Text("Usar demo") }
            Button(
                onClick = { onLogin(codigo, url) },
                enabled = valido,
                modifier = Modifier.weight(1f),
            ) { Text("Entrar") }
        }
    }
}
