package co.edu.unab.chatbotacademico.data

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ContratoChatTest {
    @Test
    fun conservaLaRespuestaV1YOmiteElAdjuntoAusente() {
        val respuesta = decodeChatResponse("""{"respuesta":"Hola","intencion":"historial","fuentes":["Cosmos"]}""")
        assertEquals("Hola", respuesta.respuesta)
        assertEquals("historial", respuesta.intencion)
        assertEquals(listOf("Cosmos"), respuesta.fuentes)
        assertTrue(respuesta.acciones.isEmpty())
        assertTrue(respuesta.graficas.isEmpty())
        assertNull(respuesta.imagen)
        assertFalse(encodeChatRequest(ChatRequest("sesion", "U00000001", "Hola")).contains("imagen"))
    }

    @Test
    fun decodificaV2InclusoConAccionesFuturasYParcialesSinCalificar() {
        val respuesta = decodeChatResponse(
            """
            {
              "respuesta":"Revisa tu matrícula",
              "acciones":[
                {"tipo":"pago","orderId":"UNAB-MAT-0123456789ab","concepto":"matricula","descripcion":"Matrícula 2026-2","monto":9850000,"moneda":"COP","estado":"pendiente","url":"/app/pagar.html?order=UNAB-MAT-0123456789ab"},
                {"tipo":"enlace","titulo":"TEMA","url":"https://tema.unab.edu.co/"},
                {"tipo":"qr","titulo":"Renueva tus préstamos","url":"https://catalogo.unab.edu.co/","imagen":"/api/qr?url=https%3A%2F%2Fcatalogo.unab.edu.co%2F"},
                {"tipo":"tipo_futuro"},
                {"tipo":"pago","monto":"no disponible"},
                {"tipo":"reserva","id":12,"espacio":"Sala de estudio 3","fecha":"2026-11-21","horaInicio":"10:00","horaFin":"12:00","estado":"confirmada","orderId":null},
                {"tipo":"sugerencias","opciones":["¿Qué tareas tengo en TEMA?"]}
              ],
              "graficas":[
                {"id":"parciales","tipo":"line","titulo":"Parciales","labels":["1","2"],"series":[{"nombre":"Notas","datos":[4.2,null]}]},
                {"tipo":"bar"}
              ],
              "imagen":{"descripcion":"Cartel","qr":["https://catalogo.unab.edu.co/"]}
            }
            """.trimIndent(),
        )

        assertEquals("Revisa tu matrícula", respuesta.respuesta)
        assertEquals(5, respuesta.acciones.size)
        assertEquals(9850000L, (respuesta.acciones[0] as Accion.Pago).monto)
        assertTrue(respuesta.acciones[1] is Accion.Enlace)
        assertTrue(respuesta.acciones[2] is Accion.Qr)
        assertNull((respuesta.acciones[3] as Accion.Reserva).orderId)
        assertTrue(respuesta.acciones[4] is Accion.Sugerencias)
        assertEquals(listOf(4.2, null), respuesta.graficas.single().series.single().datos)
        assertEquals(listOf("https://catalogo.unab.edu.co/"), respuesta.imagen?.qr)
    }

    @Test
    fun enviaElAdjuntoYConstruyeElCheckoutEnElServidorConfigurado() {
        val imagen = "data:image/jpeg;base64,AA=="
        assertTrue(encodeChatRequest(ChatRequest("sesion", "U00000205", "¿Qué ves en esta imagen?", imagen)).contains(imagen))
        val base = "https://chatbotunab.duckdns.org"
        assertEquals("$base/app/pagar.html?order=UNAB-MAT-0123456789ab", checkoutUrl(base, "UNAB-MAT-0123456789ab"))
        assertNull(urlDeServicio(base, "//otro.example/api/qr"))
        assertNull(webUrl("javascript:alert(1)"))
    }
}
