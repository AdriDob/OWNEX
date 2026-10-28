package ai.rastro.watch.sync

import android.content.Context
import android.util.Log
import com.google.android.gms.wearable.*
import kotlinx.coroutines.tasks.await

/**
 * DataClientPairing — Handles phone-watch pairing via WearOS DataClient.
 *
 * Syncs: system status, pending approvals, next action, revenue summary.
 * Uses path-based data items for efficient partial updates.
 */
class DataClientPairing(private val context: Context) {

    private val TAG = "DataClientPairing"
    private val dataClient by lazy { Wearable.getDataClient(context) }

    // Data paths
    companion object {
        const val PATH_STATUS = "/ownex/status"
        const val PATH_APPROVALS = "/ownex/approvals"
        const val PATH_ACTION = "/ownex/next-action"
        const val PATH_REVENUE = "/ownex/revenue"
        const val PATH_CONFIG = "/ownex/config"
    }

    /**
     * Check if a phone is connected.
     */
    suspend fun isPhoneConnected(): Boolean {
        return try {
            val nodes = Wearable.getNodeClient(context).connectedNodes.await()
            nodes.isNotEmpty()
        } catch (e: Exception) {
            Log.w(TAG, "Failed to check phone connection", e)
            false
        }
    }

    /**
     * Get connected phone node IDs.
     */
    suspend fun getConnectedNodes(): List<Node> {
        return try {
            Wearable.getNodeClient(context).connectedNodes.await()
        } catch (e: Exception) {
            Log.w(TAG, "Failed to get connected nodes", e)
            emptyList()
        }
    }

    /**
     * Push status data to phone.
     */
    suspend fun pushStatus(status: Map<String, Any>) {
        try {
            val putDataMapRequest = PutDataMapRequest.create(PATH_STATUS).apply {
                status.forEach { (key, value) ->
                    when (value) {
                        is String -> dataMap.putString(key, value)
                        is Boolean -> dataMap.putBoolean(key, value)
                        is Int -> dataMap.putInt(key, value)
                        is Double -> dataMap.putDouble(key, value)
                        is Long -> dataMap.putLong(key, value)
                    }
                }
                dataMap.putLong("timestamp", System.currentTimeMillis())
            }
            val request = putDataMapRequest.asPutDataRequest().setUrgent()
            dataClient.putDataItem(request).await()
            Log.d(TAG, "Status pushed to phone")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to push status", e)
        }
    }

    /**
     * Push approvals to phone.
     */
    suspend fun pushApprovals(approvals: List<Map<String, String>>) {
        try {
            val putDataMapRequest = PutDataMapRequest.create(PATH_APPROVALS).apply {
                dataMap.putInt("count", approvals.size)
                approvals.forEachIndexed { index, approval ->
                    approval.forEach { (key, value) ->
                        dataMap.putString("approval_${index}_$key", value)
                    }
                }
                dataMap.putLong("timestamp", System.currentTimeMillis())
            }
            val request = putDataMapRequest.asPutDataRequest().setUrgent()
            dataClient.putDataItem(request).await()
            Log.d(TAG, "Approvals pushed: ${approvals.size} items")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to push approvals", e)
        }
    }

    /**
     * Push next action to phone.
     */
    suspend fun pushNextAction(action: Map<String, Any>) {
        try {
            val putDataMapRequest = PutDataMapRequest.create(PATH_ACTION).apply {
                action.forEach { (key, value) ->
                    when (value) {
                        is String -> dataMap.putString(key, value)
                        is Double -> dataMap.putDouble(key, value)
                        is Int -> dataMap.putInt(key, value)
                    }
                }
                dataMap.putLong("timestamp", System.currentTimeMillis())
            }
            val request = putDataMapRequest.asPutDataRequest().setUrgent()
            dataClient.putDataItem(request).await()
            Log.d(TAG, "Next action pushed")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to push next action", e)
        }
    }

    /**
     * Read config from phone.
     */
    suspend fun readConfig(): Map<String, String> {
        return try {
            val dataItem = dataClient.getDataItems(PATH_CONFIG).await()
            val map = mutableMapOf<String, String>()
            if (dataItem.count > 0) {
                val dataMap = DataMapItem.fromDataItem(dataItem.first()).dataMap
                dataMap.keys.forEach { key ->
                    map[key] = dataMap.getString(key) ?: ""
                }
            }
            map
        } catch (e: Exception) {
            Log.w(TAG, "Failed to read config", e)
            emptyMap()
        }
    }

    /**
     * Send a message to phone (for actions like approve/reject).
     */
    suspend fun sendMessage(path: String, data: Map<String, Any>) {
        try {
            val nodes = getConnectedNodes()
            for (node in nodes) {
                val payload = data.entries.joinToString("&") { "${it.key}=${it.value}" }.toByteArray()
                Wearable.getMessageClient(context).sendMessage(node.id, path, payload).await()
                Log.d(TAG, "Message sent to ${node.displayName}: $path")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to send message", e)
        }
    }

    /**
     * Listen for data changes from phone.
     */
    fun addDataListener(listener: DataClient.OnDataChangedListener) {
        dataClient.addListener(listener)
    }

    fun removeDataListener(listener: DataClient.OnDataChangedListener) {
        dataClient.removeListener(listener)
    }

    /**
     * Clean up resources.
     */
    fun destroy() {
        dataClient.close()
    }
}
