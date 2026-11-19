package com.example.myapplication.data.repository

import com.example.myapplication.data.api.OrganizationApi
import com.example.myapplication.data.models.OrganizationResponse
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class OrganizationRepository @Inject constructor(
    private val api: OrganizationApi
) {
    suspend fun getOrganizations(): Result<List<OrganizationResponse>> = withContext(Dispatchers.IO) {
        try {
            val response = api.getOrganizations()
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("Ошибка загрузки организаций: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}