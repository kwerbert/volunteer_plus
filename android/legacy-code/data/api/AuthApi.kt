package com.example.myapplication.data.api

import com.example.myapplication.data.models.LoginRequest
import com.example.myapplication.data.models.RegisterRequest
import com.example.myapplication.data.models.TokenResponse
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.POST

/**
 * API интерфейс для User Service (порт 8008)
 * Эндпоинты для аутентификации: login, register, refresh, logout
 */
interface AuthApi {

    /**
     * Вход пользователя
     * @param request Email и пароль
     * @return Response с access и refresh токенами
     */
    @POST("api/v1/auth/login")
    suspend fun login(@Body request: LoginRequest): Response<TokenResponse>

    /**
     * Регистрация нового пользователя
     * @param request Email, пароль, опционально имя и телефон
     * @return Response с access и refresh токенами
     */
    @POST("api/v1/auth/register")
    suspend fun register(@Body request: RegisterRequest): Response<TokenResponse>

    /**
     * Обновление access токена
     * @param request Refresh токен
     * @return Response с новыми токенами
     */
    @POST("api/v1/auth/refresh")
    suspend fun refreshToken(@Body request: RefreshTokenRequest): Response<TokenResponse>

    /**
     * Выход из системы (отзыв refresh токена)
     * @param request Refresh токен
     * @return Response без тела (204 No Content)
     */
    @POST("api/v1/auth/logout")
    suspend fun logout(@Body request: RefreshTokenRequest): Response<Unit>
}

/**
 * Запрос для обновления токена
 */
data class RefreshTokenRequest(
    val refresh_token: String
)