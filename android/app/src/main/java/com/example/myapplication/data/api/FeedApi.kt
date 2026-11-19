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
        @Query("page_size") pageSize: Int = 20
    ): Response<FeedResponse>
}
