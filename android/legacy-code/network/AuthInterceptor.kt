package com.example.myapplication.network

import com.example.myapplication.BuildConfig
import com.example.myapplication.data.api.AuthApi
import com.example.myapplication.data.api.RefreshTokenRequest
import com.example.myapplication.util.Constants
import com.example.myapplication.util.JwtUtils
import com.example.myapplication.util.SessionManager
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeoutOrNull
import okhttp3.Interceptor
import okhttp3.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuthInterceptor @Inject constructor(
    private val sessionManager: SessionManager
) : Interceptor {

    private var isRefreshing = false
    private var newToken: String? = null

    private val refreshRetrofit: Retrofit by lazy {
        Retrofit.Builder()
            .baseUrl(Constants.USER_SERVICE_URL)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }

    private val refreshAuthApi: AuthApi by lazy {
        refreshRetrofit.create(AuthApi::class.java)
    }

    override fun intercept(chain: Interceptor.Chain): Response {
        val original = chain.request()
        val requestUrl = original.url.toString()
        if (requestUrl.contains("/auth/login") ||
            requestUrl.contains("/auth/register") ||
            requestUrl.contains("/auth/refresh")) {
            return chain.proceed(original)
        }

        val token = getEffectiveToken()
        val requestWithAuth = if (!token.isNullOrEmpty()) {
            original.newBuilder()
                .header("Authorization", "Bearer $token")
                .build()
        } else {
            original
        }

        var response = chain.proceed(requestWithAuth)

        if (response.code == 401 && !requestUrl.contains("/auth/logout")) {
            synchronized(this) {
                if (!isRefreshing) {
                    isRefreshing = true
                    try {
                        val newAccessToken = refreshToken()
                        if (newAccessToken != null) {
                            newToken = newAccessToken
                            response.close()
                            val newRequest = original.newBuilder()
                                .header("Authorization", "Bearer $newAccessToken")
                                .build()
                            response = chain.proceed(newRequest)
                        } else {
                            sessionManager.clear()
                        }
                    } finally {
                        isRefreshing = false
                    }
                } else {
                    // Ожидаем завершения refresh с ограничением по времени
                    var retries = 0
                    while (newToken == null && retries < 10) {
                        Thread.sleep(100)
                        retries++
                    }
                    if (newToken != null) {
                        response.close()
                        val newRequest = original.newBuilder()
                            .header("Authorization", "Bearer $newToken")
                            .build()
                        response = chain.proceed(newRequest)
                    }
                }
            }
        }
        return response
    }

    private fun refreshToken(): String? {
        val refreshToken = sessionManager.refreshToken ?: return null
        return try {
            val response = runBlocking {
                withTimeoutOrNull(5000L) {
                    refreshAuthApi.refreshToken(RefreshTokenRequest(refreshToken))
                }
            }
            if (response?.isSuccessful == true && response.body() != null) {
                val tokens = response.body()!!
                val newRole = JwtUtils.extractRole(tokens.accessToken)
                sessionManager.saveAuthData(
                    accessToken = tokens.accessToken,
                    refreshToken = tokens.refreshToken,
                    userId = tokens.userId,
                    expiresIn = tokens.expiresIn,
                    role = newRole
                )
                tokens.accessToken
            } else {
                null
            }
        } catch (e: Exception) {
            null
        }
    }

    private fun getEffectiveToken(): String? {
        // Убираем фейковый токен – только реальный
        return sessionManager.accessToken
    }
}