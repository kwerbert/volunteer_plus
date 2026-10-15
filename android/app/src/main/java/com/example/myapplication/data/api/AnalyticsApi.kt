package com.example.myapplication.data.api

import com.example.myapplication.data.models.AnalyticsResponse
import com.example.myapplication.data.models.MonthlyStatsResponse
import com.example.myapplication.data.models.OrgAnalytics
import retrofit2.Response
import retrofit2.http.GET
import retrofit2.http.Path
import retrofit2.http.Query

/**
 * API интерфейс для Analytics Service (порт 8005)
 * Эндпоинты для получения аналитики волонтёра
 */
interface AnalyticsApi {

    @GET("api/v1/analytics/users/{user_id}")
    suspend fun getUserAnalytics(@Path("user_id") userId: Long): Response<AnalyticsResponse>

    @GET("api/v1/analytics/users/{user_id}/by-organization")
    suspend fun getOrganizationAnalytics(@Path("user_id") userId: Long): Response<OrganizationStatsResponse>

    @GET("api/v1/analytics/users/{user_id}/monthly")
    suspend fun getMonthlyAnalytics(
        @Path("user_id") userId: Long,
        @Query("months") months: Int = 12
    ): Response<MonthlyStatsResponse>
}

/**
 * Модель ответа для статистики по организациям
 */
data class OrganizationStatsResponse(
    val user_id: Long,
    val organizations: List<OrgAnalyticsItem>,
    val total_organizations: Int,
    val generated_at: String
)

data class OrgAnalyticsItem(
    val organization_id: Long,
    val organization_name: String?,
    val hours_worked: Float,
    val events_completed: Int,
    val role: String?
)