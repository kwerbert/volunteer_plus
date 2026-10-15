package com.example.myapplication.data.api

import com.example.myapplication.data.models.OrganizationResponse
import retrofit2.Response
import retrofit2.http.GET

interface OrganizationApi {
    @GET("api/v1/organizations")
    suspend fun getOrganizations(): Response<List<OrganizationResponse>>
}