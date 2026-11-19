package com.example.myapplication.data.models

import com.google.gson.annotations.SerializedName

data class UpdateSettingsRequest(
    @SerializedName("main_organization_id") val mainOrganizationId: Long? = null
)