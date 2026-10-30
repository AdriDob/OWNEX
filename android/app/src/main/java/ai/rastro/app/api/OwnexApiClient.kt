package ai.rastro.app.api

import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import ai.rastro.app.model.*
import okhttp3.*
import java.io.IOException
import java.util.concurrent.TimeUnit

class OwnexApiClient(private var baseUrl: String = "http://10.0.2.2:8000") {

    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .build()

    private val gson = Gson()

    fun updateBaseUrl(url: String) {
        baseUrl = url.trimEnd('/')
    }

    private fun get(path: String): String? {
        val request = Request.Builder()
            .url("$baseUrl$path")
            .get()
            .build()
        return try {
            client.newCall(request).execute().use { response ->
                if (response.isSuccessful) response.body?.string() else null
            }
        } catch (e: IOException) {
            null
        }
    }

    private fun post(path: String, body: Any? = null): String? {
        val requestBody = if (body != null) {
            RequestBody.create(
                MediaType.parse("application/json"),
                gson.toJson(body)
            )
        } else {
            RequestBody.create(MediaType.parse("application/json"), "{}")
        }
        val request = Request.Builder()
            .url("$baseUrl$path")
            .post(requestBody)
            .build()
        return try {
            client.newCall(request).execute().use { response ->
                if (response.isSuccessful) response.body?.string() else null
            }
        } catch (e: IOException) {
            null
        }
    }

    // --- System ---

    fun getSystemStatus(): SystemStatus {
        val json = get("/api/system/status") ?: return SystemStatus()
        return try {
            val map = gson.fromJson<Map<String, Any>>(
                json, object : TypeToken<Map<String, Any>>() {}.type
            )
            SystemStatus(
                status = map["status"] as? String ?: "unknown",
                version = map["version"] as? String ?: "",
                workerRunning = map["worker_running"] as? Boolean ?: false,
                schedulerRunning = map["scheduler_running"] as? Boolean ?: false,
                activeWork = (map["active_work"] as? Number)?.toInt() ?: 0,
                pendingApprovals = (map["pending_approvals"] as? Number)?.toInt() ?: 0,
            )
        } catch (e: Exception) {
            SystemStatus()
        }
    }

    // --- Daily Brief ---

    fun getDailyBrief(): DailyBrief {
        val json = get("/api/daily-brief") ?: return DailyBrief()
        return try {
            val map = gson.fromJson<Map<String, Any>>(
                json, object : TypeToken<Map<String, Any>>() {}.type
            )
            val actions = (map["top_actions"] as? List<*>)?.mapNotNull { item ->
                val m = item as? Map<*, *> ?: return@mapNotNull null
                ActionItem(
                    id = m["id"] as? String ?: "",
                    title = m["title"] as? String ?: "",
                    platform = m["platform"] as? String ?: "",
                    ev = (m["ev"] as? Number)?.toDouble() ?: 0.0,
                    probability = (m["probability"] as? Number)?.toDouble() ?: 0.0,
                    estimatedHours = (m["estimated_hours"] as? Number)?.toDouble() ?: 0.0,
                    nextStep = m["next_step"] as? String ?: "",
                )
            } ?: emptyList()
            DailyBrief(
                greeting = map["greeting"] as? String ?: "",
                topActions = actions,
                totalEV = (map["total_ev"] as? Number)?.toDouble() ?: 0.0,
                revenueToday = (map["revenue_today"] as? Number)?.toDouble() ?: 0.0,
            )
        } catch (e: Exception) {
            DailyBrief()
        }
    }

    // --- Worker ---

    fun getWorkerStatus(): Map<String, Any> {
        val json = get("/api/worker/status") ?: return emptyMap()
        return try {
            gson.fromJson(json, object : TypeToken<Map<String, Any>>() {}.type)
        } catch (e: Exception) {
            emptyMap()
        }
    }

    fun startWorker(): Boolean = post("/api/worker/start") != null
    fun stopWorker(): Boolean = post("/api/worker/stop") != null
    fun pauseWorker(): Boolean = post("/api/worker/pause") != null
    fun resumeWorker(): Boolean = post("/api/worker/resume") != null

    // --- Work Items ---

    fun getWorkItems(): List<WorkItem> {
        val json = get("/api/worker/work-items") ?: return emptyList()
        return try {
            val list = gson.fromJson<List<Map<String, Any>>>(
                json, object : TypeToken<List<Map<String, Any>>>() {}.type
            )
            list.map { map ->
                WorkItem(
                    id = map["id"] as? String ?: "",
                    title = map["title"] as? String ?: "",
                    platform = map["platform"] as? String ?: "",
                    state = map["state"] as? String ?: "",
                    rewardLow = (map["reward_low"] as? Number)?.toDouble() ?: 0.0,
                    rewardHigh = (map["reward_high"] as? Number)?.toDouble() ?: 0.0,
                    progressPct = (map["progress_pct"] as? Number)?.toInt() ?: 0,
                    evPerHour = (map["ev_per_hour"] as? Number)?.toDouble() ?: 0.0,
                )
            }
        } catch (e: Exception) {
            emptyList()
        }
    }

    fun approveWorkItem(id: String): Boolean = post("/api/worker/work-items/$id/approve") != null
    fun rejectWorkItem(id: String): Boolean = post("/api/worker/work-items/$id/reject") != null

    // --- Approvals ---

    fun getPendingApprovals(): List<ApprovalItem> {
        val json = get("/api/approvals/pending") ?: return emptyList()
        return try {
            val list = gson.fromJson<List<Map<String, Any>>>(
                json, object : TypeToken<List<Map<String, Any>>>() {}.type
            )
            list.map { map ->
                ApprovalItem(
                    id = map["id"] as? String ?: "",
                    title = map["title"] as? String ?: "",
                    description = map["description"] as? String ?: "",
                    type = map["type"] as? String ?: "",
                    risk = map["risk"] as? String ?: "low",
                    createdAt = map["created_at"] as? String ?: "",
                )
            }
        } catch (e: Exception) {
            emptyList()
        }
    }

    fun approveAction(id: String): Boolean = post("/api/approvals/$id/approve") != null
    fun rejectAction(id: String): Boolean = post("/api/approvals/$id/reject") != null

    // --- Health ---

    fun getHealth(): HealthCheck {
        val json = get("/api/health") ?: return HealthCheck(healthy = false)
        return try {
            val map = gson.fromJson<Map<String, Any>>(
                json, object : TypeToken<Map<String, Any>>() {}.type
            )
            HealthCheck(
                healthy = map["status"] == "ok",
                score = (map["score"] as? Number)?.toInt() ?: 0,
            )
        } catch (e: Exception) {
            HealthCheck(healthy = false)
        }
    }

    // --- Revenue ---

    fun getRevenueSummary(): RevenueSummary {
        val json = get("/api/economic/financial-summary") ?: return RevenueSummary()
        return try {
            val map = gson.fromJson<Map<String, Any>>(
                json, object : TypeToken<Map<String, Any>>() {}.type
            )
            RevenueSummary(
                expected = (map["total_expected"] as? Number)?.toDouble() ?: 0.0,
                earned = (map["total_collected"] as? Number)?.toDouble() ?: 0.0,
                pending = (map["total_pending"] as? Number)?.toDouble() ?: 0.0,
            )
        } catch (e: Exception) {
            RevenueSummary()
        }
    }
}
