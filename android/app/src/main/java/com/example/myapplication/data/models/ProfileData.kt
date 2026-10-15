package com.example.myapplication.data.models

import android.os.Parcelable
import com.google.gson.annotations.SerializedName
import kotlinx.parcelize.Parcelize

data class ProfileData(
    @SerializedName("user_id")
    val userId: Long,

    @SerializedName("user_name")
    val userName: String,

    @SerializedName("total_hours")
    val totalHours: Int,

    @SerializedName("avatar_url")
    val avatarUrl: String? = null,

    @SerializedName("organizations")
    val organizations: List<OrgStats> = emptyList(),

    @SerializedName("email")
    val email: String? = null,

    @SerializedName("phone")
    val phone: String? = null,

    @SerializedName("role")
    val role: String? = null
)

data class MonthlyStat(
    val year: Int,
    val month: Int,
    val hours: Float
)

@Parcelize
data class OrgStats(
    @SerializedName("organization_id")
    val organizationId: Long,

    @SerializedName("organization_name")
    val name: String,

    @SerializedName("hours_contributed")
    val hours: Int,

    @SerializedName("events_count")
    val eventsCount: Int = 0
) : Parcelable