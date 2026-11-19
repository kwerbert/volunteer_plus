package com.example.myapplication.util

import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class SessionManager @Inject constructor() {
    fun saveAuthData(accessToken: String, refreshToken: String, userId: Long, expiresIn: Int, role: String?) {
        // Заглушка для сохранения
    }

    fun clear() {
        // Заглушка для очистки
    }

    val refreshToken: String? get() = null
    val accessToken: String? get() = null
    fun isLoggedIn(): Boolean = false
    fun getCurrentUserId(): Long = 1L
}
