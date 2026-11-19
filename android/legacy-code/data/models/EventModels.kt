package com.example.myapplication.data.models

import com.google.gson.annotations.SerializedName

data class EventRegistrationRequest(
    @SerializedName("user_id") val userId: Int
)

data class EventRegistrationResponse(
    @SerializedName("id") val id: Int,
    @SerializedName("event_id") val eventId: Int,
    @SerializedName("user_id") val userId: Int,
    @SerializedName("status") val status: String
)

data class CheckInRequest(
    @SerializedName("user_id") val userId: Int,
    @SerializedName("qr_code") val qrCode: String
)

data class ParticipationResponse(
    @SerializedName("id") val id: Int,
    @SerializedName("event_id") val eventId: Int,
    @SerializedName("user_id") val userId: Int,
    @SerializedName("status") val status: String,
    @SerializedName("checked_in_at") val checkedInAt: String? = null
)