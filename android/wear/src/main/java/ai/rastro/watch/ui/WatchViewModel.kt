package ai.rastro.watch.ui

import ai.rastro.watch.api.ApiClient
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
    private companion object {
        const val SYNC_INTERVAL_MS = 5 * 60 * 1000L // 5 minutes
    }

    init {
        ApiClient.initialize(preferencesManager)
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
                val statusResponse = withContext(Dispatchers.IO) { api.getStatus().execute().body() }
                _status.postValue(statusResponse)
                _isConnected.postValue(true)

                val notificationsResponse = withContext(Dispatchers.IO) {
                    api.getNotifications(unreadOnly = false, limit = 20).execute().body()
                }
                _notifications.postValue(notificationsResponse ?: emptyList())

                val approvalsResponse = withContext(Dispatchers.IO) {
                    api.getPendingApprovals().execute().body()
                }
                _pendingApprovals.postValue(approvalsResponse ?: emptyList())

                _error.postValue(null)
            } catch (e: Exception) {
                _isConnected.postValue(false)
                _error.postValue(e.message ?: "Connection error")
            } finally {
                _isLoading.postValue(false)
                syncJob.set(false)
            }
        }
    }

    fun markNotificationRead(notificationId: String) {
        viewModelScope.launch {
            try {
                withContext(Dispatchers.IO) {
                    ApiClient.api().markNotificationRead(notificationId).execute()
                }
                val current = _notifications.value?.toMutableList() ?: emptyList()
                val updated = current.map { n ->
                    if (n.notificationId == notificationId) n.copy(read = true) else n
                }
                _notifications.postValue(updated)
            } catch (e: Exception) {
                _error.postValue("Error marking notification: ${e.message}")
            }
        }
    }

    fun respondToApproval(requestId: String, approved: Boolean) {
        viewModelScope.launch {
            _isLoading.postValue(true)
            try {
                val response = ai.rastro.watch.model.ApiModels.ApprovalResponse(approved)
                withContext(Dispatchers.IO) {
                    ApiClient.api().respondApproval(requestId, response).execute()
                }
                val current = _pendingApprovals.value?.toMutableList() ?: emptyList()
                val updated = current.filter { it.requestId != requestId }
                _pendingApprovals.postValue(updated)
                _error.postValue(null)
            } catch (e: Exception) {
                _error.postValue("Error responding to approval: ${e.message}")
            } finally {
                _isLoading.postValue(false)
            }
        }
    }

    fun sendNotification(title: String, message: String, level: String = "medium") {
        viewModelScope.launch {
            try {
                val request = ai.rastro.watch.model.ApiModels.SendNotificationRequest(
                    title = title,
                    message = message,
                    level = level
                )
                withContext(Dispatchers.IO) {
                    ApiClient.api().sendNotification(request).execute()
                }
                _error.postValue(null)
            } catch (e: Exception) {
                _error.postValue("Error sending notification: ${e.message}")
            }
        }
    }

    fun refreshBaseUrl() {
        ApiClient.rebuild(preferencesManager)
    }

    fun checkConnection(): Boolean {
        return try {
            withContext(Dispatchers.IO) {
                ApiClient.api().healthCheck().execute().isSuccessful
            }
        } catch (e: Exception) {
            false
        }
    }
}
