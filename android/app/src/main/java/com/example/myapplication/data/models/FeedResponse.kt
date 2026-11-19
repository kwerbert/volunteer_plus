package com.example.myapplication.data.models

import com.google.gson.annotations.SerializedName

data class FeedResponse(
    @SerializedName("user_id") val userId: Long,
    @SerializedName("generated_at") val generatedAt: String,
    @SerializedName("sections") val sections: List<FeedSection>,
    @SerializedName("total_events") val totalEvents: Int
)

data class FeedSection(
    @SerializedName("section_type") val sectionType: String,
    @SerializedName("section_title") val sectionTitle: String,
    @SerializedName("events") val events: List<EventItem>,
    @SerializedName("layout") val layout: String = "horizontal"
)
