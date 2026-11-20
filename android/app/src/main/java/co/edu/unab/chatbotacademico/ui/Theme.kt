package co.edu.unab.chatbotacademico.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.LocalContentColor
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawWithCache
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

internal val Crema = Color(0xFFFFFBEE)
internal val Superficie = Color.White
internal val SuperficieSuave = Color(0xFFFFF7E6)
internal val SuperficieFuerte = Color(0xFFFFEFD0)
internal val Texto = Color(0xFF333333)
internal val TextoApagado = Color(0xFF5E574C)
internal val TextoTenue = Color(0xFF726A5D)
internal val Borde = Texto.copy(alpha = 0.12f)
internal val UnabOrange = Color(0xFFFF9D00)
internal val NaranjaFuerte = Color(0xFFE09900)
internal val NaranjaSuave = UnabOrange.copy(alpha = 0.14f)
internal val UnabPurple = Color(0xFF8600DD)
internal val MoradoFuerte = Color(0xFF6B00B3)
internal val MoradoSuave = UnabPurple.copy(alpha = 0.10f)
internal val BordeMorado = UnabPurple.copy(alpha = 0.45f)
internal val Exito = Color(0xFF0F9D67)
internal val TextoExito = Color(0xFF087049)
internal val Peligro = Color(0xFFB42318)
internal val PeligroSuave = Color(0xFFFEF3F2)
internal val SombraCalida = Color(0xFF503200)
internal val FormaTarjeta = RoundedCornerShape(18.dp)
internal val FormaContenedor = RoundedCornerShape(28.dp)
internal val FormaBoton = RoundedCornerShape(16.dp)

private val Colores = lightColorScheme(
    primary = MoradoFuerte, onPrimary = Superficie,
    primaryContainer = Color(0xFFF3E5FC), onPrimaryContainer = MoradoFuerte,
    secondary = UnabOrange, onSecondary = Texto,
    secondaryContainer = SuperficieFuerte, onSecondaryContainer = Texto,
    background = Crema, onBackground = Texto,
    surface = Superficie, onSurface = Texto,
    surfaceContainer = SuperficieSuave, surfaceContainerLow = Superficie,
    surfaceContainerHigh = SuperficieSuave,
    surfaceVariant = SuperficieSuave, onSurfaceVariant = TextoApagado,
    outline = TextoTenue, outlineVariant = Borde,
    error = Peligro, errorContainer = PeligroSuave, onErrorContainer = Peligro,
)

private val Base = Typography()
private val Tipografia = Base.copy(
    displaySmall = Base.displaySmall.copy(fontWeight = FontWeight.Black),
    headlineMedium = Base.headlineMedium.copy(fontWeight = FontWeight.Black, letterSpacing = (-0.6).sp),
    headlineSmall = Base.headlineSmall.copy(fontWeight = FontWeight.ExtraBold, letterSpacing = (-0.4).sp),
    titleLarge = Base.titleLarge.copy(fontWeight = FontWeight.ExtraBold),
    titleMedium = Base.titleMedium.copy(fontWeight = FontWeight.ExtraBold, letterSpacing = 0.sp),
    titleSmall = Base.titleSmall.copy(fontWeight = FontWeight.Bold),
    labelMedium = Base.labelMedium.copy(fontWeight = FontWeight.SemiBold),
)

@Composable
fun UnabTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = Colores, typography = Tipografia) {
        CompositionLocalProvider(LocalContentColor provides Texto, content = content)
    }
}

@Composable
fun FondoUnab(content: @Composable () -> Unit) {
    Box(Modifier.fillMaxSize().background(Crema).drawWithCache {
        val arriba = Brush.radialGradient(
            listOf(UnabOrange.copy(alpha = 0.22f), UnabOrange.copy(alpha = 0f)),
            center = Offset.Zero,
            radius = size.width.coerceAtLeast(1f) * 1.15f,
        )
        val abajo = Brush.radialGradient(
            listOf(UnabPurple.copy(alpha = 0.12f), UnabPurple.copy(alpha = 0f)),
            center = Offset(size.width, size.height),
            radius = size.width.coerceAtLeast(1f) * 1.25f,
        )
        onDrawBehind {
            drawRect(arriba)
            drawRect(abajo)
        }
    }) { content() }
}

internal fun Modifier.gradienteNaranja(forma: Shape): Modifier =
    clip(forma).drawWithCache {
        val centro = Offset(size.width / 2, size.height / 2)
        val mitad = (size.width + size.height).coerceAtLeast(1f) / 4
        val diagonal = Offset(mitad, mitad)
        val pincel = Brush.linearGradient(
            listOf(Color(0xFFFFB03A), UnabOrange),
            start = centro - diagonal,
            end = centro + diagonal,
        )
        onDrawBehind { drawRect(pincel) }
    }
