package com.example.myapplication.data.models

import com.google.gson.annotations.SerializedName

data class SubscriptionRequest(
    @SerializedName("user_id") val userId: Int,
    @SerializedName("org_id") val orgId: Int,
    @SerializedName("role") val role: String = "volunteer"
)

data class SubscriptionResponse(
    @SerializedName("id") val id: Int,
    @SerializedName("user_id") val userId: Int,
    @SerializedName("org_id") val orgId: Int,
    @SerializedName("role") val role: String,
    @SerializedName("active") val active: Boolean,
    @SerializedName("created_at") val createdAt: String
)

data class SubscriptionCheckResponse(
    @SerializedName("is_subscribed") val isSubscribed: Boolean,
    @SerializedName("subscription_id") val subscriptionId: Int?,
    @SerializedName("active") val active: Boolean,
    @SerializedName("role") val role: String?
)