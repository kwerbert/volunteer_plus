package com.example.myapplication.data.api

import com.example.myapplication.data.models.SubscriptionRequest
import com.example.myapplication.data.models.SubscriptionResponse
import com.example.myapplication.data.models.SubscriptionCheckResponse
import retrofit2.Response
import retrofit2.http.*

interface SubscriptionApi {

    @POST("api/v1/subscriptions")
    suspend fun createSubscription(
        @Body request: SubscriptionRequest
    ): Response<SubscriptionResponse>

    @GET("api/v1/subscriptions")
    suspend fun getSubscriptions(
        @Query("user_id") userId: Int
    ): Response<List<SubscriptionResponse>>

    @DELETE("api/v1/subscriptions/{sub_id}")
    suspend fun unsubscribe(
        @Path("sub_id") subId: Int
    ): Response<Unit>

    @GET("api/v1/subscriptions/check")
    suspend fun checkSubscriptionStatus(
        @Query("user_id") userId: Int,
        @Query("org_id") orgId: Int
    ): Response<SubscriptionCheckResponse>
}