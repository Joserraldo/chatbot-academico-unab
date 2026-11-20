package co.edu.unab.chatbotacademico.data

import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.serialization.Serializable
import kotlinx.serialization.Transient
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.decodeFromJsonElement
import okhttp3.Call
import okhttp3.Callback
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import java.io.IOException
import java.util.concurrent.TimeUnit

@Serializable
data class ChatRequest(
    val sessionId: String,
    val codigoEstudiante: String,
    val mensaje: String,
    val imagen: String? = null,
)

@Serializable
data class ChatResponse(
    val respuesta: String = "",
    val intencion: String? = null,
    val fuentes: List<String>? = null,
    @Transient val acciones: List<Accion> = emptyList(),
    @Transient val graficas: List<Grafica> = emptyList(),
    @Transient val imagen: ImagenRespuesta? = null,
)

class ChatApiException(message: String) : Exception(message)

private val json = Json {
    ignoreUnknownKeys = true
    explicitNulls = false
    classDiscriminator = "tipo"
}

internal fun encodeChatRequest(request: ChatRequest): String = json.encodeToString(request)

internal fun decodeChatResponse(body: String): ChatResponse {
    val payload = json.decodeFromString<JsonObject>(body)
    return json.decodeFromJsonElement<ChatResponse>(payload).copy(
        acciones = payload.decodeList("acciones"),
        graficas = payload.decodeList("graficas"),
        imagen = payload["imagen"]?.decodeOrNull(),
    )
}

// Un elemento v2 desconocido o incompleto no impide leer el texto ni el resto de la respuesta.
private inline fun <reified T> JsonObject.decodeList(key: String): List<T> =
    (get(key) as? JsonArray)?.mapNotNull { it.decodeOrNull<T>() }.orEmpty()

private inline fun <reified T> JsonElement.decodeOrNull(): T? =
    try {
        json.decodeFromJsonElement<T>(this)
    } catch (_: IllegalArgumentException) {
        null
    }

fun webUrl(value: String): HttpUrl? = value.toHttpUrlOrNull()?.takeIf {
    it.username.isEmpty() && it.password.isEmpty()
}

fun urlDeServicio(baseUrl: String, ruta: String): HttpUrl? {
    val base = webUrl(baseUrl.trim()) ?: return null
    if (!ruta.startsWith("/")) return null
    return base.resolve(ruta)?.takeIf { it.scheme == base.scheme && it.host == base.host && it.port == base.port }
}

fun checkoutUrl(baseUrl: String, orderId: String): String? =
    urlDeServicio(baseUrl, "/app/pagar.html")?.newBuilder()
        ?.addQueryParameter("order", orderId)?.build()?.toString()

class ChatApi {
    private val client = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(120, TimeUnit.SECONDS)
        .writeTimeout(90, TimeUnit.SECONDS)
        .followRedirects(false)
        .build()
    private val servicios = client.newBuilder().callTimeout(12, TimeUnit.SECONDS).build()

    suspend fun send(baseUrl: String, apiKey: String, req: ChatRequest): ChatResponse {
        val body = encodeChatRequest(req).toRequestBody("application/json".toMediaType())
        val request = request(baseUrl, "/webhook/chat", apiKey).post(body).build()
        return decode { decodeChatResponse(client.newCall(request).readBody()) }
    }

    suspend fun personas(baseUrl: String): List<PersonaDemo> = get(baseUrl, "/api/demo/personas")

    suspend fun pago(baseUrl: String, orderId: String): PagoEstado {
        val url = urlDeServicio(baseUrl, "/api/pagos")?.newBuilder()
            ?.addPathSegment(orderId)?.build() ?: throw ChatApiException("La URL del servidor no es válida.")
        return decode { json.decodeFromString(servicios.newCall(Request.Builder().url(url).build()).readBody()) }
    }

    suspend fun hoy(baseUrl: String, apiKey: String, codigo: String): Hoy = get(baseUrl, "/api/hoy/$codigo", apiKey)

    private suspend inline fun <reified T> get(baseUrl: String, path: String, apiKey: String? = null): T {
        val request = request(baseUrl, path, apiKey).build()
        return decode { json.decodeFromString(servicios.newCall(request).readBody()) }
    }

    private fun request(baseUrl: String, path: String, apiKey: String?): Request.Builder {
        // Se conserva el prefijo de una URL de chat configurada en v1.
        val url = if (path == "/webhook/chat") webUrl(baseUrl.trim().trimEnd('/') + path)
        else urlDeServicio(baseUrl, path)
        val builder = Request.Builder().url(url ?: throw ChatApiException("La URL del servidor no es válida."))
        if (apiKey != null) {
            try {
                builder.header("X-Chatbot-Key", apiKey)
            } catch (_: IllegalArgumentException) {
                throw ChatApiException("La clave de acceso contiene caracteres no válidos.")
            }
        }
        return builder
    }

    private inline fun <T> decode(parse: () -> T): T = try {
        parse()
    } catch (_: IllegalArgumentException) {
        throw ChatApiException("La respuesta del servidor no tiene el formato esperado.")
    }
}

private suspend fun Call.readBody(): String = suspendCancellableCoroutine { continuation ->
    continuation.invokeOnCancellation { cancel() }
    enqueue(object : Callback {
        override fun onFailure(call: Call, e: IOException) {
            continuation.resumeWith(Result.failure(e))
        }

        override fun onResponse(call: Call, response: Response) {
            continuation.resumeWith(runCatching { response.use { it.readBody() } })
        }
    })
}

private fun Response.readBody(): String {
    if (isSuccessful) return body?.string().orEmpty()
    throw ChatApiException(
        when (code) {
            401, 403 -> "El servidor rechazó la clave de acceso ($code)."
            404 -> "El servicio solicitado no está disponible (404)."
            in 500..599 -> "El servidor tuvo un problema ($code). Intenta de nuevo."
            else -> "Error inesperado del servidor ($code)."
        },
    )
}
