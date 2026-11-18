package com.example.myapplication.util

import android.content.Context
import android.content.SharedPreferences
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class SessionManager @Inject constructor(
    @ApplicationContext context: Context
) {
    private val prefs: SharedPreferences = context.getSharedPreferences(
        "volunteer_session",
        Context.MODE_PRIVATE
    )

    var userId: Long
        get() = prefs.getLong("user_id", -1L)
        set(value) = prefs.edit().putLong("user_id", value).apply()

    var accessToken: String?
        get() = prefs.getString("access_token", null)
        set(value) = prefs.edit().putString("access_token", value).apply()

    var refreshToken: String?
        get() = prefs.getString("refresh_token", null)
        set(value) = prefs.edit().putString("refresh_token", value).apply()

    var isLoggedIn: Boolean
        get() = prefs.getBoolean("is_logged_in", false)
        set(value) = prefs.edit().putBoolean("is_logged_in", value).apply()

    var tokenExpirationTime: Long
        get() = prefs.getLong("token_expiration_time", 0L)
        set(value) = prefs.edit().putLong("token_expiration_time", value).apply()

    // ДОБАВЛЕНО: Сохранение выбранной основной организации
    var mainOrganizationId: Long
        get() = prefs.getLong("main_org_id", -1L)
        set(value) = prefs.edit().putLong("main_org_id", value).apply()

    var mainOrganizationName: String?
        get() = prefs.getString("main_org_name", null)
        set(value) = prefs.edit().putString("main_org_name", value).apply()

    var fcmToken: String?
        get() = prefs.getString("fcm_token", null)
        set(value) = prefs.edit().putString("fcm_token", value).apply()

    fun saveAuthData(
        accessToken: String,
        refreshToken: String,
        userId: Long,
        expiresIn: Int
    ) {
        this.accessToken = accessToken
        this.refreshToken = refreshToken
        this.userId = userId
        this.isLoggedIn = true
        this.tokenExpirationTime = System.currentTimeMillis() + (expiresIn * 1000L)
    }

    fun saveAuthDataWithJwtFallback(
        accessToken: String,
        refreshToken: String,
        expiresIn: Int
    ) {
        val jwtUserId = JwtUtils.extractUserId(accessToken)
        this.accessToken = accessToken
        this.refreshToken = refreshToken
        this.userId = jwtUserId ?: Constants.DEV_FALLBACK_USER_ID
        this.isLoggedIn = true
        this.tokenExpirationTime = System.currentTimeMillis() + (expiresIn * 1000L)
    }

    fun isTokenExpired(): Boolean {
        if (tokenExpirationTime == 0L) return true
        val currentTime = System.currentTimeMillis()
        val timeLeft = tokenExpirationTime - currentTime
        return timeLeft < 60_000L
    }

    fun clear() {
        prefs.edit().clear().apply()
    }

    fun getCurrentUserId(): Long = if (userId > 0) userId else Constants.DEV_FALLBACK_USER_ID

    fun hasValidSession(): Boolean {
        return isLoggedIn && !accessToken.isNullOrEmpty() && !isTokenExpired()
    }

    fun needsTokenRefresh(): Boolean {
        if (tokenExpirationTime == 0L) return false
        val currentTime = System.currentTimeMillis()
        val timeLeft = tokenExpirationTime - currentTime
        return timeLeft < 300_000L && timeLeft > 0
    }

    fun validateAccessToken(): Boolean {
        if (accessToken.isNullOrEmpty()) return false
        return !JwtUtils.isExpired(accessToken)
    }
    var userRole: String?
        get() = prefs.getString("user_role", null)
        set(value) = prefs.edit().putString("user_role", value).apply()

    fun saveAuthData(
        accessToken: String,
        refreshToken: String,
        userId: Long,
        expiresIn: Int,
        role: String? = null
    ) {
        this.accessToken = accessToken
        this.refreshToken = refreshToken
        this.userId = userId
        this.isLoggedIn = true
        this.tokenExpirationTime = System.currentTimeMillis() + (expiresIn * 1000L)
        if (role != null) {
            this.userRole = role
        }
    }
}