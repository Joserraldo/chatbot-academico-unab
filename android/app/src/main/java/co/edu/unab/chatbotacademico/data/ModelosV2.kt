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
)

val personasRespaldo = listOf(
    PersonaDemo("U00000001", "Estudiante demo", "Ingeniería de Sistemas", "Caso original", "🎓"),
    PersonaDemo("U00000201", "Valentina", "Ingeniería de Sistemas", "Rendimiento excelente", "🌟"),
    PersonaDemo("U00000202", "Mateo", "Medicina", "En riesgo académico", "🩺"),
    PersonaDemo("U00000203", "Camila", "Derecho", "Cerca del grado", "⚖️"),
    PersonaDemo("U00000204", "Sofía", "Psicología", "Primer semestre", "🌱"),
    PersonaDemo("U00000205", "Samuel", "Administración de Empresas", "Matrícula pendiente", "💳"),
    PersonaDemo("U00000206", "Isabella", "Ingeniería Mecatrónica", "Préstamo vencido", "📚"),
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
) {
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
    data class Noticia(val titulo: String, val url: String, val fuente: String)
}
