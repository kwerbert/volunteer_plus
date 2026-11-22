package com.example.myapplication.data.repository

import com.example.myapplication.data.api.AuthApi
import com.example.myapplication.data.api.LoginRequest
import com.example.myapplication.data.api.TokenResponse
import javax.inject.Inject

class AuthRepository @Inject constructor(private val authApi: AuthApi) {
    suspend fun login(email: String, password: String): Result<TokenResponse> {
        return try {
            val response = authApi.login(LoginRequest(email, password))
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("Ошибка: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
