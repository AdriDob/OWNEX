package ai.rastro.watch.preferences

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.runBlocking

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "ownex_watch_prefs")

class PreferencesManager {

    private var context: Context? = null

    fun initialize(context: Context) {
        this.context = context
    }

    private val ds: DataStore<Preferences>
        get() = context?.dataStore ?: throw IllegalStateException("PreferencesManager not initialized")

    companion object {
        private val BASE_URL_KEY = stringPreferencesKey("base_url")
        private val DEVICE_ID_KEY = stringPreferencesKey("device_id")
        private val AUTH_TOKEN_KEY = stringPreferencesKey("auth_token")
        private val NOTIFICATIONS_ENABLED_KEY = booleanPreferencesKey("notifications_enabled")
        private val SYNC_INTERVAL_KEY = intPreferencesKey("sync_interval_minutes")

        private const val DEFAULT_BASE_URL = "http://10.0.2.2:8000"
        private const val DEFAULT_SYNC_INTERVAL = 5
    }

    val baseUrl: String
        get() = runBlocking {
            ds.data.map { it[BASE_URL_KEY] ?: DEFAULT_BASE_URL }.first()
        }

    suspend fun setBaseUrl(url: String) {
        ds.edit { it[BASE_URL_KEY] = url }
    }

    val deviceId: String
        get() = runBlocking {
            ds.data.map { it[DEVICE_ID_KEY] ?: generateDeviceId() }.first()
        }

    suspend fun setDeviceId(id: String) {
        ds.edit { it[DEVICE_ID_KEY] = id }
    }

    val authToken: String
        get() = runBlocking {
            ds.data.map { it[AUTH_TOKEN_KEY] ?: "" }.first()
        }

    suspend fun setAuthToken(token: String) {
        ds.edit { it[AUTH_TOKEN_KEY] = token }
    }

    val notificationsEnabled: Boolean
        get() = runBlocking {
            ds.data.map { it[NOTIFICATIONS_ENABLED_KEY] ?: true }.first()
        }

    suspend fun setNotificationsEnabled(enabled: Boolean) {
        ds.edit { it[NOTIFICATIONS_ENABLED_KEY] = enabled }
    }

    val syncInterval: Int
        get() = runBlocking {
            ds.data.map { it[SYNC_INTERVAL_KEY] ?: DEFAULT_SYNC_INTERVAL }.first()
        }

    suspend fun setSyncInterval(minutes: Int) {
        ds.edit { it[SYNC_INTERVAL_KEY] = minutes }
    }

    private fun generateDeviceId(): String {
        return "watch_${System.currentTimeMillis()}_${(Math.random() * 10000).toInt()}"
    }
}
