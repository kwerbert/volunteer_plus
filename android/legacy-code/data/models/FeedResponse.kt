package com.example.myapplication.data.models

import com.google.gson.annotations.SerializedName
import android.os.Parcelable
import kotlinx.parcelize.Parcelize

data class FeedResponse(
    @SerializedName("user_id") val userId: Long,
    @SerializedName("generated_at") val generatedAt: String,
    @SerializedName("sections") val sections: List<FeedSection>,
    @SerializedName("total_events") val totalEvents: Int,
    @SerializedName("has_more") val hasMore: Boolean = false,
    @SerializedName("filters_applied") val filtersApplied: Map<String, Any>? = null
)

data class FeedSection(
    @SerializedName("section_type") val sectionType: String,
    @SerializedName("section_title") val sectionTitle: String,
    @SerializedName("events") val events: List<EventItem>,
    @SerializedName("layout") val layout: String = "horizontal"
)

// ИЗМЕНЕНО: Добавлен @Parcelize для прямой передачи во Fragment
@Parcelize
data class EventItem(
    @SerializedName("id") val id: Long,
    @SerializedName("title") val title: String,
    @SerializedName("organization") val organization: OrganizationInfo,
    @SerializedName("start_time") val startTime: String,
    @SerializedName("end_time") val endTime: String? = null,
    @SerializedName("description_preview") val descriptionPreview: String?,
    @SerializedName("location_lat") val locationLat: Double? = null,
    @SerializedName("location_lon") val locationLon: Double? = null,
    @SerializedName("distance_km") val distanceKm: Double? = null,
    @SerializedName("max_participants") val maxParticipants: Int? = null,
    @SerializedName("registered_count") val registeredCount: Int? = null,
    @SerializedName("qr_secret") val qrSecret: String? = null
) : Parcelable

@Parcelize
data class OrganizationInfo(
    @SerializedName("id") val id: Long,
    @SerializedName("name") val name: String,
    @SerializedName("logo_url") val logoUrl: String? = null,
    @SerializedName("rating") val rating: Float = 0f,
    @SerializedName("verified") val verified: Boolean = false,
    @SerializedName("category_id") val categoryId: Int? = null
) : Parcelable