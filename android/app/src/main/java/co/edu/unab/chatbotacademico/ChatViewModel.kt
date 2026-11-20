package co.edu.unab.chatbotacademico

import android.app.Application
import android.graphics.Bitmap
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import co.edu.unab.chatbotacademico.data.Accion
import co.edu.unab.chatbotacademico.data.Adjunto
import co.edu.unab.chatbotacademico.data.ChatApi
import co.edu.unab.chatbotacademico.data.ChatApiException
import co.edu.unab.chatbotacademico.data.ChatRequest
import co.edu.unab.chatbotacademico.data.Grafica
import co.edu.unab.chatbotacademico.data.Prefs
import co.edu.unab.chatbotacademico.data.checkoutUrl
import co.edu.unab.chatbotacademico.data.prepararImagen
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
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
    val miniatura: Bitmap? = null,
    val acciones: List<Accion> = emptyList(),
    val graficas: List<Grafica> = emptyList(),
    val qrDetectados: List<String> = emptyList(),
)

data class ConsultaPago(
    val estado: String? = null,
    val consultando: Boolean = false,
    val error: String? = null,
)

data class UiState(
    val loaded: Boolean = false,
    val codigo: String? = null,
    val baseUrl: String = BuildConfig.BASE_URL,
    val apiKey: String = "",
    val messages: List<Msg> = emptyList(),
    val typing: Boolean = false,
    /** Mensaje de error amable; si no es null se muestra con botón Reintentar. */
    val error: String? = null,
    val adjunto: Adjunto? = null,
    val preparandoImagen: Boolean = false,
    val errorImagen: String? = null,
    val ordenAbierta: String? = null,
    val pagos: Map<String, ConsultaPago> = emptyMap(),
)

val CODIGO_REGEX = Regex("^U\\d{8}$")
private val ORDEN_REGEX = Regex("[A-Za-z0-9_-]{1,60}")

class ChatViewModel(app: Application) : AndroidViewModel(app) {
    private val prefs = Prefs(app)
    private val api = ChatApi()

    private val _state = MutableStateFlow(UiState())
    val state: StateFlow<UiState> = _state.asStateFlow()

    private var sessionId: String = UUID.randomUUID().toString()
    private var nextId = 0L
    private var ultimoEnvio: ChatRequest? = null
    private var peticionChat: Job? = null
    private var cargaImagen: Job? = null

