package com.example.myapplication.data.repository

import com.example.myapplication.data.api.SubscriptionApi
import com.example.myapplication.data.models.SubscriptionRequest
import com.example.myapplication.data.models.SubscriptionResponse
import com.example.myapplication.data.models.SubscriptionCheckResponse
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class SubscriptionRepository @Inject constructor(
    private val subscriptionApi: SubscriptionApi
) {

    suspend fun subscribe(orgId: Int, userId: Int): Result<SubscriptionResponse> =
        withContext(Dispatchers.IO) {
            try {
                val response = subscriptionApi.createSubscription(SubscriptionRequest(userId, orgId))
                if (response.isSuccessful && response.body() != null) {
                    Result.success(response.body()!!)
                } else {
                    Result.failure(Exception("Ошибка подписки: ${response.code()}"))
                }
            } catch (e: Exception) {
                Result.failure(e)
            }
        }

    suspend fun getSubscriptions(userId: Int): Result<List<SubscriptionResponse>> =
        withContext(Dispatchers.IO) {
            try {
                val response = subscriptionApi.getSubscriptions(userId)
                if (response.isSuccessful && response.body() != null) {
                    Result.success(response.body()!!)
                } else {
                    Result.failure(Exception("Ошибка загрузки подписок: ${response.code()}"))
                }
            } catch (e: Exception) {
                Result.failure(e)
            }
        }

    // ДОБАВЛЕНО
    suspend fun unsubscribe(subscriptionId: Int): Result<Unit> =
        withContext(Dispatchers.IO) {
            try {
                val response = subscriptionApi.unsubscribe(subscriptionId)
                if (response.isSuccessful) {
                    Result.success(Unit)
                } else {
                    Result.failure(Exception("Ошибка отписки: ${response.code()}"))
                }
            } catch (e: Exception) {
                Result.failure(e)
            }
        }

    // ДОБАВЛЕНО
    suspend fun checkSubscriptionStatus(userId: Int, orgId: Int): Result<SubscriptionCheckResponse> =
        withContext(Dispatchers.IO) {
            try {
                val response = subscriptionApi.checkSubscriptionStatus(userId, orgId)
                if (response.isSuccessful && response.body() != null) {
                    Result.success(response.body()!!)
                } else {
                    Result.failure(Exception("Ошибка проверки подписки: ${response.code()}"))
                }
            } catch (e: Exception) {
                Result.failure(e)
            }
        }
}