package co.edu.unab.chatbotacademico.ui

import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle

private val BULLET = Regex("^(\\s*)[-*]\\s+(.*)$")
private val HEADING = Regex("^#{1,6}\\s+(.*)$")

/** Render mínimo: **negrita**, listas con "- " (viñeta) y encabezados "#" como negrita. */
fun renderMarkdown(src: String): AnnotatedString = buildAnnotatedString {
    val lines = src.replace("\r\n", "\n").split("\n")
    lines.forEachIndexed { i, raw ->
        var line = raw
        BULLET.find(line)?.let { line = it.groupValues[1] + "•  " + it.groupValues[2] }
        line = line.replace(HEADING, "**$1**")
        val parts = line.split("**")
        // Con número par de partes hay un "**" sin cerrar: se deja literal.
        val unclosed = parts.size % 2 == 0
        parts.forEachIndexed { idx, p ->
            when {
                idx == 0 -> append(p)
                idx % 2 == 1 && unclosed && idx == parts.lastIndex -> append("**$p")
                idx % 2 == 1 -> withStyle(SpanStyle(fontWeight = FontWeight.Bold)) { append(p) }
                else -> append(p)
            }
        }
        if (i < lines.lastIndex) append("\n")
    }
}
