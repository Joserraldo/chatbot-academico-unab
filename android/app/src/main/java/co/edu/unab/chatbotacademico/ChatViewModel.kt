package co.edu.unab.chatbotacademico

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import co.edu.unab.chatbotacademico.data.ChatApi
import co.edu.unab.chatbotacademico.data.ChatApiException
import co.edu.unab.chatbotacademico.data.ChatRequest
import co.edu.unab.chatbotacademico.data.Prefs
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.io.IOException
import java.net.SocketTimeoutException
import java.util.UUID

data class Msg(
    val id: Long,
    val fromUser: Boolean,
    val text: String,
    val intencion: String? = null,
    val fuentes: List<String> = emptyList(),
)

data class UiState(
    val loaded: Boolean = false,
    val codigo: String? = null,
    val baseUrl: String = BuildConfig.BASE_URL,
    val apiKey: String = BuildConfig.CHATBOT_KEY,
    val messages: List<Msg> = emptyList(),
    val typing: Boolean = false,
    /** Mensaje de error amable; si no es null se muestra con botón Reintentar. */
    val error: String? = null,
)

val CODIGO_REGEX = Regex("^U\\d{8}$")

class ChatViewModel(app: Application) : AndroidViewModel(app) {
    private val prefs = Prefs(app)
    private val api = ChatApi()

    private val _state = MutableStateFlow(UiState())
    val state: StateFlow<UiState> = _state.asStateFlow()

    private var sessionId: String = UUID.randomUUID().toString()
    private var nextId = 0L
    private var lastUserText: String? = null

    init {
        viewModelScope.launch {
            val s = prefs.load()
            s.sessionId?.let { sessionId = it }
            _state.update {
                it.copy(
                    loaded = true,
                    codigo = s.codigo?.takeIf { c -> CODIGO_REGEX.matches(c) },
                    baseUrl = s.baseUrl?.takeIf { u -> u.isNotBlank() } ?: BuildConfig.BASE_URL,
                    apiKey = s.apiKey ?: BuildConfig.CHATBOT_KEY,
                )
            }
        }
    }

    fun login(codigo: String, baseUrl: String, apiKey: String) {
        val c = codigo.trim().uppercase()
        val u = baseUrl.trim().ifBlank { BuildConfig.BASE_URL }
        if (!CODIGO_REGEX.matches(c)) return
        viewModelScope.launch {
            val previous = _state.value.codigo
            prefs.saveLogin(c, u, apiKey.trim())
            // Una sesión por instalación + estudiante; se reutiliza si ya existía.
            val existing = prefs.load().sessionId
            sessionId = existing ?: UUID.randomUUID().toString().also { prefs.saveSession(c, it) }
            lastUserText = null
            _state.update {
                it.copy(
                    codigo = c, baseUrl = u, apiKey = apiKey.trim(),
                    messages = if (previous == c) it.messages else emptyList(),
                    error = null, typing = false,
                )
            }
        }
    }

    fun newConversation() {
        val c = _state.value.codigo ?: return
        sessionId = UUID.randomUUID().toString()
        lastUserText = null
        val sid = sessionId
        viewModelScope.launch { prefs.saveSession(c, sid) }
        _state.update { it.copy(messages = emptyList(), error = null, typing = false) }
    }

    fun logout() {
        lastUserText = null
        viewModelScope.launch { prefs.clearCodigo() }
        _state.update { it.copy(codigo = null, messages = emptyList(), error = null, typing = false) }
    }

    fun send(text: String) {
        val t = text.trim()
        if (t.isEmpty() || _state.value.typing) return
        _state.update { it.copy(messages = it.messages + Msg(nextId++, true, t), error = null) }
        request(t)
    }

    fun retry() {
        val t = lastUserText ?: return
        if (_state.value.typing) return
        _state.update { it.copy(error = null) }
        request(t)
    }

    private fun request(text: String) {
        val st = _state.value
        val codigo = st.codigo ?: return
        lastUserText = text
        _state.update { it.copy(typing = true) }
        viewModelScope.launch {
            try {
                val r = api.send(st.baseUrl, st.apiKey, ChatRequest(sessionId, codigo, text))
                lastUserText = null
                _state.update {
                    it.copy(
                        typing = false,
                        messages = it.messages + Msg(
                            nextId++, false,
                            r.respuesta.ifBlank { "No recibí contenido en la respuesta." },
                            r.intencion?.takeIf { i -> i.isNotBlank() },
                            r.fuentes.orEmpty(),
                        ),
                    )
                }
            } catch (e: Exception) {
                val msg = when (e) {
                    is ChatApiException -> e.message ?: "Ocurrió un error."
                    is SocketTimeoutException -> "El asistente tardó demasiado en responder. Intenta de nuevo."
                    is IOException -> "No pude conectarme al servidor. Revisa tu conexión a internet."
                    else -> "Ocurrió un error inesperado."
                }
                _state.update { it.copy(typing = false, error = msg) }
            }
        }
    }
}
