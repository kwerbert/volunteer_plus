package com.example.myapplication.data.repository

import com.example.myapplication.data.api.RefreshTokenRequest
import com.example.myapplication.data.api.AuthApi
import com.example.myapplication.data.models.LoginRequest
import com.example.myapplication.data.models.RegisterRequest
import com.example.myapplication.data.models.TokenResponse
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuthRepository @Inject constructor(
    private val authApi: AuthApi
) {

    /**
     * Вход пользователя
     * @return Result с токенами или ошибкой
     */
    suspend fun login(email: String, password: String): Result<TokenResponse> =
        withContext(Dispatchers.IO) {
            try {
                val response = authApi.login(LoginRequest(email, password))
                if (response.isSuccessful && response.body() != null) {
                    Result.success(response.body()!!)
                } else {
                    Result.failure(Exception("Ошибка входа: ${response.code()}"))
                }
            } catch (e: Exception) {
                Result.failure(e)
            }
        }

    /**
     * Регистрация пользователя
     * @return Result с токенами или ошибкой
     */
    suspend fun register(
        email: String,
        password: String,
        fullName: String? = null,
        phone: String? = null
    ): Result<TokenResponse> = withContext(Dispatchers.IO) {
        try {
            val response = authApi.register(RegisterRequest(email, password, fullName, phone))
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("Ошибка регистрации: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * Обновление токена
     * @return Result с новыми токенами или ошибкой
     */
    suspend fun refreshToken(refreshToken: String): Result<TokenResponse> =
        withContext(Dispatchers.IO) {
            try {
                val response = authApi.refreshToken(RefreshTokenRequest(refreshToken))
                if (response.isSuccessful && response.body() != null) {
                    Result.success(response.body()!!)
                } else {
                    Result.failure(Exception("Ошибка обновления токена: ${response.code()}"))
                }
            } catch (e: Exception) {
                Result.failure(e)
            }
        }

    /**
     * Выход из системы
     * @return Result<Unit>
     */
    suspend fun logout(refreshToken: String): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            val response = authApi.logout(RefreshTokenRequest(refreshToken))
            if (response.isSuccessful) {
                Result.success(Unit)
            } else {
                Result.failure(Exception("Ошибка выхода: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}