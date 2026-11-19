package com.example.myapplication.data.models

data class FeedFilterParams(
    val searchQuery: String? = null,
    val locationLat: Double? = null,
    val locationLon: Double? = null,
    val radiusKm: Int? = null,
    val categoryIds: List<Int>? = null,
    val showOnlySubscriptions: Boolean? = null
)