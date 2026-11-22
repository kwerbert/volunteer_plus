package com.example.myapplication.data.api

import com.example.myapplication.data.models.UpdateProfileRequest
import com.example.myapplication.data.models.UpdateSettingsRequest
import com.example.myapplication.data.models.UserResponse
import com.example.myapplication.data.models.UserSettingsResponse
import retrofit2.Response
import retrofit2.http.*

interface ProfileApi {
    @GET("api/v1/users/{user_id}")
    suspend fun getProfile(@Path("user_id") userId: Long): Response<UserResponse>

    @PUT("api/v1/users/{user_id}/settings")
    suspend fun updateSettings(
        @Path("user_id") userId: Long,
        @Body request: UpdateSettingsRequest
    ): Response<UserSettingsResponse>

    @PUT("api/v1/users/{user_id}")
    suspend fun updateProfile(
        @Path("user_id") userId: Long,
        @Body request: UpdateProfileRequest
    ): Response<UserResponse>

    @POST("api/v1/users/{user_id}/become-organizer")
    suspend fun becomeOrganizer(
        @Path("user_id") userId: Long
    ): Response<UserResponse>
}
