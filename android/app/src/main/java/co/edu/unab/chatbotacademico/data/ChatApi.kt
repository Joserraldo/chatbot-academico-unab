package co.edu.unab.chatbotacademico.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

@Serializable
data class ChatRequest(val sessionId: String, val codigoEstudiante: String, val mensaje: String)

@Serializable
data class ChatResponse(
    val respuesta: String = "",
    val intencion: String? = null,
    val fuentes: List<String>? = null,
)

class ChatApiException(message: String) : Exception(message)

class ChatApi(private val apiKey: String) {
    private val json = Json { ignoreUnknownKeys = true; explicitNulls = false; encodeDefaults = true }

    private val client = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(90, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .callTimeout(0, TimeUnit.SECONDS)
        .build()

    suspend fun send(baseUrl: String, req: ChatRequest): ChatResponse = withContext(Dispatchers.IO) {
        val url = baseUrl.trim().trimEnd('/') + "/webhook/chat"
        val body = json.encodeToString(req).toRequestBody("application/json".toMediaType())
        val request = try {
            Request.Builder().url(url).post(body)
                .header("X-Chatbot-Key", apiKey)
                .header("Content-Type", "application/json")
                .build()
        } catch (e: IllegalArgumentException) {
            throw ChatApiException("La URL del servidor no es válida.")
        }
        client.newCall(request).execute().use { resp ->
            val text = resp.body?.string().orEmpty()
            if (!resp.isSuccessful) {
                throw ChatApiException(
                    when (resp.code) {
                        401, 403 -> "El servidor rechazó la clave de acceso (${resp.code})."
                        404 -> "No se encontró el servicio de chat (404). Revisa la URL del servidor."
                        in 500..599 -> "El servidor tuvo un problema (${resp.code}). Intenta de nuevo."
                        else -> "Error inesperado del servidor (${resp.code})."
                    }
                )
            }
            try {
                json.decodeFromString<ChatResponse>(text)
            } catch (e: Exception) {
                throw ChatApiException("La respuesta del servidor no tiene el formato esperado.")
            }
        }
    }
}
