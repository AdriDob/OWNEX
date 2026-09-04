package ai.rastro.watch.preferences

import android.content.Context
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.rxjava3.RxDataStore
import ai.rastro.watch.BuildConfig
import io.reactivex.rxjava3.core.Completable
import io.reactivex.rxjava3.core.Single

object PreferencesManager {

    private const val BASE_URL_KEY = "base_url"
    private const val DEVICE_ID_KEY = "device_id"
    private const val AUTH_TOKEN_KEY = "auth_token"
    private const val NOTIFICATIONS_ENABLED_KEY = "notifications_enabled"
    private const val SYNC_INTERVAL_KEY = "sync_interval_minutes"

    private const val DEFAULT_BASE_URL = "http://10.0.2.2:8000"
    private const val DEFAULT_SYNC_INTERVAL = 5

    private var dataStore: RxDataStore<Preferences>? = null

    fun initialize(context: Context) {
        if (dataStore == null) {
            dataStore = RxDataStore(context, BuildConfig.APPLICATION_ID + ".preferences")
        }
    }

    val baseUrl: Single<String>
        get() = getString(BASE_URL_KEY, DEFAULT_BASE_URL)

    suspend fun setBaseUrl(url: String) = updateString(BASE_URL_KEY, url)

    val deviceId: Single<String>
        get() = getString(DEVICE_ID_KEY, "").map { if (it.isBlank()) generateDeviceId() else it }

    suspend fun setDeviceId(id: String) = updateString(DEVICE_ID_KEY, id)

    val authToken: Single<String>
        get() = getString(AUTH_TOKEN_KEY, "")

    suspend fun setAuthToken(token: String) = updateString(AUTH_TOKEN_KEY, token)

    val notificationsEnabled: Single<Boolean>
        get() = dataStore!!.data.first()
            .map { it[PreferencesManager.notificationsEnabledKey] ?: true }

    suspend fun setNotificationsEnabled(enabled: Boolean) = updateBoolean(NOTIFICATIONS_ENABLED_KEY, enabled)

    val syncInterval: Single<Int>
        get() = dataStore!!.data.first()
            .map { it[PreferencesManager.syncIntervalKey] ?: DEFAULT_SYNC_INTERVAL }

    suspend fun setSyncInterval(minutes: Int) = updateInt(SYNC_INTERVAL_KEY, minutes)

    private fun generateDeviceId(): String {
        return "watch_${System.currentTimeMillis()}_${(Math.random() * 10000).toInt()}"
    }

    private fun getString(key: String, defaultValue: String): Single<String> =
        dataStore!!.data.first().map { it[stringPreferencesKey(key)] ?: defaultValue }

    private suspend fun updateString(key: String, value: String): Completable =
        dataStore!!.updateDataAsync { it.putString(stringPreferencesKey(key), value) }.toCompletable()

    private fun getInt(key: String, defaultValue: Int): Single<Int> =
        dataStore!!.data.first().map { it[intPreferencesKey(key)] ?: defaultValue }

    private suspend fun updateInt(key: String, value: Int): Completable =
        dataStore!!.updateDataAsync { it.putInt(intPreferencesKey(key), value) }.toCompletable()

    private fun getBoolean(key: String, defaultValue: Boolean): Single<Boolean> =
        dataStore!!.data.first().map { it[booleanPreferencesKey(key)] ?: defaultValue }

    private suspend fun updateBoolean(key: String, value: Boolean): Completable =
        dataStore!!.updateDataAsync { it.putBoolean(booleanPreferencesKey(key), value) }.toCompletable()

    companion object {
        val notificationsEnabledKey = booleanPreferencesKey(NOTIFICATIONS_ENABLED_KEY)
        val syncIntervalKey = intPreferencesKey(SYNC_INTERVAL_KEY)
    }
}