package com.example.myapplication.network

import okhttp3.Interceptor
import okhttp3.Response
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuthInterceptor @Inject constructor() : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        // Пока просто пропускаем запрос, без сложной логики токенов
        return chain.proceed(chain.request())
    }
}
