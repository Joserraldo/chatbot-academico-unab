package co.edu.unab.chatbotacademico

import android.content.Context
import android.content.res.Configuration
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import co.edu.unab.chatbotacademico.ui.ChatScreen
import co.edu.unab.chatbotacademico.ui.Crema
import co.edu.unab.chatbotacademico.ui.FondoUnab
import co.edu.unab.chatbotacademico.ui.LoginScreen
import co.edu.unab.chatbotacademico.ui.UnabTheme
import java.util.Locale

class MainActivity : ComponentActivity() {
    private val vm: ChatViewModel by viewModels()

    override fun attachBaseContext(newBase: Context) {
        val configuracion = Configuration().apply { setLocale(Locale.forLanguageTag("es-CO")) }
        super.attachBaseContext(newBase.createConfigurationContext(configuracion))
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val barras = SystemBarStyle.light(Color.Transparent.toArgb(), Crema.toArgb())
        enableEdgeToEdge(statusBarStyle = barras, navigationBarStyle = barras)
        if (Build.VERSION.SDK_INT >= 29) window.isNavigationBarContrastEnforced = false
        setContent {
            UnabTheme {
                val st by vm.state.collectAsState()
                FondoUnab {
                    when {
                        !st.loaded -> Box(Modifier.fillMaxSize(), Alignment.Center) { CircularProgressIndicator() }
                        st.codigo == null -> LoginScreen(st.baseUrl, st.apiKey, vm::personas, vm::login)
                        else -> ChatScreen(
                            st = st,
                            onSend = vm::send,
                            onRetry = vm::retry,
                            onNew = vm::newConversation,
                            onLogout = vm::logout,
                            onAdjuntar = vm::adjuntarImagen,
                            onQuitarAdjunto = vm::quitarImagen,
                            onPago = vm::abrirPago,
                            onCerrarPago = vm::cerrarPago,
                            onConsultarPago = vm::consultarPago,
                            cargarHoy = vm::hoy,
                        )
                    }
                }
            }
        }
    }
}
