package co.edu.unab.chatbotacademico

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Surface
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import co.edu.unab.chatbotacademico.ui.ChatScreen
import co.edu.unab.chatbotacademico.ui.LoginScreen
import co.edu.unab.chatbotacademico.ui.UnabTheme

class MainActivity : ComponentActivity() {
    private val vm: ChatViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            UnabTheme {
                val st by vm.state.collectAsState()
                Surface(Modifier.fillMaxSize()) {
                    when {
                        !st.loaded -> Box(Modifier.fillMaxSize(), Alignment.Center) { CircularProgressIndicator() }
                        st.codigo == null -> LoginScreen(st.baseUrl, vm::login)
                        else -> ChatScreen(st, vm::send, vm::retry, vm::newConversation, vm::logout)
                    }
                }
            }
        }
    }
}