    init {
        viewModelScope.launch {
            val s = prefs.load()
            s.sessionId?.let { sessionId = it }
            _state.update {
                it.copy(
                    loaded = true,
                    codigo = s.codigo?.takeIf { c -> CODIGO_REGEX.matches(c) },
                    baseUrl = s.baseUrl?.takeIf { u -> u.isNotBlank() } ?: BuildConfig.BASE_URL,
                    apiKey = s.apiKey.orEmpty(),
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
            ultimoEnvio = null
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
        val sid = sessionId
        viewModelScope.launch { prefs.saveSession(c, sid) }
        limpiarConversacion(c)
    }

    fun logout() {
        viewModelScope.launch { prefs.clearCodigo() }
        limpiarConversacion(null)
    }

    private fun limpiarConversacion(codigo: String?) {
        peticionChat?.cancel()
        cargaImagen?.cancel()
        ultimoEnvio = null
        _state.update {
            it.copy(
                codigo = codigo, messages = emptyList(), error = null, typing = false,
                adjunto = null, preparandoImagen = false, errorImagen = null,
                ordenAbierta = null, pagos = emptyMap(),
            )
        }
    }

    suspend fun personas(baseUrl: String) = api.personas(baseUrl)

    suspend fun hoy() = state.value.let { api.hoy(it.baseUrl, it.apiKey, checkNotNull(it.codigo)) }

    fun adjuntarImagen(uri: Uri) {
        if (_state.value.codigo == null || _state.value.typing) return
        cargaImagen?.cancel()
        _state.update { it.copy(preparandoImagen = true, errorImagen = null) }
        cargaImagen = viewModelScope.launch {
            try {
                val imagen = prepararImagen(getApplication<Application>().contentResolver, uri)
                _state.update { it.copy(adjunto = imagen, preparandoImagen = false) }
            } catch (e: CancellationException) {
                throw e
            } catch (_: Exception) {
                _state.update { it.copy(preparandoImagen = false, errorImagen = "No se pudo leer la imagen. Prueba con otra foto.") }
            }
        }
    }

    fun quitarImagen() {
        cargaImagen?.cancel()
        _state.update { it.copy(adjunto = null, preparandoImagen = false, errorImagen = null) }
    }

    fun send(text: String, incluirAdjunto: Boolean) {
        val st = _state.value
        val codigo = st.codigo ?: return
        if (st.typing || (incluirAdjunto && st.preparandoImagen)) return
        val adjunto = st.adjunto.takeIf { incluirAdjunto }
        val texto = text.trim().ifEmpty {
            if (adjunto == null) return
            "¿Qué ves en esta imagen?"
        }
        val mensaje = Msg(nextId++, true, texto, miniatura = adjunto?.miniatura)
        _state.update {
            it.copy(
                messages = it.messages + mensaje,
                adjunto = if (incluirAdjunto) null else it.adjunto,
                errorImagen = if (incluirAdjunto) null else it.errorImagen,
            )
        }
        request(ChatRequest(sessionId, codigo, texto, adjunto?.dataUrl))
    }

    fun retry() {
        if (!_state.value.typing) ultimoEnvio?.let(::request)
    }

    private fun request(peticion: ChatRequest) {
        val st = _state.value
        ultimoEnvio = peticion
        _state.update { it.copy(typing = true, error = null) }
        peticionChat = viewModelScope.launch {
            try {
                val r = api.send(st.baseUrl, st.apiKey, peticion)
                ultimoEnvio = null
                _state.update {
                    it.copy(
                        typing = false,
                        messages = it.messages + Msg(
                            nextId++, false,
                            r.respuesta.ifBlank { r.imagen?.descripcion.orEmpty() }.ifBlank {
                                if (r.acciones.isEmpty() && r.graficas.isEmpty() && r.imagen?.qr.isNullOrEmpty()) {
                                    "No recibí contenido en la respuesta."
                                } else ""
                            },
                            r.intencion?.takeIf { i -> i.isNotBlank() },
                            r.fuentes.orEmpty(),
                            acciones = r.acciones,
                            graficas = r.graficas,
                            qrDetectados = r.imagen?.qr.orEmpty(),
                        ),
                    )
                }
            } catch (e: CancellationException) {
                throw e
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

    fun abrirPago(orderId: String) {
        val st = _state.value
        if (st.codigo == null || !ORDEN_REGEX.matches(orderId) || checkoutUrl(st.baseUrl, orderId) == null) return
        _state.update { it.copy(ordenAbierta = orderId) }
    }

    fun cerrarPago() {
        val orderId = _state.value.ordenAbierta ?: return
        _state.update { it.copy(ordenAbierta = null) }
        consultarPago(orderId)
    }

    fun consultarPago(orderId: String) {
        val st = _state.value
        val anterior = st.pagos[orderId] ?: ConsultaPago()
        if (st.codigo == null || !ORDEN_REGEX.matches(orderId) || anterior.consultando) return
        val sesion = sessionId
        _state.update { it.copy(pagos = it.pagos + (orderId to anterior.copy(consultando = true, error = null))) }
        viewModelScope.launch {
            val consulta = try {
                ConsultaPago(estado = api.pago(st.baseUrl, orderId).estado)
            } catch (e: CancellationException) {
                throw e
            } catch (_: Exception) {
                anterior.copy(consultando = false, error = "No se pudo actualizar el estado del pago.")
            }
            if (sesion == sessionId && st.codigo == _state.value.codigo) {
                _state.update { it.copy(pagos = it.pagos + (orderId to consulta)) }
            }
        }
    }
}
