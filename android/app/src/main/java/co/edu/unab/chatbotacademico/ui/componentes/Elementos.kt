package co.edu.unab.chatbotacademico.ui.componentes

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import co.edu.unab.chatbotacademico.R
import co.edu.unab.chatbotacademico.ui.Borde
import co.edu.unab.chatbotacademico.ui.FormaBoton
import co.edu.unab.chatbotacademico.ui.FormaTarjeta
import co.edu.unab.chatbotacademico.ui.MoradoFuerte
import co.edu.unab.chatbotacademico.ui.MoradoSuave
import co.edu.unab.chatbotacademico.ui.SombraCalida
import co.edu.unab.chatbotacademico.ui.Superficie
import co.edu.unab.chatbotacademico.ui.SuperficieSuave
import co.edu.unab.chatbotacademico.ui.Texto
import co.edu.unab.chatbotacademico.ui.gradienteNaranja

@Composable
internal fun TarjetaRespuesta(
    modifier: Modifier = Modifier,
    forma: Shape = FormaTarjeta,
    color: Color = Superficie,
    contenido: @Composable ColumnScope.() -> Unit,
) {
    SuperficieUnab(modifier, forma, color) {
        Column(
            Modifier.fillMaxWidth().padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
            content = contenido,
        )
    }
}

@Composable
internal fun SuperficieUnab(
    modifier: Modifier = Modifier,
    forma: Shape = FormaTarjeta,
    color: Color = Superficie,
    contenido: @Composable () -> Unit,
) {
    Surface(
        modifier = modifier.fillMaxWidth().shadow(3.dp, forma, ambientColor = SombraCalida, spotColor = SombraCalida),
        shape = forma,
        color = color,
        contentColor = Texto,
        border = BorderStroke(1.dp, Borde),
        content = contenido,
    )
}

@Composable
internal fun BotonNaranja(
    texto: String,
    habilitado: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Box(
        modifier.fillMaxWidth().heightIn(min = 52.dp).alpha(if (habilitado) 1f else 0.5f)
            .gradienteNaranja(FormaBoton).clickable(enabled = habilitado, role = Role.Button, onClick = onClick)
            .padding(horizontal = 12.dp, vertical = 8.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(texto, color = Texto, style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.Bold)
    }
}

@Composable
internal fun Insignia(texto: String, color: Color = MoradoFuerte, fondo: Color = MoradoSuave) {
    Text(
        texto,
        modifier = Modifier.background(fondo, CircleShape).padding(horizontal = 9.dp, vertical = 4.dp),
        color = color,
        style = MaterialTheme.typography.labelMedium,
    )
}

@Composable
internal fun AvatarUnab(modifier: Modifier = Modifier) {
    Image(painterResource(R.drawable.isotipo_unab), null, modifier.clip(CircleShape))
}

@Composable
internal fun EmojiEnCirculo(emoji: String, modifier: Modifier = Modifier) {
    Box(modifier.size(38.dp).background(SuperficieSuave, CircleShape), contentAlignment = Alignment.Center) {
        Text(emoji, style = MaterialTheme.typography.titleMedium)
    }
}
