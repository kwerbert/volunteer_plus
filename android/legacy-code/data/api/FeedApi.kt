package com.example.myapplication.data.api

import com.example.myapplication.data.models.FeedResponse
import retrofit2.Response
import retrofit2.http.GET
import retrofit2.http.Query

interface FeedApi {

    @GET("api/v1/feed")
    suspend fun getFeed(
        @Query("user_id") userId: Long,
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 20,
        @Query("search") searchQuery: String? = null,
        @Query("location_lat") locationLat: Double? = null,
        @Query("location_lon") locationLon: Double? = null,
        @Query("radius_km") radiusKm: Int? = null,
        @Query("category_ids") categoryIds: String? = null,
        @Query("show_only_subscriptions") showOnlySubscriptions: Boolean? = null
    ): Response<FeedResponse>
}