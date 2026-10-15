package com.example.myapplication.data.repository

import com.example.myapplication.data.api.EventApi
import com.example.myapplication.data.models.EventRegistrationRequest
import com.example.myapplication.data.models.EventRegistrationResponse
import com.example.myapplication.data.models.CheckInRequest
import com.example.myapplication.data.models.ParticipationResponse
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class EventRepository @Inject constructor(
    private val eventApi: EventApi
) {
    suspend fun registerForEvent(eventId: Int, userId: Int): Result<EventRegistrationResponse> =
        withContext(Dispatchers.IO) {
            try {
                val response = eventApi.registerForEvent(eventId, EventRegistrationRequest(userId))
                if (response.isSuccessful && response.body() != null) {
                    Result.success(response.body()!!)
                } else {
                    Result.failure(Exception("Ошибка регистрации: ${response.code()}"))
                }
            } catch (e: Exception) {
                Result.failure(e)
            }
        }
    suspend fun checkIn(eventId: Int, userId: Int, qrCode: String): Result<ParticipationResponse> =
        withContext(Dispatchers.IO) {
            try {
                val response = eventApi.checkIn(eventId, CheckInRequest(userId, qrCode))
                if (response.isSuccessful && response.body() != null) {
                    Result.success(response.body()!!)
                } else {
                    Result.failure(Exception("Ошибка отметки: ${response.code()}"))
                }
            } catch (e: Exception) {
                Result.failure(e)
            }
        }
}