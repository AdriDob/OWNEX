package ai.rastro.app.model

data class SystemStatus(
    val status: String = "unknown",
    val version: String = "",
    val workerRunning: Boolean = false,
    val schedulerRunning: Boolean = false,
    val uptime: String = "",
    val activeWork: Int = 0,
    val pendingApprovals: Int = 0,
    val todayActions: Int = 0,
)

data class DailyBrief(
    val greeting: String = "",
    val topActions: List<ActionItem> = emptyList(),
    val totalEV: Double = 0.0,
    val revenueToday: Double = 0.0,
    val blockedItems: List<String> = emptyList(),
)

data class ActionItem(
    val id: String = "",
    val title: String = "",
    val platform: String = "",
    val ev: Double = 0.0,
    val probability: Double = 0.0,
    val estimatedHours: Double = 0.0,
    val nextStep: String = "",
    val priority: Int = 0,
)

data class ApprovalItem(
    val id: String = "",
    val title: String = "",
    val description: String = "",
    val type: String = "",
    val risk: String = "low",
    val createdAt: String = "",
)

data class HealthCheck(
    val healthy: Boolean = true,
    val components: Map<String, ComponentHealth> = emptyMap(),
    val score: Int = 0,
)

data class ComponentHealth(
    val name: String = "",
    val status: String = "unknown",
    val message: String = "",
)

data class WorkItem(
    val id: String = "",
    val title: String = "",
    val platform: String = "",
    val state: String = "",
    val rewardLow: Double = 0.0,
    val rewardHigh: Double = 0.0,
    val progressPct: Int = 0,
    val evPerHour: Double = 0.0,
)

data class ChatMessage(
    val id: String = "",
    val role: String = "user",
    val content: String = "",
    val timestamp: String = "",
)

data class RevenueSummary(
    val expected: Double = 0.0,
    val committed: Double = 0.0,
    val earned: Double = 0.0,
    val pending: Double = 0.0,
    val paid: Double = 0.0,
    val net: Double = 0.0,
)
