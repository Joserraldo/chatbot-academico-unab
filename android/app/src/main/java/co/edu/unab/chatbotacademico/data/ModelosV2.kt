package co.edu.unab.chatbotacademico.data

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class PersonaDemo(
    val codigo: String,
    val nombre: String,
    val programa: String,
    val titulo: String,
    val emoji: String = "🎓",
    val descripcion: String = "",
)

val personasRespaldo = listOf(
    PersonaDemo("U00000001", "Laura", "Ingeniería de Sistemas", "Laura · semestre 6", "🧑‍💻",
        "Consulta qué cursos necesita recuperar para avanzar."),
    PersonaDemo("U00000201", "Santiago", "Ingeniería de Sistemas", "Santiago · casi graduado", "🎓",
        "Pregunta qué requisitos de grado le faltan."),
    PersonaDemo("U00000202", "Valentina", "Medicina", "Valentina · en riesgo", "🩺",
        "Consulta su riesgo académico y sus tareas vencidas."),
    PersonaDemo("U00000203", "Juan Camilo", "Derecho", "Juan Camilo · cerca del grado", "⚖️",
        "Consulta cuántos semestres y requisitos de grado le quedan."),
    PersonaDemo("U00000204", "Sofía", "Psicología", "Sofía · primer semestre", "🧠",
        "Consulta su horario, el calendario y cómo moverse en la universidad."),
    PersonaDemo("U00000205", "Andrés Felipe", "Administración de Empresas", "Andrés Felipe · matrícula pendiente", "💼",
        "Prueba el pago de su matrícula con Bold en modo de pruebas."),
    PersonaDemo("U00000206", "Nicolás", "Ingeniería Mecatrónica", "Nicolás · préstamo vencido", "🤖",
        "Consulta cómo renovar su préstamo y pagar la multa."),
)

@Serializable
sealed interface Accion {
    @Serializable
    @SerialName("pago")
    data class Pago(
        val orderId: String,
        val concepto: String,
        val descripcion: String,
        val monto: Long,
        val estado: String,
    ) : Accion

    @Serializable
    @SerialName("enlace")
    data class Enlace(val titulo: String, val url: String, val descripcion: String = "") : Accion

    @Serializable
    @SerialName("qr")
    data class Qr(val titulo: String, val url: String, val imagen: String) : Accion

    @Serializable
    @SerialName("reserva")
    data class Reserva(
        val espacio: String,
        val fecha: String,
        val horaInicio: String,
        val horaFin: String,
        val estado: String,
        val orderId: String? = null,
    ) : Accion

    @Serializable
    @SerialName("sugerencias")
    data class Sugerencias(val opciones: List<String>) : Accion
}

@Serializable
data class Grafica(
    val tipo: String,
    val titulo: String,
    val labels: List<String>,
    val series: List<Serie>,
    val unidad: String? = null,
    val nota: String? = null,
)

@Serializable
data class Serie(val nombre: String, val datos: List<Double?>)

@Serializable
data class ImagenRespuesta(val descripcion: String? = null, val qr: List<String>? = null)

@Serializable
data class PagoEstado(val estado: String)

@Serializable
data class Hoy(
    val tareas: List<Tarea> = emptyList(),
    val evaluaciones: List<Evaluacion> = emptyList(),
    val prestamos: List<Prestamo> = emptyList(),
    @SerialName("pagos_pendientes") val pagos: List<Accion.Pago> = emptyList(),
    val noticias: List<Noticia> = emptyList(),
    val estudiante: Estudiante? = null,
    @SerialName("horario_hoy") val horario: List<Clase> = emptyList(),
    val riesgo: Riesgo? = null,
) {
    @Serializable
    data class Estudiante(
        val nombre: String,
        val programa: String,
        @SerialName("semestre_actual") val semestre: Int? = null,
        val promedio: Double? = null,
        @SerialName("porcentaje_avance") val avance: Double? = null,
    )

    @Serializable
    data class Clase(val curso: String, val horario: String, val salon: String, val docente: String)

    @Serializable
    data class Riesgo(val nivel: String)

    @Serializable
    data class Tarea(
        val titulo: String,
        val curso: String,
        @SerialName("fecha_entrega") val fecha: String,
        val estado: String,
    )

    @Serializable
    data class Evaluacion(val curso: String, val docente: String, @SerialName("fecha_limite") val fecha: String)

    @Serializable
    data class Prestamo(
        val titulo: String,
        @SerialName("fecha_vencimiento") val fecha: String,
        val estado: String,
        val multa: Long = 0,
    )

    @Serializable
    data class Noticia(val titulo: String, val url: String, val fuente: String, val fecha: String? = null)
}
