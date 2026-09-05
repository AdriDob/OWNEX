package ai.rastro.watch.sync

import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.util.Log
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleObserver
import androidx.lifecycle.OnLifecycleEvent
import androidx.lifecycle.ProcessLifecycleOwner
import ai.rastro.watch.preferences.PreferencesManager
import ai.rastro.watch.api.ApiClient
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class SyncService : Service(), LifecycleObserver {

    private val TAG = "SyncService"
    private var syncJob: Job? = null
    private val isRunning = java.util.concurrent.atomic.AtomicBoolean(false)

    override fun onCreate() {
        super.onCreate()
        ProcessLifecycleOwner.get().lifecycle.addObserver(this)
        Log.d(TAG, "SyncService created")
    }

    @OnLifecycleEvent(Lifecycle.Event.ON_START)
    fun onAppForeground() {
        if (!isRunning.getAndSet(true)) {
            startSyncLoop()
        }
    }

    @OnLifecycleEvent(Lifecycle.Event.ON_STOP)
    fun onAppBackground() {
        // Keep syncing in background for dataSync foreground service
    }

    private fun startSyncLoop() {
        val scope = CoroutineScope(Dispatchers.IO)
        syncJob = scope.launch {
            while (isRunning.get()) {
                try {
                    syncAll()
                } catch (e: Exception) {
                    Log.e(TAG, "Sync error: ${e.message}")
                }
                delay(getSyncIntervalMinutes() * 60 * 1000L)
            }
        }
    }

    private fun getSyncIntervalMinutes(): Long {
        return try {
            PreferencesManager.syncInterval.blockingGet().toLong()
        } catch (e: Exception) {
            5L
        }
    }

    private fun syncAll() {
        try {
            val api = ApiClient.api()
            val statusResponse = api.getStatus().await()
            Log.d(TAG, "Sync completed: status=${statusResponse.systemOnline}")
        } catch (e: Exception) {
            Log.e(TAG, "Sync failed: ${e.message}")
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        super.onDestroy()
        isRunning.set(false)
        syncJob?.cancel()
        ProcessLifecycleOwner.get().lifecycle.removeObserver(this)
        Log.d(TAG, "SyncService destroyed")
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (!isRunning.getAndSet(true)) {
            startSyncLoop()
        }
        return START_STICKY
    }
}