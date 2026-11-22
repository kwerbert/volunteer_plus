package com.example.myapplication.util

import android.util.Log
import com.auth0.android.jwt.JWT

/**
 * Утилиты для работы с JWT токенами
 * Используется как fallback если backend не возвращает user_id в ответе
 */
object JwtUtils {

    private const val TAG = "JwtUtils"

    /**
     * Извлечение user_id из JWT токена
     * @param token JWT токен (access или refresh)
     * @return user_id или null если токен невалиден
     */
    fun extractUserId(token: String?): Long? {
        if (token.isNullOrEmpty()) {
            Log.w(TAG, "Token is null or empty")
            return null
        }

        return try {
            val jwt = JWT(token)
            val userId = jwt.getClaim("user_id").asLong()
            Log.d(TAG, "Extracted user_id from JWT: $userId")
            userId
        } catch (e: Exception) {
            Log.e(TAG, "Failed to decode JWT token", e)
            null
        }
    }

    /**
     * Извлечение email из JWT токена
     * @param token JWT токен
     * @return email или null если токен невалиден
     */
    fun extractEmail(token: String?): String? {
        if (token.isNullOrEmpty()) {
            return null
        }

        return try {
            val jwt = JWT(token)
            jwt.getClaim("email").asString()
        } catch (e: Exception) {
            Log.e(TAG, "Failed to decode JWT token", e)
            null
        }
    }

    /**
     * Извлечение роли из JWT токена
     * @param token JWT токен
     * @return role или null если токен невалиден
     */
    fun extractRole(token: String?): String? {
        if (token.isNullOrEmpty()) {
            return null
        }

        return try {
            val jwt = JWT(token)
            jwt.getClaim("role").asString()
        } catch (e: Exception) {
            Log.e(TAG, "Failed to decode JWT token", e)
            null
        }
    }

    /**
     * Проверка истечения токена
     * @param token JWT токен
     * @return true если токен истёк
     */
    fun isExpired(token: String?): Boolean {
        if (token.isNullOrEmpty()) {
            return true
        }

        return try {
            val jwt = JWT(token)
            jwt.isExpired(0)  // 0 секунд лейниенс
        } catch (e: Exception) {
            Log.e(TAG, "Failed to check token expiration", e)
            true
        }
    }

    /**
     * Получение времени истечения токена (в секундах с эпохи Unix)
     * @param token JWT токен
     * @return timestamp истечения или null
     */
    fun getExpirationTime(token: String?): Long? {
        if (token.isNullOrEmpty()) {
            return null
        }

        return try {
            val jwt = JWT(token)
            jwt.expiresAt?.time ?: null
        } catch (e: Exception) {
            Log.e(TAG, "Failed to get token expiration time", e)
            null
        }
    }
}