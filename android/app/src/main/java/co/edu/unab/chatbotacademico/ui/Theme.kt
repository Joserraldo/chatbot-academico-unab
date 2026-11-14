package co.edu.unab.chatbotacademico.ui

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val UnabOrange = Color(0xFFFFA300)
val UnabPurple = Color(0xFF8A00E6)

private val Light = lightColorScheme(
    primary = UnabPurple, onPrimary = Color.White,
    primaryContainer = Color(0xFFF0DBFF), onPrimaryContainer = Color(0xFF2C0050),
    secondary = UnabOrange, onSecondary = Color.Black,
    secondaryContainer = Color(0xFFFFE2B0), onSecondaryContainer = Color(0xFF3A2400),
    background = Color(0xFFFFFBFF), surface = Color(0xFFFFFBFF),
)

private val Dark = darkColorScheme(
    primary = Color(0xFFD9B0FF), onPrimary = Color(0xFF4A0080),
    primaryContainer = Color(0xFF6A00B3), onPrimaryContainer = Color(0xFFF0DBFF),
    secondary = UnabOrange, onSecondary = Color.Black,
    secondaryContainer = Color(0xFF5C3B00), onSecondaryContainer = Color(0xFFFFDDAE),
    background = Color(0xFF1C1B1F), surface = Color(0xFF1C1B1F),
)

@Composable
fun UnabTheme(dark: Boolean = isSystemInDarkTheme(), content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = if (dark) Dark else Light, content = content)
}
