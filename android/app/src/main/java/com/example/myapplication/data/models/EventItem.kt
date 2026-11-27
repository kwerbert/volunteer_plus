package com.example.myapplication.data.models

data class OrganizationInfo(
    val id: Long,
    val name: String,
    val logoUrl: String? = null,
    val rating: Float = 0f,
    val verified: Boolean = false,
    val categoryId: Int? = null
)

data class EventItem(
    val id: Long,
    val title: String,
    val organization: OrganizationInfo,
    val startTime: String,
    val endTime: String? = null,
    val descriptionPreview: String? = null,
    val locationLat: Double? = null,
    val locationLon: Double? = null,
    val distanceKm: Double? = null,
    val maxParticipants: Int? = null,
    val registeredCount: Int? = null,
    val qrSecret: String? = null,
    
    // Поля для организатора
    val whatToDo: String? = null,
    val volunteerRequirements: String? = null,
    val requiredVolunteers: Int? = null,
    val additionalInfo: String? = null,
    val hoursReward: Int? = null,
    val isPast: Boolean = false // <-- Флаг: мероприятие уже прошло
)
