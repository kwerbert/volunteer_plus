package com.example.myapplication.data.models

import com.google.gson.annotations.SerializedName

// ==================== REQUEST MODELS ====================
data class LoginRequest(
    @SerializedName("email")
    val email: String,
    @SerializedName("password")
    val password: String
)

data class RegisterRequest(
    @SerializedName("email")
    val email: String,
    @SerializedName("password")
    val password: String,
    @SerializedName("full_name")
    val fullName: String? = null,
    @SerializedName("phone")
    val phone: String? = null
)

// ==================== RESPONSE MODELS ====================
data class TokenResponse(
    @SerializedName("access_token")
    val accessToken: String,
    @SerializedName("refresh_token")
    val refreshToken: String,
    @SerializedName("token_type")
    val tokenType: String = "bearer",
    @SerializedName("expires_in")
    val expiresIn: Int,
    @SerializedName("user_id")
    val userId: Long
)

data class UserAuthResponse(
    @SerializedName("id")
    val id: Long,
    @SerializedName("email")
    val email: String,
    @SerializedName("full_name")
    val fullName: String? = null,
    @SerializedName("phone")
    val phone: String? = null,
    @SerializedName("role")
    val role: String = "volunteer",
    @SerializedName("is_active")
    val isActive: Boolean = true,
    @SerializedName("is_verified")
    val isVerified: Boolean = false
)

data class AuthResult(
    val tokens: TokenResponse,
    val user: UserAuthResponse? = null
)

// ==================== ERROR MODELS ====================
data class AuthErrorResponse(
    @SerializedName("detail")
    val detail: String,
    @SerializedName("error_code")
    val errorCode: String? = null
)