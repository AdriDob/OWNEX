package ai.rastro.watch.ui

import ai.rastro.watch.api.ApiClient
import ai.rastro.watch.api.WearOSApi
import ai.rastro.watch.model.ApiModels.WearOSApproval
import ai.rastro.watch.model.ApiModels.WearOSNotification
import ai.rastro.watch.model.ApiModels.WearOSStatus
import ai.rastro.watch.preferences.PreferencesManager
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.util.concurrent.atomic.AtomicBoolean

class WatchViewModel(
    private val preferencesManager: PreferencesManager
) : ViewModel() {

    // State
    private val _status = MutableLiveData<WearOSStatus?>()
    val status: LiveData<WearOSStatus?> = _status

    private val _notifications = MutableLiveData<List<WearOSNotification>>(emptyList())
    val notifications: LiveData<List<WearOSNotification>> = _notifications

    private val _pendingApprovals = MutableLiveData<List<WearOSApproval>>(emptyList())
    val pendingApprovals: LiveData<List<WearOSApproval>> = _pendingApprovals

    private val _isLoading = MutableLiveData<Boolean>(false)
    val isLoading: LiveData<Boolean> = _isLoading

    private val _error = MutableLiveData<String?>()
    val error: LiveData<String?> = _error

    private val _isConnected = MutableLiveData<Boolean>(false)
    val isConnected: LiveData<Boolean> = _isConnected

    private val syncJob = AtomicBoolean(false)
    private const val SYNC_INTERVAL_MS = 5 * 60 * 1000 // 5 minutes

    init {
        startSyncLoop()
    }

    private fun startSyncLoop() {
        viewModelScope.launch {
            while (true) {
                syncAll()
                delay(SYNC_INTERVAL_MS)
            }
        }
    }

    fun syncAll() {
        if (syncJob.getAndSet(true)) return

        viewModelScope.launch {
            _isLoading.postValue(true)
            _error.postValue(null)

            try {
                val api = ApiClient.api()
                val statusResponse = api.getStatus().await()
                _status.postValue(statusResponse)
                _isConnected.postValue(true)

                val notificationsResponse = api.getNotifications(unreadOnly = false, limit = 20).await()
                _notifications.postValue(notificationsResponse)

                val approvalsResponse = api.getPendingApprovals().await()
                _pendingApprovals.postValue(approvalsResponse)

                _error.postValue(null)
            } catch (e: Exception) {
                _isConnected.postValue(false)
                _error.postValue(e.message ?: "Error de conexión")
            } finally {
                _isLoading.postValue(false)
                syncJob.set(false)
            }
        }
    }

    fun markNotificationRead(notificationId: String) {
        viewModelScope.launch {
            try {
                ApiClient.api().markNotificationRead(notificationId).await()
                val current = _notifications.value?.toMutableList() ?: emptyList()
                val updated = current.map { n ->
                    if (n.notificationId == notificationId) n.copy(read = true) else n
                }
                _notifications.postValue(updated)
            } catch (e: Exception) {
                _error.postValue("Error al marcar notificación: ${e.message}")
            }
        }
    }

    fun respondToApproval(requestId: String, approved: Boolean) {
        viewModelScope.launch {
            _isLoading.postValue(true)
            try {
                val response = WearOSApi.ApprovalResponse(approved)
                ApiClient.api().respondApproval(requestId, response).await()
                val current = _pendingApprovals.value?.toMutableList() ?: emptyList()
                val updated = current.filter { it.requestId != requestId }
                _pendingApprovals.postValue(updated)
                _error.postValue(null)
            } catch (e: Exception) {
                _error.postValue("Error al responder aprobación: ${e.message}")
            } finally {
                _isLoading.postValue(false)
            }
        }
    }

    fun sendNotification(title: String, message: String, level: String = "medium") {
        viewModelScope.launch {
            try {
                val request = WearOSApi.SendNotificationRequest(
                    title = title,
                    message = message,
                    level = level
                )
                ApiClient.api().sendNotification(request).await()
                _error.postValue(null)
            } catch (e: Exception) {
                _error.postValue("Error al enviar notificación: ${e.message}")
            }
        }
    }

    fun refreshBaseUrl() {
        ApiClient.rebuild(preferencesManager)
    }

    // Health check for connection status
    fun checkConnection(): Boolean {
        return try {
            ApiClient.api().healthCheck().execute().isSuccessful
        } catch (e: Exception) {
            false
        }
    }
}