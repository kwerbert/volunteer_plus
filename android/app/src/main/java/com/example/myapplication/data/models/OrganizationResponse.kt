package com.example.myapplication.data.models

import com.google.gson.annotations.SerializedName

data class OrganizationResponse(
    @SerializedName("id") val id: Int,
    @SerializedName("name") val name: String,
    @SerializedName("description") val description: String?,
    @SerializedName("is_verified") val isVerified: Boolean,
    @SerializedName("rating") val rating: Float,
    @SerializedName("category_id") val categoryId: Int?,
    @SerializedName("avatar_url") val avatarUrl: String? = null
)