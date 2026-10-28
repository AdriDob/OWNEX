package ai.rastro.watch.api

import ai.rastro.watch.model.ApiModels.ApprovalResponse
import ai.rastro.watch.model.ApiModels.SendNotificationRequest
import ai.rastro.watch.model.ApiModels.WearOSApproval
import ai.rastro.watch.model.ApiModels.WearOSNotification
import ai.rastro.watch.model.ApiModels.WearOSStatus
import retrofit2.Call
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.PUT
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface WearOSApi {

    @GET("/wear-os/status")
    fun getStatus(): Call<WearOSStatus>

    @GET("/wear-os/notifications")
    fun getNotifications(
        @Query("level") level: String? = null,
        @Query("unread_only") unreadOnly: Boolean = false,
        @Query("limit") limit: Int = 20
    ): Call<List<WearOSNotification>>

    @PUT("/wear-os/notification/{notificationId}/read")
    fun markNotificationRead(@Path("notificationId") notificationId: String): Call<Unit>

    @POST("/wear-os/notification")
    fun sendNotification(@Body request: SendNotificationRequest): Call<WearOSNotification>

    @GET("/wear-os/approvals/pending")
    fun getPendingApprovals(): Call<List<WearOSApproval>>

    @POST("/wear-os/approval-request")
    fun requestApproval(@Body request: ApprovalRequest): Call<WearOSApproval>

    @POST("/wear-os/approval/{requestId}/respond")
    fun respondApproval(
        @Path("requestId") requestId: String,
        @Body response: ApprovalResponse
    ): Call<Unit>

    @POST("/wear-os/clear-notifications")
    fun clearNotifications(@Query("days") days: Int = 7): Call<Unit>

    // Health check for connection
    @GET("/health")
    fun healthCheck(): Call<Unit>

    data class ApprovalRequest(
        val title: String,
        val description: String,
        val workflowId: String? = null
    )
}