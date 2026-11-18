package com.example.myapplication.data.models

import com.google.gson.annotations.SerializedName

data class UserSettingsResponse(
    @SerializedName("id") val id: Int,
    @SerializedName("user_id") val userId: Int,
    @SerializedName("main_organization_id") val mainOrganizationId: Long? = null
)