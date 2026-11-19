package com.example.myapplication.api

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.Path
import retrofit2.http.POST
import retrofit2.http.Query

data class RegisterTokenRequest(
    val user_id: Int,
    val device_token: String,
    val platform: String,
    val app_version: String?
)

data class RegisterTokenResponse(
    val success: Boolean,
    val token_id: Int?,
    val error: String?
)

interface NotificationApiService {

    @POST("api/v1/tokens/register")
    suspend fun registerToken(@Body request: RegisterTokenRequest): Response<RegisterTokenResponse>

    @DELETE("api/v1/tokens/{device_token}")
    suspend fun unregisterToken(
        @Path("device_token") deviceToken: String,
        @Query("token") jwtToken: String
    ): Response<Unit>
}