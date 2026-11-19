package co.edu.unab.chatbotacademico.data

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.first

private val Context.dataStore by preferencesDataStore(name = "chatbot_prefs")

data class Saved(val codigo: String?, val baseUrl: String?, val sessionId: String?, val apiKey: String?)

class Prefs(private val context: Context) {
    private val kCodigo = stringPreferencesKey("codigo")
    private val kUrl = stringPreferencesKey("baseUrl")
    private val kApiKey = stringPreferencesKey("apiKey")
    private fun kSession(codigo: String) = stringPreferencesKey("session_$codigo")

    suspend fun load(): Saved {
        val p = context.dataStore.data.first()
        val codigo = p[kCodigo]
        return Saved(codigo, p[kUrl], codigo?.let { p[kSession(it)] }, p[kApiKey])
    }

    suspend fun saveLogin(codigo: String, baseUrl: String, apiKey: String) {
        context.dataStore.edit { it[kCodigo] = codigo; it[kUrl] = baseUrl; it[kApiKey] = apiKey }
    }

    suspend fun saveSession(codigo: String, sessionId: String) {
        context.dataStore.edit { it[kSession(codigo)] = sessionId }
    }

    suspend fun clearCodigo() {
        context.dataStore.edit { it.remove(kCodigo) }
    }
}
