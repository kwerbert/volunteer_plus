package com.example.myapplication.data.local.entities

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "cached_events")
data class CachedEventEntity(
    @PrimaryKey val id: Long,
    val title: String,
    val organizationId: Long,
    val organizationName: String,
    val startTime: String,
    val endTime: String? = null,
    val descriptionPreview: String?,
    val locationLat: Double? = null,
    val locationLon: Double? = null,
    val distanceKm: Double? = null,
    val cachedAt: Long = System.currentTimeMillis()
)