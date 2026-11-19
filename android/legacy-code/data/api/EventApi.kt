package com.example.myapplication.data.api

import com.example.myapplication.data.models.EventRegistrationRequest
import com.example.myapplication.data.models.EventRegistrationResponse
import retrofit2.Response
import com.example.myapplication.data.models.CheckInRequest
import com.example.myapplication.data.models.ParticipationResponse
import retrofit2.http.*

interface EventApi {
    @POST("api/v1/events/{event_id}/register")
    suspend fun registerForEvent(
        @Path("event_id") eventId: Int,
        @Body request: EventRegistrationRequest
    ): Response<EventRegistrationResponse>
    @POST("api/v1/events/{event_id}/check-in")
    suspend fun checkIn(
        @Path("event_id") eventId: Int,
        @Body request: CheckInRequest
    ): Response<ParticipationResponse>
}