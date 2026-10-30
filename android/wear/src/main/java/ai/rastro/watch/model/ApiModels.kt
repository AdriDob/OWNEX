package ai.rastro.watch.model

import com.google.gson.annotations.SerializedName

data class WearOSStatus(
    @SerializedName("system_online") val systemOnline: Boolean = true,
    @SerializedName("scheduler_running") val schedulerRunning: Boolean = false,
    @SerializedName("active_workflows") val activeWorkflows: Int = 0,
    @SerializedName("pending_approvals") val pendingApprovals: Int = 0,
    @SerializedName("findings_total") val findingsTotal: Int = 0,
    @SerializedName("findings_confirmed") val findingsConfirmed: Int = 0,
    @SerializedName("targets_active") val targetsActive: Int = 0,
    @SerializedName("health_score") val healthScore: Int = 100,
    @SerializedName("last_updated") val lastUpdated: String = ""
)

data class WearOSNotification(
    @SerializedName("notification_id") val notificationId: String,
    @SerializedName("title") val title: String,
    @SerializedName("message") val message: String,
    @SerializedName("level") val level: String,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("read") val read: Boolean = false,
    @SerializedName("requires_action") val requiresAction: Boolean = false,
    @SerializedName("action_type") val actionType: String? = null
)

data class WearOSApproval(
    @SerializedName("request_id") val requestId: String,
    @SerializedName("title") val title: String,
    @SerializedName("description") val description: String,
    @SerializedName("workflow_id") val workflowId: String? = null,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("responded") val responded: Boolean = false,
    @SerializedName("approved") val approved: Boolean? = null
)

data class ApprovalResponse(
    @SerializedName("approved") val approved: Boolean
)

data class SendNotificationRequest(
    @SerializedName("title") val title: String,
    @SerializedName("message") val message: String,
    @SerializedName("level") val level: String = "medium",
    @SerializedName("requires_action") val requiresAction: Boolean = false,
    @SerializedName("action_type") val actionType: String? = null
)

data class ApiError(
    val error: String? = null,
    val detail: String? = null
)