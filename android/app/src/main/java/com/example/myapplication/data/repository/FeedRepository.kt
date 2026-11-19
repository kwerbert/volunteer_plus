package com.example.myapplication.data.repository

import com.example.myapplication.data.api.FeedApi
import com.example.myapplication.data.models.FeedResponse
import javax.inject.Inject

class FeedRepository @Inject constructor(private val api: FeedApi) {
    suspend fun getFeed(userId: Long): Result<FeedResponse> {
        return try {
            val response = api.getFeed(userId)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("Ошибка сервера: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
