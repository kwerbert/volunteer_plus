package com.example.myapplication.data.models

import com.google.gson.annotations.SerializedName

data class AnalyticsResponse(
    @SerializedName("user_id") val userId: Long,
    @SerializedName("total_hours") val totalHours: Float,
    @SerializedName("total_events") val totalEvents: Int,
    @SerializedName("organizations_count") val organizationsCount: Int,
    @SerializedName("organizations") val organizations: List<OrgAnalytics> = emptyList()
)

data class OrgAnalytics(
    @SerializedName("organization_id") val organizationId: Long,
    @SerializedName("organization_name") val organizationName: String?,
    @SerializedName("hours_worked") val hoursWorked: Float,
    @SerializedName("events_completed") val eventsCompleted: Int,
    @SerializedName("role") val role: String?
)

data class MonthlyStatsResponse(
    val user_id: Long,
    val months: List<MonthlyData>,
    val total_hours: Float,
    val total_events: Int
)

data class MonthlyData(
    val year: Int,
    val month: Int,
    val hours_worked: Float,
    val events_completed: Int
)