package ai.catseye.wearos

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.support.wearable.activity.WearableActivity
import android.support.wearable.view.WatchViewStub
import android.view.View
import android.widget.Button
import android.widget.ImageView
import android.widget.TextView
import androidx.core.app.NotificationCompat
import androidx.wear.widget.WearableRecyclerView
import org.json.JSONObject

/**
 * ORION Wear OS Companion — Panel táctil de alerta y decisión rápida
 *
 * Features:
 * - Salud del sistema en un vistazo
 * - Notificaciones críticas
 * - Aprobaciones ráctas
 * - Resumen de MERLIN
 * - Sincronización con Android Companion
 */
class MainActivity : WearableActivity() {

    private lateinit var systemStatusView: TextView
    private lateinit var workflowsCountView: TextView
    private lateinit var approvalsCountView: TextView
    private lateinit var notificationIcon: ImageView
    private lateinit var notificationTitle: TextView
    private lateinit var notificationMessage: TextView
    private lateinit var approveButton: Button
    private lateinit var rejectButton: Button
    private lateinit var merlinSummaryView: TextView

    private var currentApproval: JSONObject? = null
    private var currentNotification: JSONObject? = null

    companion object {
        private const val NOTIFICATION_CHANNEL_ID = "orion_wear_channel"
        private const val CHANNEL_NAME = "ORION Wear Notifications"
        private const val CHANNEL_IMPORTANCE = NotificationManager.IMPORTANCE_HIGH
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // Create notification channel
        createNotificationChannel()

        // Initialize views
        val stub = findViewById<WatchViewStub>(R.id.watch_view_stub)
        stub.setOnLayoutListener {
            initializeViews()
        }
    }

    private fun initializeViews() {
        systemStatusView = findViewById(R.id.system_status)
        workflowsCountView = findViewById(R.id.workflows_count)
        approvalsCountView = findViewById(R.id.approvals_count)
        notificationIcon = findViewById(R.id.notification_icon)
        notificationTitle = findViewById(R.id.notification_title)
        notificationMessage = findViewById(R.id.notification_message)
        approveButton = findViewById(R.id.btn_approve)
        rejectButton = findViewById(R.id.btn_reject)
        merlinSummaryView = findViewById(R.id.merlin_summary)

        // Setup button listeners
        approveButton.setOnClickListener { approveCurrentApproval() }
        rejectButton.setOnClickListener { rejectCurrentApproval() }

        // Start polling for system status
        startPolling()
    }

    private fun createNotificationChannel() {
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val channel = NotificationChannel(
            NOTIFICATION_CHANNEL_ID,
            CHANNEL_NAME,
            CHANNEL_IMPORTANCE
        ).apply {
            description = "Critical notifications from ORION system"
            enableVibration(true)
            enableLights(true)
        }
        notificationManager.createNotificationChannel(channel)
    }

    private fun startPolling() {
        // Poll every 30 seconds
        val pollingInterval = 30000L

        Thread {
            while (true) {
                updateSystemStatus()
                Thread.sleep(pollingInterval)
            }
        }.start()
    }

    private fun updateSystemStatus() {
        // Simulate API call to get system status
        val status = fetchSystemStatus()

        runOnUiThread {
            systemStatusView.text = when (status.getString("status")) {
            "online" -> "🟢 ORION Online"
            "offline" -> "🔴 ORION Offline"
            else -> "🟡 ORION Connecting"
            }

            workflowsCountView.text = "${status.getInt("active_workflows)} Workflows"
            approvalsCountView.text = "${status.getInt("pending_approvals")} Approvals"

            // Update MERLIN summary
            val merlinSummary = status.optString("merlin_summary", "No recent activity")
            merlinSummaryView.text = "🧙 $merlinSummary"

            // Check for critical notifications
            val notifications = status.optJSONArray("notifications")
            if (notifications != null && notifications.length() > 0) {
                val latestNotification = notifications.getJSONObject(0)
                showNotification(latestNotification)
            }

            // Check for pending approvals
            val approvals = status.optJSONArray("approvals")
            if (approvals != null && approvals.length() > 0) {
                val latestApproval = approvals.getJSONObject(0)
                showApproval(latestApproval)
            }
        }
    }

    private fun fetchSystemStatus(): JSONObject {
        // In production, this would make an API call to the backend
        // For now, return simulated data
        return JSONObject().apply {
            put("status", "online")
            put("active_workflows", 3)
            put("pending_approvals", 2)
            put("merlin_summary", "2 opportunities detected today")
            put("notifications", JSONObject().apply {
                put("icon", "🚨")
                put("title", "Finding Detected")
                put("message", "SQL injection in target")
                put("risk", "high")
            })
            put("approvals", JSONObject().apply {
                put("id", 1)
                put("title", "Submit Report")
                put("description", "Submit SQL injection finding")
                put("risk", "high")
            })
        }
    }

    private fun showNotification(notification: JSONObject) {
        currentNotification = notification

        runOnUiThread {
            notificationIcon.text = notification.getString("icon")
            notificationTitle.text = notification.getString("title")
            notificationMessage.text = notification.getString("message")

            // Send native Wear OS notification
            sendWearNotification(
                notification.getString("title"),
                notification.getString("message"),
                notification.getString("risk")
            )
        }
    }

    private fun showApproval(approval: JSONObject) {
        currentApproval = approval

        runOnUiThread {
            notificationIcon.text = "✅"
            notificationTitle.text = approval.getString("title")
            notificationMessage.text = approval.getString("description")

            approveButton.visibility = View.VISIBLE
            rejectButton.visibility = View.VISIBLE
        }
    }

    private fun approveCurrentApproval() {
        currentApproval?.let { approval ->
            // In production, make API call to approve
            simulateApiCall("approve", approval.getInt("id"))

            // Clear approval
            currentApproval = null
            approveButton.visibility = View.GONE
            rejectButton.visibility = View.GONE

            // Show confirmation
            notificationTitle.text = "✓ Approved"
            notificationMessage.text = "Request approved successfully"
        }
    }

    private fun rejectCurrentApproval() {
        currentApproval?.let { approval ->
            // In production, make API call to reject
            simulateApiCall("reject", approval.getInt("id"))

            // Clear approval
            currentApproval = null
            approveButton.visibility = View.GONE
            rejectButton.visibility = View.GONE

            // Show confirmation
            notificationTitle.text = "✗ Rejected"
            notificationMessage.text = "Request rejected"
        }
    }

    private fun sendWearNotification(title: String, message: String, risk: String) {
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        val notification = NotificationCompat.Builder(this, NOTIFICATION_CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_launcher)
            .setContentTitle(title)
            .setContentText(message)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setAutoCancel(true)
            .build()

        notificationManager.notify(System.currentTimeMillis().toInt(), notification)
    }

    private fun simulateApiCall(action: String, id: Int) {
        // In production, make actual API call to backend
        // For now, just log
        println("API Call: $action approval $id")
    }
}
